import functools
from asyncio import Semaphore
from inspect import iscoroutinefunction
from typing import Any

from blinker import Signal
from blinker import signal as get_signal
from fake_useragent import FakeUserAgent
from httpx import QueryParams
from tenacity import (
    AsyncRetrying,
    Future,
    RetryCallState,
    stop_after_attempt,
    wait_fixed,
    wait_random,
)

from hssp.exception.exception import RequestException, RequestStateException
from hssp.logger.log import hssp_logger
from hssp.models.net import ProxyModel, RequestModel
from hssp.network.downloader import HttpxDownloader, RequestsDownloader
from hssp.network.downloader.base import DownloaderBase
from hssp.network.response import Response
from hssp.settings.settings import settings


class Net:
    def __init__(
        self,
        downloader_cls: type[DownloaderBase] = HttpxDownloader,
        sem: Semaphore = None,
    ):
        """
        Args:
            downloader_cls: 使用的下载器
            sem: 信号量，控制并发
        """
        self._downloader = downloader_cls(sem, settings.headers, settings.cookies)
        self.logger = hssp_logger.getChild("net")

        if downloader_cls.__name__ == RequestsDownloader.__name__:
            self.logger.warning("不建议使用request下载器，无法发挥异步的性能")

        # net id
        self_id = id(self)

        # 请求重试信号
        self.request_retry_signal = get_signal(f"request_retry##{self_id}")
        # 请求之前信号
        self.request_before_signal = get_signal(f"request_before##{self_id}")
        # 响应之后信号
        self.response_after_signal = get_signal(f"response_signal##{self_id}")

    def get_cookies(self):
        """
        获取cookies
        Returns:

        """
        return self._downloader.cookies

    async def close(self):
        """
        关闭
        Returns:

        """
        await self._downloader.close()

    async def _retry_handler(self, req_data: RequestModel, retry_state: RetryCallState):
        """
        处理重试之后和重试失败
        Args:
            req_data: 请求数据
            retry_state: 重试状态

        Returns:

        """
        outcome: Future = retry_state.outcome
        attempt_number = retry_state.attempt_number
        exception = outcome.exception()
        exception_type = type(exception).__name__
        exception_msg = list(exception.args)

        # 执行重试中间件
        async for _ in self._send_signal(self.request_retry_signal, exception):
            ...

        if isinstance(exception, RequestStateException):
            exception_msg = f"响应状态:{exception.code} 不在 200 ~ 299 范围内"

        log_msg = (
            f"[{req_data.method}] {req_data.url} "
            f"使用代理：{req_data.proxy} 发生异常: [{exception_type}]: {exception_msg}"
        )

        if attempt_number == req_data.retrys_count:
            self.logger.error(f"{log_msg} {attempt_number}次重试全部失败")
            raise RequestException(exception_type, exception_msg)

        self.logger.error(f"{log_msg} 第{attempt_number}次重试")

    async def _send_signal(self, signal: Signal, *args, **kwargs):
        """
        发送信号
        Args:
            signal: 信号
            *args: 位置参数
            **kwargs: 键值参数

        Returns:

        """
        for receiver in signal.receivers_for(None):
            if iscoroutinefunction(receiver):
                result = await receiver(*args, **kwargs)
            else:
                result = receiver(*args, **kwargs)

            yield receiver, result

    async def _request(self, data: RequestModel) -> Response:
        """
        使用下载器发起异步请求
        Args:
            data: 请求数据

        Returns:
            返回响应
        """
        # 执行请求中间件
        async for _receiver, result in self._send_signal(self.request_before_signal, data):
            if result and isinstance(result, RequestModel):
                data = result
            if result and isinstance(result, Response):
                return result

        self.logger.info(
            f"[{data.method}] {data.url} "
            f"proxy: {data.proxy} "
            f"params: {data.url_params} "
            f"json_data: {data.json_data} "
            f"form_data: {data.form_data} "
            f"cookies: {data.cookies} "
            f"client_cookies: {self.get_cookies()}"
        )

        resp = await self._downloader.download(data)

        # 执行响应中间件
        async for _receiver, result in self._send_signal(self.response_after_signal, resp):
            if result and isinstance(result, Response):
                return result

        return resp

    def _set_fake_user_agent(self, data: RequestModel):
        """
        如果传入的UA是符合FakeUserAgent属性的，则使用FakeUserAgent获取一个假的UA
        Args:
            data: 请求数据
        """
        fake_user_agent_attrs = ["random", "chrome", "googlechrome", "edge", "firefox", "ff", "safari"]
        if data.user_agent not in fake_user_agent_attrs:
            return

        fake_user_agent = FakeUserAgent()
        data.user_agent = getattr(fake_user_agent, data.user_agent)

    def _set_default_request(self, data: RequestModel):
        """
        使用设置里面的全局设置对情求数据进行设置
        Args:
            data: 情求数据

        Returns:

        """
        if data.user_agent is None:
            data.user_agent = settings.user_agent

        if data.headers is None:
            data.headers = settings.headers or {}

        if data.cookies is None:
            data.cookies = settings.cookies

        if data.timeout is None:
            data.timeout = settings.timeout

        if data.proxy is None:
            data.proxy = settings.proxy

        if data.retrys_count is None:
            data.retrys_count = settings.retrys_count

        if data.retrys_delay is None:
            data.retrys_delay = settings.retrys_delay

    async def request(self, data: RequestModel) -> Response:
        """
        发起异步请求
        Args:
            data: 请求参数

        Returns:

        """
        self._set_default_request(data)

        if data.proxy:
            self._downloader.set_proxy(data.proxy)

        # 设置假UA
        self._set_fake_user_agent(data)

        # 更新UA
        if data.user_agent:
            data.headers.update({"User-Agent": data.user_agent})

        # 处理 POST form的数据
        # 有些情况form数据的key是相同的，而且还要求顺序，这时使用dict就无法实现
        # 这里是把form数据手动转为经过编码的字符串类型
        if data.form_data and isinstance(data.form_data, list | dict):
            form_data = QueryParams(data.form_data).__str__()
            data.form_data = form_data
            data.headers["Content-Type"] = "application/x-www-form-urlencoded"

        if data.retrys_count < 1:
            return await self._request(data)

        # 设置重试的等候时间
        wait = wait_fixed(data.retrys_delay) + wait_random(0.1, 1) if data.retrys_delay else wait_fixed(0)

        # 异步重试
        retry_resp = AsyncRetrying(
            stop=stop_after_attempt(data.retrys_count),
            after=functools.partial(self._retry_handler, data),
            retry_error_callback=functools.partial(self._retry_handler, data),
            wait=wait,
        )

        return await retry_resp.wraps(functools.partial(self._request, data))()

    async def get(
        self,
        url: str,
        params: dict = None,
        user_agent: str = None,
        headers: dict = None,
        cookies: dict = None,
        timeout: float = None,
        proxy: ProxyModel | str | None = None,
        request_data: RequestModel = None,
    ) -> Response:
        """
        发起GET请求
        Args:
            url: 地址
            params: url参数
            user_agent: ua
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
            proxy: 代理设置
            request_data: 其他的请求参数

        Returns:

        """
        request_data = request_data or RequestModel(url=url, method="GET")
        request_data.url = url
        request_data.method = "GET"
        request_data.url_params = params
        request_data.user_agent = user_agent
        request_data.headers = headers
        request_data.cookies = cookies
        request_data.timeout = timeout
        request_data.proxy = proxy

        return await self.request(request_data)

    async def post(
        self,
        url: str,
        params: dict = None,
        json_data: dict = None,
        form_data: dict[str, Any] | list[tuple[str]] | str | bytes | None = None,
        user_agent: str = None,
        headers: dict = None,
        cookies: dict = None,
        timeout: float = None,
        proxy: ProxyModel | str | None = None,
        request_data: RequestModel = None,
    ) -> Response:
        """
        发起POST请求
        Args:
            url: 地址
            params: url参数
            json_data:
            form_data:
            user_agent: ua
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
            proxy: 代理设置
            request_data: 其他的请求参数

        Returns:

        """
        request_data = request_data or RequestModel(url=url, method="POST")
        request_data.url = url
        request_data.method = "POST"
        request_data.url_params = params
        request_data.user_agent = user_agent
        request_data.headers = headers
        request_data.cookies = cookies
        request_data.timeout = timeout
        request_data.json_data = json_data
        request_data.form_data = form_data
        request_data.proxy = proxy

        return await self.request(request_data)
