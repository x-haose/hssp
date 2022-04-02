from dataclasses import dataclass, field
# from enum import Enum, auto
from typing import Union, Dict, Iterable

from httpx import AsyncClient


@dataclass
class BaseSetting:
    pass


@dataclass
class ReqSetting(BaseSetting):
    user_agent: str = field(default="")
    encoding: str = field(default="")
    headers: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)
    proxies: Union[Dict, str] = field(default=None)
    timeout: float = field(default=10)
    delay: int = field(default=0)
    retrys_count: int = field(default=10)
    retries_delay: int = field(default=0)
    allow_codes: list = field(default=None)
    session: AsyncClient = field(default=None)
    random_ua: bool = field(default=False)


@dataclass
class SpSetting(BaseSetting):
    concurrency: int = field(default=64)
    log_Level: str = field(default="DEBUG")
    out_path: Union[Iterable, str] = field(default_factory=str)


@dataclass
class Setting(SpSetting, ReqSetting):
    pass
