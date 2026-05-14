"""Filter-related CLI commands."""

import asyncio
import json
import typer
from rich.console import Console
from rich.table import Table
from typing import Optional

from src.config.manager import ConfigManager
from src.storage.database import DatabaseManager
from src.utils.logger import logger
# Импортируем внутреннюю логику поиска для переиспользования
from src.cli.commands.search import _execute_search

app = typer.Typer()
console = Console()


@app.command()
def create(
    name: str = typer.Option(..., "--name", help="Unique name for the filter"),
    source: str = typer.Option(..., "--source", help="Source ID or shortname (e.g., club12345)"),
    media_type: str = typer.Option("photo", "--type", help="Type of media", 
                                   case_sensitive=False),
    after: Optional[str] = typer.Option(None, "--after", help="Filter: upload date >= (YYYY-MM-DD)"),
    before: Optional[str] = typer.Option(None, "--before", help="Filter: upload date <= (YYYY-MM-DD)"),
    min_likes: int = typer.Option(0, "--min-likes", help="Minimum number of likes"),
    limit: int = typer.Option(30, "--limit", help="Number of results (1-200)", min=1, max=200)
):
    """Create a named filter with search parameters."""
    try:
        db_manager = DatabaseManager()
        
        # Check if filter name already exists
        existing_filter = db_manager.get_filter_by_name(name)
        if existing_filter:
            console.print(f"[red]✗ Filter '{name}' already exists[/red]")
            raise typer.Exit(code=1)
        
        # Create parameters dict
        params = {
            "source": source,
            "type": media_type,
            "after": after,
            "before": before,
            "min_likes": min_likes,
            "limit": limit
        }
        
        # Save filter
        db_manager.add_filter(name, params)
        
        console.print(f"[green]✓ Filter '{name}' created with parameters:[/green]")
        console.print(json.dumps(params, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error creating filter: {e}")
        console.print(f"[red]✗ Error creating filter: {e}[/red]")
        raise typer.Exit(code=3)


@app.command(name="list")  # Переименовываем в list, чтобы было vk-downloader filter list
def list_filters():
    """List all saved filters."""
    try:
        db_manager = DatabaseManager()
        
        filters = db_manager.get_all_filters()
        
        if not filters:
            console.print("[yellow]No saved filters found[/yellow]")
            return
        
        table = Table(title="Saved Filters")
        table.add_column("Name", style="dim")
        table.add_column("Type")
        table.add_column("Source", style="magenta")
        table.add_column("Date Range", style="blue")
        table.add_column("Min Likes")
        
        for fltr in filters:
            try:
                params = json.loads(fltr.params) if fltr.params.startswith('{') else {'params': fltr.params}
                media_type = params.get('type', 'N/A')
                source = params.get('source', 'N/A')
                after = params.get('after', 'N/A')
                before = params.get('before', 'N/A')
                min_likes = str(params.get('min_likes', 'N/A'))
                
                date_range = f"{after} to {before}" if after != 'N/A' or before != 'N/A' else "Any"
                
                table.add_row(
                    fltr.name,
                    media_type,
                    source,
                    date_range,
                    min_likes
                )
            except Exception as e:
                logger.warning(f"Error parsing filter params for {fltr.name}: {e}")
                table.add_row(fltr.name, "Error", "Error", "Error", "Error")
        
        console.print(table)
        
    except Exception as e:
        logger.error(f"Error listing filters: {e}")
        console.print(f"[red]✗ Error listing filters: {e}[/red]")
        raise typer.Exit(code=3)


@app.command()
def apply(
    name: str = typer.Option(..., "--name", help="Name of the filter to apply")
):
    """Apply a saved filter (runs search with its parameters)."""
    try:
        db_manager = DatabaseManager()
        
        filter_item = db_manager.get_filter_by_name(name)
        if not filter_item:
            console.print(f"[red]✗ Filter '{name}' not found[/red]")
            raise typer.Exit(code=1)
        
        console.print(f"[green]🔄 Applying filter '{name}'...[/green]")
        
        # Parse params
        try:
            params = json.loads(filter_item.params) if filter_item.params.startswith('{') else {'params': filter_item.params}
        except Exception as e:
            logger.error(f"Error parsing filter params: {e}")
            console.print(f"[red]✗ Error parsing filter params: {e}[/red]")
            raise typer.Exit(code=1)

        # Extract params with defaults
        source = params.get('source', '')
        media_type = params.get('type', 'photo')
        after = params.get('after')
        before = params.get('before')
        min_likes = params.get('min_likes', 0)
        limit = params.get('limit', 30)
        
        # Run the search logic asynchronously using the shared function from search.py
        try:
            asyncio.run(
                _execute_search(source, media_type, after, before, min_likes, limit, save_filter=None, offset=0)
            )
        except Exception as e:
            console.print(f"[red]✗ Search execution failed: {e}[/red]")
            raise typer.Exit(code=2)

    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Filter apply failed")
        console.print(f"[red]✗ Error applying filter: {e}[/red]")
        raise typer.Exit(code=3)


@app.command()
def delete(
    name: str = typer.Option(..., "--name", help="Name of the filter to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")
):
    """Delete a saved filter."""
    try:
        db_manager = DatabaseManager()
        
        filter_item = db_manager.get_filter_by_name(name)
        if not filter_item:
            console.print(f"[red]✗ Filter '{name}' not found[/red]")
            raise typer.Exit(code=1)
        
        if not force:
            confirm = typer.confirm(f"Delete filter '{name}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return
        
        # Real deletion from DB
        success = db_manager.delete_filter(name)
        if success:
            console.print(f"[green]✓ Filter '{name}' deleted[/green]")
        else:
            console.print(f"[red]✗ Failed to delete filter '{name}'[/red]")
            raise typer.Exit(code=3)
        
    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Error deleting filter: {e}")
        console.print(f"[red]✗ Error deleting filter: {e}[/red]")
        raise typer.Exit(code=3)