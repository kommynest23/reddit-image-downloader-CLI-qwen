"""Typer app definition for the VK Media Downloader CLI."""

import typer

from .commands import config, search, download, list, metadata, filters, delete

app = typer.Typer(
    name="vk-downloader",
    help="CLI tool for downloading media from VKontakte",
    epilog="Use 'vk-downloader COMMAND --help' for more information on a command."
)

# config остаётся группой, так как имеет подкоманды (set, get, auth-status)
app.add_typer(config.app, name="config", help="Manage configuration settings")

# Остальные команды — одиночные функции. name=None "вливает" их в корень CLI
app.add_typer(search.app, name=None)
app.add_typer(download.app, name=None)
app.add_typer(list.app, name=None)
app.add_typer(metadata.app, name=None)
app.add_typer(filters.app, name=None)
app.add_typer(delete.app, name=None)

if __name__ == "__main__":
    app()