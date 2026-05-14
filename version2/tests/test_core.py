import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from vk_downloader.api.client import VKAPIClient, VKAPIError
from vk_downloader.config.models import AppConfig, VKConfig

@pytest.fixture
def config():
    return AppConfig(vk=VKConfig(token="test_token"))

@pytest.mark.asyncio
async def test_vk_client_users_get_success():
    client = VKAPIClient("token")
    mock_response = {"response": [{"id": 1}]}
    with patch.object(client.client, "get", AsyncMock(return_value=MagicMock(
        status_code=200, json=MagicMock(return_value=mock_response)
    ))):
        users = await client.users_get()
        assert users == [{"id": 1}]
    await client.close()

@pytest.mark.asyncio
async def test_vk_client_error():
    client = VKAPIClient("bad_token")
    error_resp = {"error": {"error_code": 5, "error_msg": "Auth failed"}}
    with patch.object(client.client, "get", AsyncMock(return_value=MagicMock(
        status_code=200, json=MagicMock(return_value=error_resp)
    ))):
        with pytest.raises(VKAPIError) as exc_info:
            await client.users_get()
        assert exc_info.value.code == 5
    await client.close()

@pytest.mark.asyncio
async def test_upsert_media_item():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from vk_downloader.storage.models import Base, MediaItem
    from vk_downloader.storage.database import init_db, get_session, upsert_media_item

    # Создаём in-memory SQLite
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import vk_downloader.storage.database as db_mod
    db_mod.engine = engine
    db_mod.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with get_session() as session:
        data = {
            "vk_id": 123,
            "owner_id": -1,
            "url": "http://example.com",
            "media_type": "photo",
            "title": "test",
            "width": 100,
            "height": 200,
            "size_bytes": 1024,
            "date": 1672531200
        }
        item = await upsert_media_item(session, data)
        assert item.id is not None
        # Повторный вызов должен обновить, а не создать дубликат
        data["title"] = "updated"
        item2 = await upsert_media_item(session, data)
        assert item2.id == item.id
        assert item2.title == "updated"

    await engine.dispose()

def test_config_load():
    from vk_downloader.config.manager import ConfigManager
    import os
    # Сохраняем оригинальные переменные
    orig_token = os.environ.get("VK_TOKEN")
    os.environ["VK_TOKEN"] = "env_token"
    # Если config.yaml существует, он будет использован, но мы проверяем приоритет env
    config = ConfigManager.load("nonexistent.yaml")
    assert config.vk.token == "env_token"
    if orig_token is not None:
        os.environ["VK_TOKEN"] = orig_token
    else:
        del os.environ["VK_TOKEN"]