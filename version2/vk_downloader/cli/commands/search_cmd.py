import typer
import asyncio
from datetime import datetime
from typing import Optional
from ...api.client import VKAPIClient
from ...utils.resolver import resolve_screen_name
from ...storage.database import get_session, upsert_media_item
from loguru import logger

app = typer.Typer()

@app.callback(invoke_without_command=True)
def search(
    ctx: typer.Context,
    source: str = typer.Option(..., help="ID пользователя/сообщества или shortname (например vk)"),
    type: str = typer.Option("photo", help="Тип медиа: photo, video, doc"),
    limit: int = typer.Option(10, min=1, max=200),
    after: Optional[str] = typer.Option(None, help="Дата после (YYYY-MM-DD)"),
    before: Optional[str] = typer.Option(None, help="Дата до (YYYY-MM-DD)"),
    min_likes: Optional[int] = typer.Option(None, help="Минимальное число лайков")
):
    """Поиск медиа файлов и сохранение в БД"""
    asyncio.run(search_async(ctx, source, type, limit, after, before, min_likes))

async def search_async(ctx, source, type, limit, after, before, min_likes):
    """Асинхронная логика поиска, доступна для вызова из других команд."""
    config = ctx.obj["config"]
    client = VKAPIClient(config.vk.token, config.vk.api_version)

    # Разрешение owner_id
    if source.lstrip("-").isdigit():
        owner_id = int(source)
    else:
        owner_id = await resolve_screen_name(config.vk.token, source)
        if owner_id is None:
            typer.echo(f"❌ Не удалось разрешить screen_name: {source}", err=True)
            raise typer.Exit(1)

    def parse_date(d: str):
        return int(datetime.strptime(d, "%Y-%m-%d").timestamp())

    after_ts = parse_date(after) if after else None
    before_ts = parse_date(before) if before else None

    items = await client.search_media(owner_id, type, limit)
    await client.close()

    async with get_session() as session:
        for item in items:
            data = {
                "vk_id": item["id"],
                "owner_id": item["owner_id"],
                "title": item.get("title", ""),
                "url": item["url"],
                "media_type": item["media_type"],
                "width": item.get("width", 0),
                "height": item.get("height", 0),
                "size_bytes": item.get("size_bytes", 0),
                "date": item.get("date", 0),
            }
            await upsert_media_item(session, data)

    typer.echo(f"✅ Найдено и сохранено: {len(items)} элементов")