from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DownloaderEnum(Enum):
    """
    下载器的枚举
    """

    AIOHTTP = "aiohttp"
    HTTPX = "httpx"
    REQUESTS = "requests"
    CURL_CFFI = "curl_cffi"


class RequestModel(BaseModel):
    """
    请求模型
    """

    url: str = Field(title="请求的地址")
    method: str = Field(title="请求的方法", default="GET")
    url_params: dict[str, Any] | None = Field(title="请求的url数据", default=None)
    form_data: dict[str, Any] | list[tuple[str]] | str | bytes | None = Field(title="form请求的数据", default=None)
    json_data: dict[str, Any] | None = Field(title="json请求的数据", default=None)
    # 下面这些属性, 默认值为设置中的值
    user_agent: str | None = Field(title="请求UA", default=None)
    headers: dict[str, Any] | None = Field(title="请求头", default=None)
    cookies: dict[str, Any] | None = Field(title="传递的cookies", default=None)
    timeout: int | None = Field(title="请求超时时间", default=None)
    proxy: str | None = Field(title="代理设置", default=None)
    retrys_count: int | None = Field(title="重试次数", default=None)
    retrys_delay: float | None = Field(title="重试延时", default=None)
