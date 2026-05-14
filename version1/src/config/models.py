"""Configuration models using Pydantic."""

from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field


class VKAuthConfig(BaseModel):
    """VK API authentication configuration."""
    service_token: str = Field(..., description="VK service token for API access")
    api_version: str = Field("5.199", description="VK API version to use")


class DownloadConfig(BaseModel):
    """Download configuration options."""
    download_directory: Path = Field(
        default_factory=lambda: Path.home() / "Downloads" / "vk-media",
        description="Directory to store downloaded media"
    )
    max_concurrent_downloads: int = Field(4, ge=1, le=10, description="Max concurrent downloads")
    timeout_seconds: int = Field(30, ge=5, le=120, description="Request timeout in seconds")


class CacheConfig(BaseModel):
    """Cache configuration options."""
    enabled: bool = Field(True, description="Enable API response caching")
    ttl_hours: int = Field(1, ge=1, le=24, description="Cache TTL in hours")
    cache_directory: Path = Field(
        default_factory=lambda: Path.cwd() / "cache",
        description="Directory to store cached API responses"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    vk: VKAuthConfig
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    favorite_users: List[str] = Field(default=[], description="List of favorite user IDs or screen names")
    min_size_mb: float = Field(0.0, description="Minimum file size in MB to download")
    allow_private: bool = Field(False, description="Allow downloading private content")
    media_types: List[str] = Field(default=["photo", "video"], description="Allowed media types to download")