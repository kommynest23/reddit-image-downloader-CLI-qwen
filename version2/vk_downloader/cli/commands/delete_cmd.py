import typer
import asyncio
import os
from datetime import datetime, timedelta
from ...storage.database import get_session
from ...storage.models import MediaItem
from sqlalchemy import select
from loguru import logger

app = typer.Typer()

@app.callback(invoke_without_command=True)
def delete(
    ctx: typer.Context,
    ids: str = typer.Option(None, help="ID записей через запятую"),
    older_than: int = typer.Option(None, help="Удалить записи старше N дней"),
    remove_files: bool = typer.Option(False, "--remove-files"),
    dry_run: bool = typer.Option(False, "--dry-run")
):
    """Удалить записи из БД и (опционально) файлы"""
    asyncio.run(_delete_async(ctx, ids, older_than, remove_files, dry_run))

async def _delete_async(ctx, ids, older_than, remove_files, dry_run):
    async with get_session() as session:
        query = select(MediaItem)
        if ids:
            id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
            query = query.filter(MediaItem.id.in_(id_list))
        elif older_than:
            cutoff = datetime.utcnow() - timedelta(days=older_than)
            query = query.filter(MediaItem.created_at < cutoff)
        else:
            typer.echo("Укажите --ids или --older-than", err=True)
            raise typer.Exit(1)

        result = await session.execute(query)
        items = result.scalars().all()
        if not items:
            typer.echo("Нет записей для удаления")
            return

        typer.echo(f"Будет удалено записей: {len(items)}")
        if dry_run:
            for item in items:
                typer.echo(f"  - ID {item.id}: {item.title}")
            return

        if not typer.confirm("Удалить безвозвратно?"):
            raise typer.Abort()

        for item in items:
            if remove_files and item.download_path and os.path.exists(item.download_path):
                try:
                    os.remove(item.download_path)
                    logger.info(f"Удалён файл {item.download_path}")
                except OSError as e:
                    logger.error(f"Не удалось удалить файл: {e}")
            await session.delete(item)
        await session.commit()
    typer.echo("✅ Удаление выполнено")