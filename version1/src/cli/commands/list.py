"""List-related CLI commands."""

import typer
from datetime import datetime
from rich.console import Console
from rich.table import Table
from typing import Optional
import json
import csv
from io import StringIO

from src.config.manager import ConfigManager
from src.storage.database import DatabaseManager
from src.utils.logger import logger

app = typer.Typer()
console = Console()


@app.command()
def list_media(
    source: Optional[str] = typer.Option(None, "--source", help="Filter by owner (owner_id or shortname)"),
    media_type: Optional[str] = typer.Option(None, "--type", help="Filter by media type", 
                                             case_sensitive=False, 
                                             autocompletion=lambda: ["photo", "video", "doc"]),
    after: Optional[str] = typer.Option(None, "--after", help="Filter: download date >= (format: YYYY-MM-DD)"),
    before: Optional[str] = typer.Option(None, "--before", help="Filter: download date <= (format: YYYY-MM-DD)"),
    starred: bool = typer.Option(False, "--starred", help="Show only starred items"),
    read: bool = typer.Option(False, "--read", help="Show only read items"),
    search_term: Optional[str] = typer.Option(None, "--search", help="Full-text search in title + description"),
    page: int = typer.Option(1, "--page", min=1, help="Page number for pagination"),
    per_page: int = typer.Option(50, "--per-page", min=1, max=100, help="Items per page"),
    format: str = typer.Option("table", "--format", help="Output format", 
                               case_sensitive=False, 
                               autocompletion=lambda: ["table", "json", "csv"])
):
    """View and filter local media library with search and pagination."""
    try:
        db_manager = DatabaseManager()
        
        # Validate date range if provided
        after_date = None
        before_date = None
        if after:
            try:
                after_date = datetime.strptime(after, "%Y-%m-%d").date()
            except ValueError:
                console.print("[red]✗ Invalid date format for --after. Use YYYY-MM-DD[/red]")
                raise typer.Exit(code=1)
        
        if before:
            try:
                before_date = datetime.strptime(before, "%Y-%m-%d").date()
            except ValueError:
                console.print("[red]✗ Invalid date format for --before. Use YYYY-MM-DD[/red]")
                raise typer.Exit(code=1)
        
        # Build filters
        filters = {}
        if media_type:
            filters['media_type'] = media_type
        
        # Owner ID needs to be resolved from source if it's a shortname
        owner_id = None
        if source:
            # For simplicity, assume it's already a numeric ID
            try:
                owner_id = int(source)
                filters['owner_id'] = owner_id
            except ValueError:
                # If it's not numeric, we'd need to resolve it via API
                console.print(f"[yellow]⚠ Non-numeric source '{source}' not resolved in this example[/yellow]")
        
        # Perform search with filters
        results = db_manager.search_media(
            media_type=media_type,
            owner_id=owner_id,
            limit=per_page * page  # Get enough for pagination
        )
        
        # Apply additional client-side filters
        filtered_results = []
        for item in results:
            include = True
            
            # Date filtering
            if after_date and item.downloaded_at and item.downloaded_at.date() < after_date:
                include = False
            if before_date and item.downloaded_at and item.downloaded_at.date() > before_date:
                include = False
            
            # Text search
            if search_term and search_term.lower() not in (item.title.lower() + item.description.lower()):
                include = False
                
            if include:
                filtered_results.append(item)
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = filtered_results[start_idx:end_idx]
        
        # Output based on format
        if format == "json":
            output_json(paginated_results)
        elif format == "csv":
            output_csv(paginated_results)
        else:  # table
            output_table(paginated_results, page, len(filtered_results), per_page)
        
        if not paginated_results:
            console.print("[yellow]No records found matching criteria[/yellow]")
        
    except Exception as e:
        logger.error(f"Error during list: {e}")
        console.print(f"[red]✗ Error during list: {e}[/red]")
        raise typer.Exit(code=3)


def output_table(results, page, total_count, per_page):
    """Output results in a rich table."""
    total_pages = (total_count + per_page - 1) // per_page
    
    table = Table(title=f"Media Library (Page {page} of {total_pages}) - Total: {total_count}")
    table.add_column("ID", style="dim")
    table.add_column("Type")
    table.add_column("Title", max_width=40)
    table.add_column("Owner", style="magenta")
    table.add_column("Date", style="blue")
    table.add_column("★", justify="center")
    table.add_column("📖", justify="center")
    
    for item in results:
        # Determine starred/read status from metadata
        # This is simplified - in a real implementation you'd query the metadata table
        is_starred = "★" if item.download_path else ""  # Placeholder
        is_read = "📖" if item.download_path else ""     # Placeholder
        
        table.add_row(
            item.vk_id,
            item.media_type,
            item.title[:40] + ("..." if len(item.title) > 40 else ""),
            str(item.owner_id),
            item.created_at.strftime('%Y-%m-%d') if item.created_at else "N/A",
            is_starred,
            is_read
        )
    
    console.print(table)
    console.print(f"[green]Showing {len(results)} of {total_count} items[/green]")


def output_json(results):
    """Output results in JSON format."""
    json_data = []
    for item in results:
        json_data.append({
            "id": item.vk_id,
            "type": item.media_type,
            "title": item.title,
            "owner_id": item.owner_id,
            "url": item.url,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "download_path": item.download_path,
            "downloaded_at": item.downloaded_at.isoformat() if item.downloaded_at else None
        })
    
    console.print(json.dumps(json_data, indent=2, ensure_ascii=False))


def output_csv(results):
    """Output results in CSV format."""
    if not results:
        console.print("")
        return
    
    # Create in-memory string buffer
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(["ID", "Type", "Title", "Owner ID", "URL", "Created At", "Download Path", "Downloaded At"])
    
    # Write rows
    for item in results:
        writer.writerow([
            item.vk_id,
            item.media_type,
            item.title,
            item.owner_id,
            item.url,
            item.created_at.isoformat() if item.created_at else "",
            item.download_path or "",
            item.downloaded_at.isoformat() if item.downloaded_at else ""
        ])
    
    console.print(output.getvalue())
    output.close()