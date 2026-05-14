import typer
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from ...storage.database import get_session
from ...storage.models import MediaItem
from sqlalchemy import select
from rich.progress import Progress
import httpx
from loguru import logger

app = typer.Typer()

@app.callback(invoke_without_command=True)
def download(
    ctx: typer.Context,
    ids: Optional[str] = typer.Option(None, help="ID записей через запятую"),
    from_filter: Optional[str] = typer.Option(None, help="Имя сохранённого фильтра"),
    dest: Optional[str] = typer.Option(None, help="Корневая папка для скачивания"),
    skip_existing: bool = typer.Option(False, "--skip-existing")
):
    """Скачать файлы по ID или фильтру"""
    asyncio.run(_download_async(ctx, ids, from_filter, dest, skip_existing))

async def _download_async(ctx, ids, from_filter, dest, skip_existing):
    config = ctx.obj["config"]
    download_root = dest or config.download.dest

    async with get_session() as session:
        query = select(MediaItem)
        if ids:
            id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
            query = query.filter(MediaItem.id.in_(id_list))
        elif from_filter:
            # применение фильтра — упрощённо
            pass
        else:
            typer.echo("Укажите --ids или --from-filter", err=True)
            raise typer.Exit(1)

        result = await session.execute(query)
        items = result.scalars().all()
        if not items:
            typer.echo("Нет элементов для скачивания")
            return

        async with httpx.AsyncClient() as client:
            with Progress() as progress:
                task = progress.add_task("Скачивание...", total=len(items))
                for item in items:
                    if not item.url:
                        logger.warning(f"Пропуск {item.id}: отсутствует URL")
                        progress.advance(task)
                        continue
                    try:
                        date_str = datetime.fromtimestamp(item.date).strftime("%Y-%m")
                        folder = Path(download_root) / str(item.owner_id) / date_str
                        folder.mkdir(parents=True, exist_ok=True)

                        if item.media_type == "photo":
                            ext = ".jpg"
                        elif item.media_type == "video":
                            ext = ".mp4"
                        else:
                            ext = os.path.splitext(item.url.split("?")[0])[1] or ".dat"
                        filename = f"{item.id}_{item.vk_id}{ext}"
                        file_path = folder / filename

                        if skip_existing and file_path.exists():
                            progress.advance(task)
                            continue

                        async with client.stream("GET", item.url) as response:
                            response.raise_for_status()
                            with open(file_path, "wb") as f:
                                async for chunk in response.aiter_bytes(1024*64):
                                    f.write(chunk)

                        item.download_path = str(file_path)
                        item.downloaded_at = datetime.utcnow()
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Ошибка скачивания {item.id}: {e}")
                    progress.advance(task)
        await session.commit()
    typer.echo("✅ Скачивание завершено")