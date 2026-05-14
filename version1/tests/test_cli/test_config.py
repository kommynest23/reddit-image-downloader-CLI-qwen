"""Tests for config CLI commands."""

import pytest
from typer.testing import CliRunner
from src.cli.commands.config import app
from unittest.mock import Mock, patch


runner = CliRunner()


def test_config_set_get_valid(mock_config_manager):
    """Test setting and getting a valid configuration value."""
    with patch('src.cli.commands.config.ConfigManager', return_value=mock_config_manager):
        # Test setting a value
        result = runner.invoke(app, ["set", "download.max_concurrent_downloads", "6"])
        assert result.exit_code == 0
        assert "Установлено:" in result.output

        # Test getting a value
        result = runner.invoke(app, ["get", "download.max_concurrent_downloads"])
        assert result.exit_code == 0


def test_config_set_invalid_key(mock_config_manager):
    """Test attempting to set a non-existent config key."""
    with patch('src.cli.commands.config.ConfigManager', return_value=mock_config_manager):
        result = runner.invoke(app, ["set", "nonexistent.key", "value"])
        assert result.exit_code == 1
        assert "Invalid config key" in result.output


@pytest.mark.asyncio
async def test_auth_status_valid_token(mock_config_manager, mock_vk_client):
    """Test token validation: successful response from users.get."""
    with patch('src.cli.commands.config.ConfigManager', return_value=mock_config_manager):
        with patch('src.cli.commands.config.VKAPIClient', return_value=mock_vk_client):
            with patch('src.cli.commands.config.test_token', return_value=True):
                result = runner.invoke(app, ["auth", "status"])
                assert result.exit_code == 0
                assert "Token is valid" in result.output


@pytest.mark.asyncio
async def test_auth_status_invalid_token(mock_config_manager):
    """Test token validation: access denied error."""
    with patch('src.cli.commands.config.ConfigManager', return_value=mock_config_manager):
        with patch('src.cli.commands.config.VKAPIClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            with patch('src.cli.commands.config.test_token', return_value=False):
                result = runner.invoke(app, ["auth", "status"])
                assert result.exit_code == 2
                assert "Token validation failed" in result.output