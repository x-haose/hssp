from abc import ABC, abstractmethod
from asyncio import Semaphore

from hssp.models.net import RequestModel
from hssp.network.response import Response


class DownloaderBase(ABC):
    def __init__(self, sem: Semaphore, headers: dict = None, cookies=None):
        """
        Args:
            sem: 信号量，控制并发
        """
        self.sem = sem
        self._default_headers = headers or {}
        self._default_cookies = cookies or {}

    async def download(self, request: RequestModel) -> Response:
        """
        下载方法，受信号量控制
        Args:
            request:

        Returns:

        """
        if self.sem:
            async with self.sem:
                return await self._download(request)
        else:
            return await self._download(request)

    @property
    @abstractmethod
    def cookies(self):
        """
        获取cookies
        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    def set_proxy(self, proxy: str):
        """
        设置代理，有些客户端不可以在请求时设置代理，所以提供一个入口
        Args:
            proxy: 代理

        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    async def _download(self, request: RequestModel) -> Response:
        """
        下载，子类实现具体的请求方法
        Args:
            request: 请求模型

        Returns:
            放回响应
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        """
        关闭下载器
        Returns:

        """
        raise NotImplementedError


class RenderDownloader(DownloaderBase, ABC):
    def put_back(self, driver):
        """
        释放浏览器对象
        """
        pass

    def close(self):
        """
        关闭浏览器
        """
        pass

    def close_all(self):
        """
        关闭所有浏览器
        """
        pass
