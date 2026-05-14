import os
import yaml
from dotenv import load_dotenv
from .models import AppConfig, VKConfig

class ConfigManager:
    CONFIG_FILE = "config.yaml"

    @classmethod
    def load(cls, config_path: str = None) -> AppConfig:
        path = config_path or os.getenv("VK_DOWNLOADER_CONFIG", cls.CONFIG_FILE)
        load_dotenv()

        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        # Приоритет переменных окружения
        if "VK_TOKEN" in os.environ:
            data.setdefault("vk", {})["token"] = os.environ["VK_TOKEN"]
        if "DB_PATH" in os.environ:
            data.setdefault("database", {})["path"] = os.environ["DB_PATH"]
        if "DOWNLOAD_DEST" in os.environ:
            data.setdefault("download", {})["dest"] = os.environ["DOWNLOAD_DEST"]

        return AppConfig(**data)

    @classmethod
    def save(cls, config: AppConfig, config_path: str = None):
        path = config_path or cls.CONFIG_FILE
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config.model_dump(), f, allow_unicode=True)