from pydantic import BaseModel, Field
from typing import Optional

class VKConfig(BaseModel):
    token: str
    api_version: str = "5.199"

class DatabaseConfig(BaseModel):
    path: str = "media.db"

class DownloadConfig(BaseModel):
    dest: str = "./downloads"

class AppConfig(BaseModel):
    vk: VKConfig
    database: DatabaseConfig = DatabaseConfig()
    download: DownloadConfig = DownloadConfig()