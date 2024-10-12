import logging
import sys
from pathlib import Path

from loguru import logger

# noinspection PyProtectedMember
from loguru._defaults import env

from hssp.logger.handler import InterceptHandler
from hssp.settings.settings import settings
from hssp.utils.classes import SingletonMeta


class Logger(metaclass=SingletonMeta):
    @classmethod
    def init_logger(
        cls,
        log_file: str | Path | None = None,
        hide_types: list[str] | None = None,
    ):
        log_format = env(
            "LOGURU_FORMAT",
            str,
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<red>{extra[type]: <10}</red> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )
        logger.remove()
        logger.add(sys.stdout, colorize=True, format=log_format)

        logfile = Path(log_file) if isinstance(log_file, str) else Path
        logger.add(logfile, backtrace=True, format=log_format)

        logging.basicConfig(handlers=[InterceptHandler(hide_types)], level=settings.log_mode, force=True)

    @classmethod
    def get_logger(cls, name: str):
        """
        获取一个带类型的日志
        Args:
            name: 日志类型

        Returns:

        """

        name = name.replace(".", " ☞ ")
        return logging.getLogger(name)


hssp_logger = Logger.get_logger("hssp")
