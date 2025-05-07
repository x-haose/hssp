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
from hssp.models.net import RequestModel
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

    def create_request_model(
        self,
        url: str,
        method: str,
        params: dict = None,
        json_data: dict = None,
        form_data: dict[str, Any] | list[tuple[str]] | str | bytes | None = None,
        user_agent: str = None,
        headers: dict = None,
        cookies: dict = None,
        timeout: float = None,
        proxy: str | None = None,
        retrys_count: int | None = None,
        retrys_delay: float | None = None,
    ) -> RequestModel:
        """
        创建并配置请求模型，应用默认设置
        Args:
            url: 地址
            method: 请求方法
            params: url参数
            json_data: json参数
            form_data: form参数。
            user_agent: ua 可以设置为 random, chrome, googlechrome, edge, firefox, ff, safari 或者具体ua
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
            proxy: 代理设置
            retrys_count: 重试次数
            retrys_delay: 重试延时

        Returns:
            返回请求模型
        """

        # 如果传入的UA是符合FakeUserAgent属性的，则使用FakeUserAgent获取一个假的UA
        user_agent = user_agent or settings.user_agent
        fake_user_agent_attrs = ["random", "chrome", "googlechrome", "edge", "firefox", "ff", "safari"]
        user_agent = getattr(FakeUserAgent(), user_agent) if user_agent in fake_user_agent_attrs else user_agent

        # 更新请求头的UA
        headers = headers or settings.headers or {}
        if user_agent:
            headers.update({"User-Agent": user_agent})

        # 处理 POST form的数据
        # 有些情况form数据的key是相同的，而且还要求顺序，这时使用dict就无法实现
        # 这里是把form数据手动转为经过编码的字符串类型
        if form_data and isinstance(form_data, list | dict):
            form_data = QueryParams(form_data).__str__()
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        # 创建请求模型
        request_data = RequestModel(
            url=url,
            method=method,
            url_params=params,
            json_data=json_data,
            form_data=form_data,
            user_agent=user_agent,
            headers=headers,
            cookies=cookies or settings.cookies or {},
            timeout=timeout if timeout is not None else settings.timeout,
            proxy=proxy if proxy is not None else settings.proxy,
            retrys_count=retrys_count if retrys_count is not None else settings.retrys_count,
            retrys_delay=retrys_delay if retrys_delay is not None else settings.retrys_delay,
        )

        return request_data

    async def request(self, data: RequestModel) -> Response:
        """
        发起异步请求
        Args:
            data: 请求参数

        Returns:
            返回响应
        """
        if data.proxy:
            self._downloader.set_proxy(data.proxy)

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
        proxy: str | None = None,
        retrys_count: int | None = None,
        retrys_delay: float | None = None,
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
            retrys_count: int | None = None,
            retrys_delay: float | None = None,

        Returns:

        """
        request_data = self.create_request_model(
            url=url,
            method="GET",
            params=params,
            user_agent=user_agent,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            retrys_count=retrys_count,
            retrys_delay=retrys_delay,
        )

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
        proxy: str | None = None,
        retrys_count: int | None = None,
        retrys_delay: float | None = None,
    ) -> Response:
        """
        发起POST请求
        Args:
            url: 地址
            params: url参数
            json_data: json参数
            form_data: form参数。
            user_agent: ua 可以设置为 random, chrome, googlechrome, edge, firefox, ff, safari 或者具体ua
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
            proxy: 代理设置
            retrys_count: 重试次数
            retrys_delay: 重试延时

        Returns:

        """
        request_data = self.create_request_model(
            url=url,
            method="POST",
            params=params,
            json_data=json_data,
            form_data=form_data,
            user_agent=user_agent,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            retrys_count=retrys_count,
            retrys_delay=retrys_delay,
        )

        return await self.request(request_data)

    async def head(
        self,
        url: str,
        params: dict = None,
        json_data: dict = None,
        form_data: dict[str, Any] | list[tuple[str]] | str | bytes | None = None,
        user_agent: str = None,
        headers: dict = None,
        cookies: dict = None,
        timeout: float = None,
        proxy: str | None = None,
        retrys_count: int | None = None,
        retrys_delay: float | None = None,
    ) -> Response:
        """
        发起HEAD请求
        Args:
            url: 地址
            params: url参数
            json_data: json参数
            form_data: form参数。
            user_agent: ua 可以设置为 random, chrome, googlechrome, edge, firefox, ff, safari 或者具体ua
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
            proxy: 代理设置
            retrys_count: 重试次数
            retrys_delay: 重试延时

        Returns:

        """
        request_data = self.create_request_model(
            url=url,
            method="HEAD",
            params=params,
            json_data=json_data,
            form_data=form_data,
            user_agent=user_agent,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            retrys_count=retrys_count,
            retrys_delay=retrys_delay,
        )

        return await self.request(request_data)
