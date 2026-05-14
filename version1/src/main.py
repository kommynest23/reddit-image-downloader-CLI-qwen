"""Main entry point for the VK Media Downloader CLI application."""

import sys
import typer
from rich.console import Console
from rich.traceback import install

from src.config.manager import ConfigManager
from src.utils.logger import logger

# Install rich traceback for better error reporting
install()

app = typer.Typer(
    name="vk-downloader",
    help="CLI tool for downloading media from VKontakte",
    epilog="Use 'vk-downloader COMMAND --help' for more information on a command.",
    no_args_is_help=True
)

console = Console()


@app.callback()
def main():
    """
    Main callback to initialize the application.
    """
    pass


@app.command()
def config_test():
    """Test command to verify configuration loading."""
    try:
        config_manager = ConfigManager()
        config = config_manager.config
        
        console.print("[green]✓ Configuration loaded successfully[/green]")
        console.print(f"Download directory: {config.download.download_directory}")
        console.print(f"Favorite users: {config.favorite_users}")
        
        # Check if VK credentials are set
        if config.vk.service_token:
            console.print("[green]✓ VK service token configured[/green]")
        else:
            console.print("[yellow]⚠ VK service token not set[/yellow]")
            
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        console.print(f"[red]✗ Error loading configuration: {e}[/red]")
        sys.exit(2)  # API error code


def handle_exit_code(error_type: str) -> int:
    """
    Map error types to appropriate exit codes.
    
    Args:
        error_type: Type of error that occurred
        
    Returns:
        Appropriate exit code (0=OK, 1=input error, 2=API error, 3=FS error)
    """
    if error_type == "input_error":
        return 1
    elif error_type == "api_error":
        return 2
    elif error_type == "fs_error":
        return 3
    else:
        return 1  # Default to input error


if __name__ == "__main__":
    # Import and run the CLI app
    from src.cli.app import app
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled exception occurred")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(2)  # Treat unhandled exceptions as API errors