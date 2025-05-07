import asyncio
from json import JSONDecodeError

from curl_cffi.const import CurlHttpVersion
from curl_cffi.requests import AsyncSession

from hssp.exception.exception import RequestStateException
from hssp.models.net import RequestModel
from hssp.network.downloader.base import DownloaderBase
from hssp.network.response import Response


class CurlCffiDownloader(DownloaderBase):
    def __init__(self, sem: asyncio.Semaphore, headers: dict = None, cookies=None):
        super().__init__(sem, headers, cookies)

        self.client = AsyncSession(
            verify=False,
            headers=self._default_headers,
            cookies=self._default_cookies,
            impersonate="chrome110",
            http_version=CurlHttpVersion.V2_0,
        )

    async def close(self):
        await self.client.close()

    @property
    def cookies(self):
        return self.client.cookies.get_dict()

    def set_proxy(self, proxy: str): ...

    async def _download(self, request_data: RequestModel) -> Response:
        proxies = {"https": request_data.proxy, "http": request_data.proxy}

        # noinspection PyTypeChecker
        response = await self.client.request(
            method=request_data.method,
            url=request_data.url,
            params=request_data.url_params,
            data=request_data.form_data,
            json=request_data.json_data,
            cookies=request_data.cookies,
            headers=request_data.headers,
            proxies=proxies,
            timeout=request_data.timeout,
        )

        if not response.ok:
            raise RequestStateException(code=response.status_code)

        resp_headers = dict(response.headers)
        resp_content = response.content
        resp_text = response.text
        resp_cookies = response.cookies.get_dict()
        try:
            resp_json = response.json()
        except (JSONDecodeError, UnicodeDecodeError):
            resp_json = None

        return Response(
            url=response.url,
            status_code=response.status_code,
            headers=resp_headers,
            cookies=resp_cookies,
            client_cookies=self.cookies,
            content=resp_content,
            text=resp_text,
            json=resp_json,
            request_data=request_data,
        )
