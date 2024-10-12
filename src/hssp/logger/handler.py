import logging
import logging.config
import sys
from types import FrameType

from loguru import logger


class InterceptHandler(logging.StreamHandler):
    def __init__(self, hide_types: list[str] | None = None):
        super().__init__()
        self.hide_types = [
            hide_type if "###" in hide_type else f"{hide_type}###ALL" for hide_type in hide_types or [] if hide_type
        ]

    def emit(self, record: logging.LogRecord):
        # Get corresponding Loguru level if it exists
        try:
            level: int | str = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        # noinspection PyProtectedMember,PyUnresolvedReferences
        frame: FrameType | None = sys._getframe(6)
        depth: int = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        fmt = "%(message)s"
        formatter = logging.Formatter(fmt=fmt)
        msg = formatter.format(record)

        # 按照类型去过滤掉不想看到的日志
        record_name = f"{record.name.strip()}###{record.levelname}"
        for hide_type in self.hide_types:
            hide_type_name, hide_type_level = hide_type.split("###")
            if not record_name.startswith(hide_type_name):
                continue
            if hide_type_level == "ALL" or hide_type == record_name:
                return

        record.name = record.name.replace(".", " ☞ ").strip()
        etxra_data = {"type": record.name}
        logger.bind(**etxra_data).opt(depth=depth, exception=record.exc_info).log(level, msg)
