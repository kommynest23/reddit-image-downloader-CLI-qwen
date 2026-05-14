"""Config-related CLI commands."""

import typer
from rich.console import Console
from rich.table import Table
import asyncio

from src.config.manager import ConfigManager
from src.api.client import VKAPIClient
from src.utils.logger import logger

app = typer.Typer()
console = Console()
auth_app = typer.Typer()
app.add_typer(auth_app, name="auth", help="Authentication-related commands")


@auth_app.command("status")
def auth_status():
    """Check the status of the VK API authentication token."""
    try:
        config_manager = ConfigManager()
        
        if not config_manager.config.vk.service_token:
            console.print("[red]✗ No VK service token configured[/red]")
            raise typer.Exit(code=2)
        
        # Create API client and try a simple request
        client = VKAPIClient(config_manager)
        
        # Try to get current user info as a test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_token(client))
        finally:
            loop.close()
        
        if result:
            console.print("[green]✓ Token is valid[/green]")
            console.print(f"API Version: {config_manager.config.vk.api_version}")
        else:
            console.print("[red]✗ Token validation failed[/red]")
            raise typer.Exit(code=2)
        
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        console.print(f"[red]✗ Error checking auth status: {e}[/red]")
        raise typer.Exit(code=2)


@app.command()
def set_config(key: str, value: str):
    """Set a configuration value."""
    try:
        config_manager = ConfigManager()
        
        # Validate key exists in AppConfig model
        parts = key.split('.')
        current_model = config_manager.config.__class__.__dict__
        
        # Navigate through nested attributes
        model = config_manager.config
        for part in parts[:-1]:
            model = getattr(model, part)
        
        # Check if final key exists
        if not hasattr(model, parts[-1]):
            console.print(f"[red]✗ Invalid config key: {key}[/red]")
            console.print("[yellow]Available keys:[/yellow]")
            # Print available keys recursively
            print_config_keys(config_manager.config)
            raise typer.Exit(code=1)
        
        # Convert value to appropriate type
        field_info = model.model_fields.get(parts[-1])
        if field_info:
            value_type = field_info.annotation
            if value_type == bool:
                converted_value = value.lower() in ['true', '1', 'yes', 'on']
            elif value_type == int:
                converted_value = int(value)
            elif value_type == float:
                converted_value = float(value)
            elif hasattr(value_type, '__origin__') and value_type.__origin__ is list:
                converted_value = [item.strip() for item in value.split(',')]
            else:
                converted_value = value
        else:
            converted_value = value
        
        # Update the nested attribute
        current_attr = config_manager.config
        for part in parts[:-1]:
            current_attr = getattr(current_attr, part)
        setattr(current_attr, parts[-1], converted_value)
        
        # Save to file
        config_manager.save_config()
        
        console.print(f"[green]✓ Установлено: {key} = {converted_value}[/green]")
        
    except ValueError as e:
        console.print(f"[red]✗ Invalid value: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error setting config: {e}")
        console.print(f"[red]✗ Error setting config: {e}[/red]")
        raise typer.Exit(code=3)


@app.command()
def get_config(key: str):
    """Get a configuration value."""
    try:
        config_manager = ConfigManager()
        
        # Navigate through nested attributes
        parts = key.split('.')
        current_attr = config_manager.config
        for part in parts:
            current_attr = getattr(current_attr, part)
        
        console.print(str(current_attr))
        
    except AttributeError:
        console.print(f"[red]✗ Invalid config key: {key}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        console.print(f"[red]✗ Error getting config: {e}[/red]")
        raise typer.Exit(code=3)


async def test_token(client: VKAPIClient):
    """Test the token by making a simple API request."""
    try:
        # Try to get current user info (this requires no special permissions)
        result = await client.get_user_info(['1'])
        return len(result) > 0
    except Exception as e:
        logger.error(f"Token test failed: {e}")
        return False


def print_config_keys(obj, prefix=""):
    """Recursively print available config keys."""
    for field_name in obj.__class__.__annotations__:
        field_value = getattr(obj, field_name)
        key_path = f"{prefix}.{field_name}" if prefix else field_name
        if hasattr(field_value, '__annotations__'):  # Nested model
            print_config_keys(field_value, key_path)
        else:
            console.print(f"  {key_path}")