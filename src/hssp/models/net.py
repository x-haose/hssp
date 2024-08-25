from typing import Any

from pydantic import BaseModel, Field


class ProxyModel(BaseModel):
    http: str = ""
    https: str = ""


class RequestModel(BaseModel):
    url: str = Field(title="请求的地址")
    method: str = Field(title="请求的方法", default="GET")
    url_params: dict[str, Any] | None = Field(title="请求的url数据", default=None)
    form_data: dict[str, Any] | list[tuple[str]] | str | None = Field(title="form请求的数据", default=None)
    json_data: dict[str, Any] | None = Field(title="json请求的数据", default=None)
    allow_codes: list = Field(title="允许的状态码", default=list(range(200, 400)))

    # 下载这些属性, 默认值为设置中的值
    user_agent: str | None = Field(title="请求UA", default=None)
    headers: dict[str, Any] | None = Field(title="请求头", default=None)
    cookies: dict[str, Any] | None = Field(title="传递的cookies", default=None)
    timeout: int | None = Field(title="请求超时时间", default=None)
    proxy: ProxyModel | str | None = Field(title="代理设置", default=None)
    retrys_count: int | None = Field(title="重试次数", default=None)
    retrys_delay: int | None = Field(title="重试延时", default=None)
