import functools
from asyncio import Semaphore
from inspect import iscoroutinefunction
from typing import Type, Any

from httpx import QueryParams
from blinker import signal as get_signal
from blinker import Signal
from tenacity import (
    AsyncRetrying,
    Future,
    RetryCallState,
    stop_after_attempt,
    wait_fixed,
    wait_random,
)

from hssp.exception.exception import RequestStateException, RequestException
from hssp.logger.log import hssp_logger
from hssp.models.net import RequestModel
from hssp.network.downloader import DownloaderBase, HttpxDownloader
from hssp.network.response import Response


class Net:
    def __init__(
            self,
            downloader_cls: Type[DownloaderBase] = HttpxDownloader,
            sem: Semaphore = None,
            headers: dict = None,
            cookies: dict = None,
    ):
        """
        Args:
            downloader_cls: 使用的下载器
            sem: 信号量，控制并发
        """
        self._downloader = downloader_cls(sem, headers, cookies)
        self.logger = hssp_logger.getChild("net")

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
        async for receiver, result in self._send_signal(self.request_before_signal, data):
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
        async for receiver, result in self._send_signal(self.response_after_signal, resp):
            if result and isinstance(result, Response):
                return result

        return resp

    async def request(self, data: RequestModel) -> Response:
        """
        发起异步请求
        Args:
            data: 请求参数

        Returns:

        """
        if data.proxy:
            self._downloader.set_proxy(data.proxy)

        # 更新UA
        if data.user_agent:
            data.headers.update({"User-Agent": data.user_agent})

        # 设置请求头
        data.headers = data.headers or {}

        # 处理 POST form的数据
        # 有些情况form数据的key是相同的，而且还要求顺序，这时使用dict就无法实现
        # 这里是把form数据收到转为字符串类型
        if data.form_data and (isinstance(data.form_data, list) or isinstance(data.form_data, dict)):
            form_data = QueryParams(data.form_data).__str__()
            data.form_data = form_data
            data.headers['Content-Type'] = "application/x-www-form-urlencoded"

        if data.retrys_count < 1:
            return await self._request(data)

        # 设置重试的等候时间
        if data.retries_delay:
            wait = wait_fixed(data.retries_delay) + wait_random(0.1, 1)
        else:
            wait = wait_fixed(0)

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

        return await self.request(request_data)

    async def post(
            self,
            url: str,
            params: dict = None,
            json_data: dict = None,
            form_data: dict[str, Any] | list[tuple[str]] | None = None,
            user_agent: str = None,
            headers: dict = None,
            cookies: dict = None,
            timeout: float = None,
            request_data: RequestModel = None,
    ) -> Response:
        """
        发起GET请求
        Args:
            url: 地址
            params: url参数
            json_data:
            form_data:
            user_agent: ua
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
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

        return await self.request(request_data)
