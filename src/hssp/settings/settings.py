from typing import Any

from pydantic import BaseModel

from hssp.models.config import LogMode
from hssp.settings.setting_base import SettingsBase


class ProxyModel(BaseModel):
    http: str = ""
    https: str = ""


class Settings(SettingsBase):
    """
    设置
    """

    # 日志模式
    log_mode: LogMode = LogMode.INFO

    # 默认并发量
    concurrency: int = 32

    # 请求UA
    user_agent: str | None = None

    # 默认请求头
    headers: dict[str, Any] | None = None

    # 默认的cookies
    cookies: dict[str, Any] | None = None

    # 默认的请求超时时间
    timeout: int | None = 20

    # 默认的代理设置
    proxy: ProxyModel | str | None = None

    # 默认的重试次数
    retrys_count: int = 15

    # 默认每次重视之间的延迟，单位是秒
    retrys_delay: int = 0


settings = Settings()
