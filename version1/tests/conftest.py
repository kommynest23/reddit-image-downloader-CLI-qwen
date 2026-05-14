"""Pytest configuration for VK Media Downloader tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from src.config.manager import ConfigManager
from src.api.client import VKAPIClient
from src.storage.database import DatabaseManager


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for testing."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.config = Mock()
    config_manager.config.vk = Mock()
    config_manager.config.vk.service_token = "test_token"
    config_manager.config.vk.api_version = "5.199"
    config_manager.config.download = Mock()
    config_manager.config.download.download_directory = "/tmp/test"
    config_manager.config.download.timeout_seconds = 30
    return config_manager


@pytest.fixture
def mock_vk_client():
    """Mock VKAPIClient for testing."""
    client = Mock(spec=VKAPIClient)
    return client


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager for testing."""
    db_manager = Mock(spec=DatabaseManager)
    return db_manager