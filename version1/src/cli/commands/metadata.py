"""Metadata-related CLI commands."""

import typer
from rich.console import Console
from rich.table import Table
import webbrowser
from typing import Optional

from src.config.manager import ConfigManager
from src.storage.database import DatabaseManager
from src.utils.logger import logger

app = typer.Typer()
console = Console()


@app.command()
def metadata(
    vk_id: str = typer.Option(..., "--id", help="VK ID of media (e.g., photo_123_456)"),
    star: bool = typer.Option(False, "--star", help="Star the media item"),
    unstar: bool = typer.Option(False, "--unstar", help="Unstar the media item"),
    read: bool = typer.Option(False, "--read", help="Mark as read"),
    unread: bool = typer.Option(False, "--unread", help="Mark as unread"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Add tags (comma-separated)"),
    tags_remove: Optional[str] = typer.Option(None, "--tags-remove", help="Remove specified tags"),
    open_in_browser: bool = typer.Option(False, "--open", help="Open original post in browser"),
    show: bool = typer.Option(False, "--show", help="Show current metadata without changes")
):
    """Manage metadata: tags, statuses (starred/read), open in browser."""
    try:
        db_manager = DatabaseManager()
        
        # Find the media item
        media_item = db_manager.get_media_item_by_vk_id(vk_id)
        if not media_item:
            console.print(f"[red]✗ Media with ID '{vk_id}' not found[/red]")
            raise typer.Exit(code=1)
        
        # Check for conflicting flags
        if star and unstar:
            console.print("[red]✗ Cannot use both --star and --unstar[/red]")
            raise typer.Exit(code=1)
        if read and unread:
            console.print("[red]✗ Cannot use both --read and --unread[/red]")
            raise typer.Exit(code=1)
        
        changes_made = []
        
        # Handle starring
        if star:
            db_manager.add_metadata(media_item.id, "is_starred", "1")
            changes_made.append("set starred")
        elif unstar:
            db_manager.add_metadata(media_item.id, "is_starred", "0")
            changes_made.append("removed starred")
        
        # Handle read status
        if read:
            db_manager.add_metadata(media_item.id, "is_read", "1")
            changes_made.append("set read")
        elif unread:
            db_manager.add_metadata(media_item.id, "is_read", "0")
            changes_made.append("set unread")
        
        # Handle tags
        if tags:
            for tag_name in [t.strip() for t in tags.split(",") if t.strip()]:
                db_manager.add_tag(media_item.id, tag_name)
            changes_made.append(f"added {len(tags.split(','))} tags")
        
        if tags_remove:
            console.print(f"[yellow]⚠ Removing tags functionality not fully implemented in this example[/yellow]")
            # In a real implementation, you'd need to remove tags from the tags table
            changes_made.append(f"attempted to remove tags: {tags_remove}")
        
        # Open in browser
        if open_in_browser:
            # Construct VK post URL - this is a simplified version
            # A real implementation would need to determine the correct post URL
            post_url = f"https://vk.com/id{media_item.owner_id}"
            webbrowser.open(post_url)
            console.print(f"[green]✓ Opening {post_url} in browser[/green]")
        
        # Show metadata
        if show or not changes_made:
            display_metadata(media_item, db_manager)
        else:
            console.print(f"[green]✓ Updated: {' '.join(changes_made)}[/green]")
        
    except Exception as e:
        logger.error(f"Error managing metadata: {e}")
        console.print(f"[red]✗ Error managing metadata: {e}[/red]")
        raise typer.Exit(code=3)


def display_metadata(media_item, db_manager):
    """Display current metadata for a media item."""
    console.print(f"[bold]📷 {media_item.vk_id}[/bold]")
    
    table = Table(show_header=False, box=None)
    table.add_column("Field", style="dim", width=15)
    table.add_column("Value")
    
    table.add_row("Title:", media_item.title or "N/A")
    table.add_row("Description:", media_item.description or "N/A")
    table.add_row("Type:", media_item.media_type)
    table.add_row("Owner:", str(media_item.owner_id))
    table.add_row("URL:", media_item.url)
    table.add_row("Path:", media_item.download_path or "Not downloaded")
    table.add_row("Created:", media_item.created_at.strftime('%Y-%m-%d %H:%M') if media_item.created_at else "N/A")
    
    console.print(table)
    
    # In a real implementation, you'd query the tags and metadata tables
    console.print("\n[yellow]Tags: [design] [reference][/yellow]")  # Placeholder
    console.print("[yellow]Statuses: ★ 📖[/yellow]")  # Placeholder