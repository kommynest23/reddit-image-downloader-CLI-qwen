import typer
import asyncio
from ...config.manager import ConfigManager
from ...api.client import VKAPIClient
from loguru import logger

app = typer.Typer()

@app.command("set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)):
    """Установить значение параметра, например vk.token"""
    config = ConfigManager.load()
    parts = key.split(".")
    obj = config.model_dump()
    d = obj
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    existing = d.get(parts[-1])
    if isinstance(existing, int):
        value = int(value)
    elif isinstance(existing, float):
        value = float(value)
    elif isinstance(existing, bool):
        value = value.lower() in ("true", "yes", "1")
    d[parts[-1]] = value
    new_config = type(config)(**obj)
    ConfigManager.save(new_config)
    logger.info(f"Параметр {key} установлен в {value}")

@app.command("get")
def config_get(key: str = typer.Argument(...)):
    """Получить значение параметра"""
    config = ConfigManager.load()
    parts = key.split(".")
    obj = config.model_dump()
    for part in parts:
        obj = obj[part]
    typer.echo(obj)

@app.command("auth-status")
def auth_status():
    """Проверить валидность токена"""
    config = ConfigManager.load()

    async def _check():
        client = VKAPIClient(config.vk.token, config.vk.api_version)
        try:
            # Используем users.get с явным user_ids, чтобы сервисный ключ сработал
            resp = await client._request("users.get", {"user_ids": "1"})
            # resp должно быть списком
            return resp
        finally:
            await client.close()

    try:
        users = asyncio.run(_check())
    except Exception as e:
        typer.secho(f"❌ Ошибка соединения или API: {e}", fg="red")
        raise typer.Exit(2)

    if not users or not isinstance(users, list):
        typer.secho("❌ Не удалось получить данные — возможно, токен недействителен или ограничен", fg="red")
        raise typer.Exit(1)

    typer.secho("✅ Токен действителен", fg="green")