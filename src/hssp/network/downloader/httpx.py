from asyncio import Semaphore
from json import JSONDecodeError

from httpx import AsyncClient

from hssp.exception.exception import RequestStateException
from hssp.models.net import RequestModel
from hssp.network.downloader.base import DownloaderBase
from hssp.network.response import Response


class HttpxDownloader(DownloaderBase):
    def __init__(self, sem: Semaphore, headers: dict = None, cookies=None):
        super().__init__(sem, headers, cookies)

        self.client = AsyncClient(
            verify=False,
            http2=True,
            headers=self._default_headers,
            cookies=self._default_cookies,
        )

    async def close(self):
        await self.client.aclose()

    @property
    def cookies(self):
        return {cookie.name: cookie.value for cookie in self.client.cookies.jar}

    def set_proxy(self, proxy: str):
        self.client = AsyncClient(headers=self.client.headers, cookies=self.client.cookies, proxy=proxy, verify=False)

    async def _download(self, request_data: RequestModel) -> Response:
        request = self.client.build_request(
            request_data.method,
            request_data.url,
            headers=request_data.headers,
            timeout=request_data.timeout,
            cookies=request_data.cookies,
            params=request_data.url_params,
            data=request_data.form_data,
            json=request_data.json_data,
        )
        response = await self.client.send(request, follow_redirects=True)
        if not response.is_success:
            raise RequestStateException(code=response.status_code)

        try:
            json_data = response.json()
        except (JSONDecodeError, UnicodeDecodeError):
            json_data = None

        # 图片等二进制数据无法解码的，直接返回空字符串
        try:
            text_data = response.text
        except UnicodeDecodeError:
            text_data = ""

        resp_cookies = {cookie.name: cookie.value for cookie in response.cookies.jar}
        return Response(
            url=response.url.__str__(),
            status_code=response.status_code,
            headers=response.headers,
            cookies=resp_cookies,
            client_cookies=self.cookies,
            content=response.content,
            text=text_data,
            json=json_data,
            request_data=request_data,
        )
