from asyncio import Semaphore

from aiohttp import ClientSession, ClientTimeout, ContentTypeError, TCPConnector

from hssp.exception.exception import RequestStateException
from hssp.models.net import RequestModel
from hssp.network.downloader.base import DownloaderBase
from hssp.network.response import Response


class AiohttpDownloader(DownloaderBase):
    def __init__(self, sem: Semaphore, headers: dict = None, cookies=None):
        super().__init__(sem, headers, cookies)

        self.client = ClientSession(
            headers=self._default_headers,
            cookies=self._default_cookies,
            connector=TCPConnector(ssl=False),
            trust_env=True,
        )

    async def close(self):
        await self.client.close()

    def set_proxy(self, proxy: str): ...

    @property
    def cookies(self):
        return {cookie.key: cookie.value for cookie in self.client.cookie_jar}

    async def _download(self, request_data: RequestModel) -> Response:
        timeout = ClientTimeout(total=request_data.timeout)
        response = await self.client.request(
            method=request_data.method,
            url=request_data.url,
            params=request_data.url_params,
            data=request_data.form_data,
            json=request_data.json_data,
            cookies=request_data.cookies,
            headers=request_data.headers,
            proxy=request_data.proxy,
            timeout=timeout,
        )

        if not response.ok:
            raise RequestStateException(code=response.status)

        resp_headers = dict(response.headers)
        resp_content = await response.read()

        # 图片等二进制数据无法解码的，直接返回空字符串
        try:
            resp_text = await response.text()
        except UnicodeDecodeError:
            resp_text = ""

        resp_cookies = {name: cookie.value for name, cookie in response.cookies.items()}
        try:
            resp_json = await response.json()
        except (ContentTypeError, UnicodeDecodeError):
            resp_json = None

        return Response(
            url=response.url.__str__(),
            status_code=response.status,
            headers=resp_headers,
            cookies=resp_cookies,
            client_cookies=self.cookies,
            content=resp_content,
            text=resp_text,
            json=resp_json,
            request_data=request_data,
        )
