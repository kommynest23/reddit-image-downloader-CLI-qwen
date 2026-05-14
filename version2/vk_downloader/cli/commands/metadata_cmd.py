import typer
import asyncio
from ...storage.database import get_session
from ...storage.models import MediaItem, Tag
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

app = typer.Typer()

@app.callback(invoke_without_command=True)
def metadata(
    ctx: typer.Context,
    id: int = typer.Option(..., help="ID записи"),
    star: bool = typer.Option(False, "--star"),
    unstar: bool = typer.Option(False, "--unstar"),
    read: bool = typer.Option(False, "--read"),
    unread: bool = typer.Option(False, "--unread"),
    tags: list[str] = typer.Option([], "--tag", help="Добавить теги"),
    tags_remove: list[str] = typer.Option([], "--tag-remove", help="Удалить теги"),
):
    """Управление тегами и статусами медиа"""
    asyncio.run(_metadata_async(ctx, id, star, unstar, read, unread, tags, tags_remove))

async def _metadata_async(ctx, id, star, unstar, read, unread, tags, tags_remove):
    async with get_session() as session:
        # Предзагружаем теги
        stmt = select(MediaItem).options(selectinload(MediaItem.tags)).filter(MediaItem.id == id)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            typer.secho(f"Запись с ID {id} не найдена", fg="red")
            raise typer.Exit(1)

        if star:
            if not any(t.tag_name == "starred" for t in item.tags):
                item.tags.append(Tag(tag_name="starred"))
                logger.info(f"Starred {id}")
        if unstar:
            for t in item.tags:
                if t.tag_name == "starred":
                    session.delete(t)
        if read:
            if not any(t.tag_name == "read" for t in item.tags):
                item.tags.append(Tag(tag_name="read"))
                logger.info(f"Read {id}")
        if unread:
            for t in item.tags:
                if t.tag_name == "read":
                    session.delete(t)

        for tag_name in tags:
            if not any(t.tag_name == tag_name for t in item.tags):
                item.tags.append(Tag(tag_name=tag_name))
        for tag_name in tags_remove:
            for t in item.tags:
                if t.tag_name == tag_name:
                    session.delete(t)

        await session.commit()
    typer.echo("✅ Метаданные обновлены")