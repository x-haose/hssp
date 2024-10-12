from abc import ABCMeta
from configparser import ConfigParser
from pathlib import Path
from typing import Any

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings.sources import (
    ConfigFileSourceMixin,
    InitSettingsSource,
    JsonConfigSettingsSource,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)


class IniConfigSettingsSource(InitSettingsSource, ConfigFileSourceMixin):
    """
    A source class that loads variables from a Ini file
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        ini_file: Path | None = None,
        ini_file_encoding: str | None = None,
    ):
        self.ini_file_path = ini_file or settings_cls.model_config.get("json_file")
        self.ini_file_encoding = (
            ini_file_encoding if ini_file_encoding is not None else settings_cls.model_config.get("env_file_encoding")
        )
        self.ini_data = self._read_files(self.ini_file_path)
        super().__init__(settings_cls, self.ini_data)

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        with open(file_path, encoding=self.ini_file_encoding) as ini_file:
            file_content = ini_file.read()
            parser = ConfigParser()
            parser.read_string(file_content)
            return getattr(parser, "_sections", {}).get("settings", {})


class SettingsBase(BaseSettings, metaclass=ABCMeta):
    """
    项目设置的基类
    """

    model_config = SettingsConfigDict(
        extra="allow",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_file=(Path.cwd() / "configs").absolute() / ".env",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        自定义配置来源
        Args:
            settings_cls:
            init_settings: 初始化设置
            env_settings:环境变量设置
            dotenv_settings:
            file_secret_settings:加密文件设置

        Returns:

        """
        # 默认的设置
        default_settings = {
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        }
        root_dir = (Path.cwd() / "configs").absolute()

        # json 配置文件
        json_file = root_dir / "settings.json"
        if json_file.exists():
            json_settings_source = JsonConfigSettingsSource(settings_cls, json_file)
            default_settings.add(json_settings_source)

        # ini配置文件
        ini_file = root_dir / "settings.ini"
        if ini_file.exists():
            ini_settings_source = IniConfigSettingsSource(settings_cls, ini_file)
            default_settings.add(ini_settings_source)

        # yaml配置文件
        yaml_file = root_dir / "settings.yaml"
        if yaml_file.exists():
            yaml_settings_source = YamlConfigSettingsSource(settings_cls, yaml_file)
            default_settings.add(yaml_settings_source)

        # toml配置文件
        toml_file = root_dir / "settings.toml"
        if toml_file.exists():
            toml_settings_source = TomlConfigSettingsSource(settings_cls, toml_file)
            default_settings.add(toml_settings_source)

        return tuple(default_settings)
