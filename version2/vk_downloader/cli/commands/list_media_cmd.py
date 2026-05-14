import typer
import asyncio
from ...storage.database import get_session
from ...storage.models import MediaItem, Tag
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from rich.console import Console
from rich.table import Table
from datetime import datetime

app = typer.Typer()

@app.callback(invoke_without_command=True)
def list_media(
    ctx: typer.Context,
    source: int = typer.Option(None, help="owner_id источника"),
    type: str = typer.Option(None, help="photo/video/doc"),
    starred: bool = typer.Option(False, "--starred"),
    search: str = typer.Option(None, help="Полнотекстовый поиск"),
    page: int = typer.Option(1, min=1),
    per_page: int = typer.Option(20, min=1, max=100)
):
    """Просмотр медиатеки с фильтрацией"""
    asyncio.run(_list_media_async(ctx, source, type, starred, search, page, per_page))

async def _list_media_async(ctx, source, type, starred, search, page, per_page):
    async with get_session() as session:
        query = select(MediaItem).options(selectinload(MediaItem.tags))
        if source:
            query = query.filter(MediaItem.owner_id == source)
        if type:
            query = query.filter(MediaItem.media_type == type)
        if search:
            pattern = f"%{search}%"
            query = query.filter(MediaItem.title.ilike(pattern))
        if starred:
            query = query.join(MediaItem.tags).filter(Tag.tag_name == "starred")

        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await session.execute(query)
        items = result.scalars().all()

        table = Table(title=f"Медиатека (страница {page}, всего {total})")
        table.add_column("ID", style="dim")
        table.add_column("Тип")
        table.add_column("Название")
        table.add_column("Владелец")
        table.add_column("Дата")
        table.add_column("Статус")

        for item in items:
            star_mark = "★" if any(t.tag_name == "starred" for t in item.tags) else " "
            read_mark = "📖" if any(t.tag_name == "read" for t in item.tags) else " "
            date_str = datetime.fromtimestamp(item.date).strftime("%Y-%m-%d") if item.date else "—"
            table.add_row(str(item.id), item.media_type, item.title[:60],
                          str(item.owner_id), date_str, f"{star_mark} {read_mark}")

        console = Console()
        console.print(table)