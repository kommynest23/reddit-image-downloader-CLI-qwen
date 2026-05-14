"""Search-related CLI commands."""

import asyncio
import typer
from datetime import datetime
from rich.console import Console
from rich.table import Table
from typing import Optional

from src.config.manager import ConfigManager
from src.api.client import VKAPIClient
from src.storage.database import DatabaseManager
from src.utils.logger import logger

app = typer.Typer()
console = Console()

@app.command()
def search(
    source: str = typer.Option(..., "--source", help="Source ID or shortname (e.g., vk, club123, tproger)"),
    media_type: str = typer.Option("photo", "--type", help="Type of media"),
    after: Optional[str] = typer.Option(None, "--after", help="Date >= (YYYY-MM-DD)"),
    before: Optional[str] = typer.Option(None, "--before", help="Date <= (YYYY-MM-DD)"),
    min_likes: int = typer.Option(0, "--min-likes", help="Minimum likes"),
    limit: int = typer.Option(30, "--limit", help="Results limit (1-200)"),
    save_filter: Optional[str] = typer.Option(None, "--save-filter", help="Save params as filter"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset")
):
    """Search for media in VK public communities/profiles."""
    
    # 1. Валидация дат
    after_date = before_date = None
    if after:
        try: after_date = datetime.strptime(after, "%Y-%m-%d").date()
        except ValueError: 
            console.print("[red]✗ Invalid --after format. Use YYYY-MM-DD[/red]"); raise typer.Exit(code=1)
    if before:
        try: before_date = datetime.strptime(before, "%Y-%m-%d").date()
        except ValueError: 
            console.print("[red]✗ Invalid --before format. Use YYYY-MM-DD[/red]"); raise typer.Exit(code=1)
    if after_date and before_date and after_date > before_date:
        console.print("[red]✗ --after must be earlier than --before[/red]"); raise typer.Exit(code=1)

    # 2. Запуск асинхронной логики
    try:
        asyncio.run(
            _execute_search(
                source, media_type, after_date, before_date, 
                min_likes, limit, save_filter, offset
            )
        )
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Search failed")
        console.print(f"[red]✗ Search error: {e}[/red]")
        raise typer.Exit(code=2)


async def _resolve_source(client: VKAPIClient, source: str) -> str:
    """Convert shortname/slug to VK API owner_id using official VK resolver."""
    # 1. Если уже числовой ID (с минусом или без) → возвращаем как есть
    if source.lstrip('-').isdigit():
        return source

    try:
        # 2. Официальный метод VK для резолва любых shortname
        resp = await client._make_request('utils.resolveScreenName', {'screen_name': source})
        
        if resp.get('response'):
            r = resp['response']
            obj_type = r.get('type')
            obj_id = r.get('object_id')

            # VK возвращает разные типы объектов
            if obj_type in ('group', 'page', 'event'):
                return f"-{obj_id}"  # Группы/паблики/встречи требуют минус
            elif obj_type == 'user':
                return str(obj_id)   # Пользователи → положительный ID
            elif obj_type == 'application':
                raise ValueError(f"Source '{source}' is an application, not supported")
            
    except Exception as e:
        # Если метод недоступен или вернул ошибку → пробуем fallback
        logger.debug(f"utils.resolveScreenName failed for '{source}': {e}")

    # 3. Если ничего не сработало → понятная ошибка
    raise ValueError(f"Source '{source}' not found or is invalid. Use numeric ID (e.g., -1, 12345) or exact shortname.")


async def _execute_search(source, media_type, after_date, before_date, min_likes, limit, save_filter, offset):
    """Internal async logic for search."""
    config_manager = ConfigManager()
    db_manager = DatabaseManager()
    client = VKAPIClient(config_manager)
    
    # 🔍 Resolve shortname to owner_id
    try:
        owner_id = await _resolve_source(client, source)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)
    
    # Fetch media
    if media_type == "photo":
        results = await client.get_user_photos(owner_id, count=limit, offset=offset)
    elif media_type == "video":
        posts = await client.get_wall_posts(owner_id, count=limit, offset=offset)
        results = [a.video for p in posts for a in p.attachments if a.type == "video" and a.video]
    elif media_type == "doc":
        posts = await client.get_wall_posts(owner_id, count=limit, offset=offset)
        results = [a.doc for p in posts for a in p.attachments if a.type == "doc" and a.doc]
    else:
        console.print(f"[red]✗ Unsupported type: {media_type}[/red]"); raise typer.Exit(code=1)

    # Filter
    filtered = []
    for item in results:
        if hasattr(item, 'date'):
            d = datetime.fromtimestamp(item.date).date()
            if after_date and d < after_date: continue
            if before_date and d > before_date: continue
        if min_likes > 0 and hasattr(item, 'likes') and item.likes:
            c = item.likes.get('count', 0) if isinstance(item.likes, dict) else 0
            if c < min_likes: continue
        filtered.append(item)

    # Save to DB
    for item in filtered:
        title = (getattr(item, 'title', '') or getattr(item, 'text', ''))[:255]
        desc = getattr(item, 'text', getattr(item, 'description', ''))
        if media_type == "photo":
            db_manager.add_media_item(f"photo_{item.owner_id}_{item.id}", item.owner_id, title, 
                                      item.get_largest_photo_url() or '', "photo", 
                                      width=getattr(item, 'width'), height=getattr(item, 'height'), 
                                      description=desc, is_private=False)
        elif media_type == "video":
            db_manager.add_media_item(f"video_{item.owner_id}_{item.id}", item.owner_id, title, 
                                      getattr(item, 'player', ''), "video", description=desc, is_private=False)
        elif media_type == "doc":
            db_manager.add_media_item(f"doc_{item.owner_id}_{item.id}", item.owner_id, title, 
                                      getattr(item, 'url', ''), "doc", size_bytes=getattr(item, 'size'), 
                                      description=desc, is_private=False)

    # Output
    table = Table(title=f"Found {len(filtered)} {media_type}s from '{source}' ({owner_id})")
    table.add_column("ID", style="dim"); table.add_column("Type"); table.add_column("Title", max_width=40)
    table.add_column("Owner ID"); table.add_column("Date"); table.add_column("Size")
    
    for item in filtered:
        d = datetime.fromtimestamp(item.date).date() if hasattr(item, 'date') else "N/A"
        sz = f"{item.size} bytes" if hasattr(item, 'size') and item.size else "N/A"
        table.add_row(str(getattr(item, 'id', 'N/A')), media_type, 
                      (getattr(item, 'title', '') or getattr(item, 'text', ''))[:40], 
                      str(getattr(item, 'owner_id', 'N/A')), str(d), sz)
    console.print(table)
    console.print(f"[green]✓ Found: {len(filtered)} of {limit}[/green]")

    if save_filter:
        db_manager.add_filter(save_filter, {"source": source, "type": media_type, "after": str(after_date), 
                                            "before": str(before_date), "min_likes": min_likes, "limit": limit})
        console.print(f"[green]✓ Saved filter '{save_filter}'[/green]")