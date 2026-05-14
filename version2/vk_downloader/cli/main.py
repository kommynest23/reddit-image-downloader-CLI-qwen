import typer
import asyncio
from ..config.manager import ConfigManager
from ..utils.logger import setup_logger
from ..storage.database import init_db, create_tables
from .commands import config_cmd, search_cmd, download_cmd, list_media_cmd, metadata_cmd, filter_cmd, delete_cmd

app = typer.Typer()

@app.callback()
def main_callback(ctx: typer.Context):
    """Загрузка конфигурации и инициализация БД."""
    setup_logger()
    config = ConfigManager.load()
    # Инициализация базы данных
    db_url = f"sqlite+aiosqlite:///{config.database.path}"
    init_db(db_url)
    # Явно создаём таблицы, если их нет
    asyncio.run(create_tables())
    ctx.obj = {"config": config}

app.add_typer(config_cmd.app, name="config", help="Управление настройками")
app.add_typer(search_cmd.app, name="search", help="Поиск медиа")
app.add_typer(download_cmd.app, name="download", help="Скачивание файлов")
app.add_typer(list_media_cmd.app, name="list-media", help="Просмотр библиотеки")
app.add_typer(metadata_cmd.app, name="metadata", help="Теги и статусы")
app.add_typer(filter_cmd.app, name="filter", help="Сохранённые фильтры")
app.add_typer(delete_cmd.app, name="delete", help="Удаление записей")