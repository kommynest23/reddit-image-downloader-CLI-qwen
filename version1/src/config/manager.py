"""Configuration manager for loading and saving application settings."""

import os
from pathlib import Path
from typing import Optional
from pydantic import ValidationError
import yaml
from dotenv import load_dotenv

from .models import AppConfig, DownloadConfig, CacheConfig


class ConfigManager:
    """Manages application configuration using YAML and environment variables."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager with optional custom config path."""
        load_dotenv()
        
        if config_path is None:
            # Default to ~/.config/vk-cli/config.yaml
            config_home = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config'))
            self.config_path = config_home / 'vk-cli' / 'config.yaml'
        else:
            self.config_path = config_path
            
        # Create parent directories if they don't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create default
        self._config: Optional[AppConfig] = None
        self.load_config()

    @property
    def config(self) -> AppConfig:
        """Get loaded configuration, raise error if not loaded."""
        if self._config is None:
            raise ValueError("Configuration not loaded")
        return self._config

    def load_config(self) -> AppConfig:
        """Load configuration from YAML file, with fallback to defaults."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    raw_data = yaml.safe_load(f)
                
                if raw_data is None:
                    # Empty file, use defaults
                    raw_data = {}
                    
                # Override with environment variables if present
                raw_data = self._apply_env_overrides(raw_data)
                
                self._config = AppConfig(**raw_data)
            else:
                # Create with defaults
                self._config = AppConfig(
                    vk=self._get_default_vk_auth(),
                    download=DownloadConfig(),
                    cache=CacheConfig(),
                    favorite_users=[],
                    min_size_mb=0.0,
                    allow_private=False,
                    media_types=["photo", "video"]
                )
                
            return self.config
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")

    def save_config(self) -> None:
        """Save current configuration to YAML file."""
        if self._config is None:
            raise ValueError("No configuration to save")
            
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config.model_dump(), f, default_flow_style=False, allow_unicode=True)

    def _apply_env_overrides(self, config_dict: dict) -> dict:
        """Apply environment variable overrides to config dictionary."""
        # VK auth config
        if 'vk' not in config_dict:
            config_dict['vk'] = {}
            
        vk_env_mapping = {
            'service_token': 'VK_SERVICE_TOKEN',
            'api_version': 'VK_API_VERSION'
        }
        
        for key, env_var in vk_env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value:
                config_dict['vk'][key] = env_value
        
        # Other config values
        download_dir = os.getenv('VK_DOWNLOAD_DIR')
        if download_dir:
            config_dict.setdefault('download', {})['download_directory'] = download_dir
            
        return config_dict

    def _get_default_vk_auth(self):
        """Get default VK auth config from environment or empty values."""
        return {
            'service_token': os.getenv('VK_SERVICE_TOKEN', ''),
            'api_version': os.getenv('VK_API_VERSION', '5.199'),
        }