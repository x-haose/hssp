import asyncio
import functools
import json
import traceback
from dataclasses import dataclass, field
from inspect import iscoroutinefunction
from types import AsyncGeneratorType
from typing import Callable, Tuple

from furl import furl
from hssp.exceptions import BrowerError
from hssp.response import Response
from hssp.settings import ReqSetting
from httpx import AsyncClient, Timeout
from loguru import logger
from pyppeteer.browser import Browser
from pyppeteer.network_manager import Request as PYPPRequest
from pyppeteer.page import Page
from tenacity import (
    AsyncRetrying, Future, RetryCallState,
    stop_after_attempt, wait_fixed, wait_random
)

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None


@dataclass
class Request(object):
    method: str
    url: str
    _setting: ReqSetting
    callback: Callable = field(default=None)
    metadata: dict = field(default=None)
    data: dict = field(default=None)
    json: dict = field(default=None)
    params: dict = field(default=None)
    user_agent: str = field(default=None)
    headers: dict = field(default=None)
    cookies: dict = field(default=None)
    timeout: float = field(default=None)
    session: AsyncClient = field(default=None)
    browser: Browser = field(default=None)
    is_browser: bool = field(default=False)
    _page: Page = field(default=None, init=False)

    def __post_init__(self):
        # 设置user_agent
        self.user_agent = self.user_agent or self._setting.user_agent

        # 设置httpx会话
        if not self.session:
            self.session = AsyncClient(proxies=self._setting.proxies, verify=False)

        # 设置session的headers、cookies、timeout
        self.session.headers = self.headers or self._setting.headers
        self.session.cookies = self.cookies or self._setting.cookies
        self.session.timeout = Timeout(self.timeout or self._setting.timeout)

        # user_agent设置到headers中
        if self.user_agent:
            self.session.headers.update({"user-agent": self.user_agent})

        self.headers = dict(self.session.headers)

        # 设置允许的状态码 默认是200-300之间
        allow_codes = list(range(200, 300))
        if not self._setting.allow_codes:
            self._setting.allow_codes = allow_codes
        else:
            self._setting.allow_codes.extend(allow_codes)

    async def close(self):
        """
        关闭session
        :return:
        """
        await self.session.aclose()

    def retry_handler(self, retry_state: RetryCallState):
        """
        处理重试之后和重试失败
        :param retry_state:
        :return:
        """
        outcome: Future = retry_state.outcome
        attempt_number = retry_state.attempt_number
        exception_type = type(outcome.exception()).__name__
        exception_msg = list(outcome.exception().args)
        stack_msg = traceback.format_stack()[2].strip()
        log_msg = f"[{self.method}] {self.url} 发生异常: [{exception_type}]: {exception_msg}"

        if 'retry_error_callback' in stack_msg:
            logger.error(f"{log_msg} {attempt_number}次重试全部失败")
            return None, Response(url=self.url, metadata=self.metadata)
        else:
            logger.error(f"{log_msg} 第{attempt_number}次重试")

        if self._page:
            asyncio.ensure_future(self._page.close())

    async def request(self, sem: asyncio.Semaphore) -> Tuple[AsyncGeneratorType, Response]:
        """
        使用httpx发起请求 带重试机制
        :param sem: 信号量 用于控制并发
        :return: 返回异步回调函数的执行结果和响应
        """
        if self._setting.retrys_count < 1:
            return await self._request(sem)

        # 设置重试的等候时间
        if self._setting.retries_delay:
            wait = wait_fixed(self._setting.retries_delay) + wait_random(0, 2)
        else:
            wait = wait_fixed(0)

        # 异步重试
        r = AsyncRetrying(
            stop=stop_after_attempt(self._setting.retrys_count),
            after=self.retry_handler,
            retry_error_callback=self.retry_handler,
            wait=wait
        )
        resp = await r.wraps(self._request)(sem)
        return resp

    async def _request_httpx(self, sem: asyncio.Semaphore) -> Response:
        """
        使用httpx发起请求
        :param sem: 信号量 用于控制并发
        :return:
        """
        async with sem:
            resp = await self.session.request(
                self.method,
                self.url,
                data=self.data,
                json=self.json,
                params=self.params,
            )
        response = Response(
            ok=resp.status_code in self._setting.allow_codes,
            url=str(resp.url),
            metadata=self.metadata,
            content=resp.content,
            status_code=resp.status_code,
            history=resp.history,
            cookies=dict(resp.cookies),
            headers=resp.headers
        )
        response.encoding = self._setting.encoding or resp.encoding
        response.json = resp.json
        return response

    async def _request_brower(self, sem: asyncio.Semaphore) -> Response:
        """
        使用pyppeteer的方式打开请求数据
        :param sem: 信号量 用于控制并发
        :return:
        """

        async def set_brower_request(pypp_req: PYPPRequest):
            if pypp_req.resourceType in ['image', 'media', 'eventsource', 'websocket']:
                await pypp_req.abort()
            else:
                await pypp_req.continue_({
                    "url": url,
                    "method": self.method,
                    "headers": headers
                })

        url = furl(self.url).add(self.params or {}).url
        headers = dict(self.session.headers)
        cookies = dict(self.session.cookies)

        async with sem:
            # 打开新页面
            self._page = await self.browser.newPage()
            # 启用拦截器
            await self._page.setRequestInterception(True)
            # 更改请求
            self._page.on("request", lambda pypp_req: asyncio.ensure_future(set_brower_request(pypp_req)))

            for k, v in cookies.items():
                await self._page.setCookie({
                    "name": k,
                    "value": v,
                    "domain": furl(url).host
                })

            # 打开网页
            resp = await self._page.goto(
                url=url,
                timeout=self.session.timeout.read * 1000,
                waitUntil="networkidle2",
            )

        if not resp:
            raise BrowerError()

        content = await resp.buffer()
        content = content.encode('utf-8') if isinstance(content, str) else content
        cookies = await self._page.cookies()
        cookies = {data['name']: data['value'] for data in cookies}
        response = Response(
            ok=resp.ok,
            url=resp.url,
            metadata=self.metadata,
            content=content,
            status_code=resp.status,
            cookies=cookies,
            headers=resp.headers
        )
        await self._page.close()
        self.session.cookies = cookies
        response.json = functools.partial(json.loads, response.text)
        return response

    async def _request(self, sem: asyncio.Semaphore) -> Tuple[AsyncGeneratorType, Response]:
        """
        使用httpx发起请求
        :param sem: 信号量 用于控制并发
        :return: 返回异步回调函数的执行结果和响应
        """
        if self._setting.delay > 0:
            await asyncio.sleep(self._setting.delay)

        logger.debug(f"[{self.method}] {self.url}")

        if self.is_browser:
            response = await self._request_brower(sem)
        else:
            response = await self._request_httpx(sem)

        if self.callback and response.ok:
            if iscoroutinefunction(self.callback):
                callback_result = await self.callback(response)
            else:
                callback_result = self.callback(response)
        else:
            callback_result = None

        return callback_result, response
