from asyncio import Semaphore

from requests import JSONDecodeError, Session
from requests.utils import cookiejar_from_dict, dict_from_cookiejar

from hssp.exception.exception import RequestStateException
from hssp.models.net import RequestModel
from hssp.network.downloader.base import DownloaderBase
from hssp.network.response import Response


class RequestsDownloader(DownloaderBase):
    def __init__(self, sem: Semaphore, headers: dict = None, cookies=None):
        super().__init__(sem, headers, cookies)

        self.client = Session()
        self.client.verify = False
        self.client.headers = self._default_headers
        self.client.cookies = cookiejar_from_dict(self._default_cookies)

    async def close(self):
        self.client.close()

    def set_proxy(self, proxy: str): ...

    @property
    def cookies(self):
        return dict_from_cookiejar(self.client.cookies)

    async def _download(self, request_data: RequestModel) -> Response:
        proxies = {"https": request_data.proxy, "http": request_data.proxy}

        response = self.client.request(
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
        resp_cookies = dict_from_cookiejar(response.cookies)
        try:
            resp_json = response.json()
        except (JSONDecodeError, UnicodeDecodeError):
            resp_json = None

        return Response(
            url=response.url.__str__(),
            status_code=response.status_code,
            headers=resp_headers,
            cookies=resp_cookies,
            client_cookies=self.cookies,
            content=resp_content,
            text=resp_text,
            json=resp_json,
            request_data=request_data,
        )
