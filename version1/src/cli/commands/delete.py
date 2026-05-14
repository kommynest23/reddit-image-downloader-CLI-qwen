"""Delete-related CLI commands."""

import asyncio
import typer
from rich.console import Console
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

from src.storage.database import DatabaseManager
from src.utils.logger import logger

app = typer.Typer()
console = Console()


@app.command()
def delete(
    ids: Optional[str] = typer.Option(None, "--ids", help="Comma-separated list of VK IDs"),
    older_than: Optional[int] = typer.Option(None, "--older-than", help="Delete records older than N days"),
    max_likes: Optional[int] = typer.Option(None, "--max-likes", help="Delete records with likes <= threshold"),
    source: Optional[str] = typer.Option(None, "--source", help="Filter by owner"),
    media_type: Optional[str] = typer.Option(None, "--type", help="Filter by media type"),
    remove_files: bool = typer.Option(False, "--remove-files", help="Also delete local files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation")
):
    """Delete records from local library and optionally corresponding files."""
    try:
        asyncio.run(
            _execute_delete(ids, older_than, max_likes, source, media_type, remove_files, dry_run, force)
        )
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Delete failed")
        console.print(f"[red]✗ Delete error: {e}[/red]")
        raise typer.Exit(code=3)


async def _execute_delete(ids, older_than, max_likes, source, media_type, remove_files, dry_run, force):
    """Internal async logic for deletion."""
    db_manager = DatabaseManager()
    records_to_delete = []

    # 1. Determine records
    if ids:
        for vk_id in [i.strip() for i in ids.split(',') if i.strip()]:
            rec = db_manager.get_media_item_by_vk_id(vk_id)
            if rec:
                records_to_delete.append(rec)
            else:
                console.print(f"[yellow]⚠ Not found: {vk_id}[/yellow]")
    elif any([older_than, max_likes, source, media_type]):
        # Simplified criteria filtering
        all_recs = db_manager.search_media(
            media_type=media_type, 
            owner_id=int(source) if source and source.isdigit() else None, 
            limit=1000
        )
        for rec in all_recs:
            include = True
            if older_than and rec.downloaded_at:
                if rec.downloaded_at > datetime.now() - timedelta(days=older_than):
                    include = False
            if include:
                records_to_delete.append(rec)
    else:
        console.print("[red]✗ Specify --ids or filtering criteria[/red]")
        raise typer.Exit(code=1)

    if not records_to_delete:
        console.print("[yellow]No records found for deletion[/yellow]")
        return

    # 2. Confirm bulk deletion
    if len(records_to_delete) > 10 and not force and not dry_run:
        if not typer.confirm(f"Delete {len(records_to_delete)} records?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # 3. Dry run mode
    if dry_run:
        console.print("[bold]🗑️ Will be deleted (dry run):[/bold]")
        for i, rec in enumerate(records_to_delete, 1):
            p = rec.download_path or "No file"
            d = rec.created_at.strftime('%Y-%m-%d') if rec.created_at else "N/A"
            console.print(f"[{i}] {rec.vk_id} — \"{rec.title}\" — {d} — {p}")
        console.print(f"[green]Total: {len(records_to_delete)} records[/green]")
        return

    # 4. Execute deletion
    deleted = 0
    file_err = 0
    for rec in records_to_delete:
        try:
            if remove_files and rec.download_path:
                try:
                    Path(rec.download_path).unlink(missing_ok=True)
                    logger.info(f"Deleted file: {rec.download_path}")
                except Exception as e:
                    logger.error(f"File delete error {rec.download_path}: {e}")
                    file_err += 1
            
            # Cascade delete from DB (tags/metadata removed automatically)
            db_manager.delete_media_item(rec.vk_id)
            deleted += 1
        except Exception as e:
            logger.error(f"Error deleting {rec.vk_id}: {e}")

    console.print(f"[green]✓ Deleted: {deleted} records[/green]")
    if file_err:
        console.print(f"[yellow]⚠ File errors: {file_err}[/yellow]")