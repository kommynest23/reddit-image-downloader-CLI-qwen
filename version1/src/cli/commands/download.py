"""Download-related CLI commands."""

import asyncio
import os
import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn
from typing import Optional

from src.config.manager import ConfigManager
from src.storage.database import DatabaseManager
from src.utils.logger import logger
from src.utils.helpers import sanitize_filename
import httpx

app = typer.Typer()
console = Console()


@app.command()
def download(
    ids: Optional[str] = typer.Option(None, "--ids", help="Comma-separated list of VK IDs (e.g., photo_123_456,doc_789_012)"),
    from_filter: Optional[str] = typer.Option(None, "--from-filter", help="Name of saved filter to download from"),
    max_concurrent: int = typer.Option(4, "--max-concurrent", min=1, max=10, help="Max parallel downloads"),
    dest: Optional[str] = typer.Option(None, "--dest", help="Destination directory for downloads"),
    skip_existing: bool = typer.Option(False, "--skip-existing", help="Skip files already present on disk"),
    verify_hash: bool = typer.Option(False, "--verify-hash", help="Verify SHA256 hash when --skip-existing")
):
    """Asynchronously download media files by list of VK IDs or from a saved filter."""
    
    # Запуск асинхронной логики
    try:
        asyncio.run(
            _execute_download(ids, from_filter, max_concurrent, dest, skip_existing, verify_hash)
        )
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Download failed")
        console.print(f"[red]✗ Download error: {e}[/red]")
        raise typer.Exit(code=2)


async def _execute_download(ids, from_filter, max_concurrent, dest, skip_existing, verify_hash):
    """Internal async logic for downloading."""
    config_manager = ConfigManager()
    db_manager = DatabaseManager()
    
    # Определяем список ID
    id_list = []
    if ids:
        id_list = [i.strip() for i in ids.split(',') if i.strip()]
    elif from_filter:
        # TODO: Логика получения ID из фильтра (пока заглушка)
        console.print("[yellow]⚠ --from-filter пока не реализован, используйте --ids[/yellow]")
        raise typer.Exit(code=1)
    else:
        console.print("[red]✗ Specify either --ids or --from-filter[/red]")
        raise typer.Exit(code=1)

    if not id_list:
        console.print("[red]✗ No valid IDs to download[/red]")
        raise typer.Exit(code=1)

    # Папка загрузки
    download_dir = Path(dest) if dest else Path(config_manager.config.download.download_directory)
    download_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent)
    downloaded_count = 0
    skipped_count = 0
    errors_count = 0

    async def download_single(vk_id: str):
        nonlocal downloaded_count, skipped_count, errors_count
        async with semaphore:
            try:
                # 1. Получаем инфо из БД
                item = db_manager.get_media_item_by_vk_id(vk_id)
                if not item:
                    console.print(f"[red]✗ Item {vk_id} not found in DB[/red]")
                    errors_count += 1
                    return

                # 2. Формируем путь
                owner_dir = download_dir / str(item.owner_id)
                date_dir = owner_dir / f"{item.created_at.strftime('%Y-%m')}"
                date_dir.mkdir(parents=True, exist_ok=True)

                ext = Path(item.url).suffix or '.jpg'
                filename = sanitize_filename(f"{vk_id}{ext}")
                filepath = date_dir / filename

                # 3. Проверка существования
                if skip_existing and filepath.exists():
                    console.print(f"[yellow]⚠ Skipped existing: {filename}[/yellow]")
                    skipped_count += 1
                    # Отмечаем как скачанное, если вдруг забыли
                    if not item.downloaded_at:
                        db_manager.mark_as_downloaded(vk_id, str(filepath))
                    return

                # 4. Скачивание
                async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                    async with client.stream("GET", item.url) as response:
                        response.raise_for_status()
                        total = int(response.headers.get("Content-Length", 0))
                        
                        with Progress(
                            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                            BarColumn(bar_width=None),
                            "[progress.percentage]{task.percentage:>3.1f}%",
                            "•", TransferSpeedColumn(), "•", TimeRemainingColumn(),
                        ) as progress:
                            task = progress.add_task("Download", filename=filename, total=total)
                            with open(filepath, "wb") as f:
                                async for chunk in response.aiter_bytes(chunk_size=8192):
                                    f.write(chunk)
                                    progress.update(task, advance=len(chunk))

                # 5. Обновление БД
                db_manager.mark_as_downloaded(vk_id, str(filepath))
                downloaded_count += 1
                console.print(f"[green]✓ Downloaded: {filename}[/green]")

            except Exception as e:
                console.print(f"[red]✗ Failed {vk_id}: {e}[/red]")
                errors_count += 1

    # Запускаем параллельно
    await asyncio.gather(*[download_single(vid) for vid in id_list])

    # Итог
    console.print(f"\n[bold]Summary:[/bold] Downloaded: {downloaded_count}, Skipped: {skipped_count}, Errors: {errors_count}")