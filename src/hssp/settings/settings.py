from hssp.models.config import LogMode
from hssp.settings.setting_base import SettingsBase


class Settings(SettingsBase):
    """
    设置
    """

    # 日志模式
    log_mode: LogMode = LogMode.INFO

    # 默认并发量
    concurrency: int = 32


settings = Settings()
