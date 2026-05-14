import typer
import asyncio
from ...storage.database import get_session
from ...storage.models import Filter
from sqlalchemy import select
from loguru import logger
from ...cli.commands.search_cmd import search_async

app = typer.Typer()

@app.command("create")
def filter_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Имя фильтра"),
    source: str = typer.Option(...),
    type: str = typer.Option("photo"),
    limit: int = typer.Option(10),
    after: str = typer.Option(None),
    before: str = typer.Option(None),
    min_likes: int = typer.Option(None)
):
    """Создать сохранённый поисковый фильтр"""
    asyncio.run(_filter_create_async(ctx, name, source, type, limit, after, before, min_likes))

async def _filter_create_async(ctx, name, source, type, limit, after, before, min_likes):
    params = {
        "source": source,
        "type": type,
        "limit": limit,
        "after": after,
        "before": before,
        "min_likes": min_likes,
    }
    async with get_session() as session:
        existing = await session.execute(select(Filter).filter(Filter.name == name))
        if existing.scalar_one_or_none():
            typer.secho(f"Фильтр '{name}' уже существует", fg="red")
            raise typer.Exit(1)
        session.add(Filter(name=name, params=params))
        await session.commit()
    logger.info(f"Фильтр '{name}' создан")

@app.command("list")
def filter_list(ctx: typer.Context):
    """Показать все сохранённые фильтры"""
    asyncio.run(_filter_list_async(ctx))

async def _filter_list_async(ctx):
    async with get_session() as session:
        result = await session.execute(select(Filter))
        filters = result.scalars().all()
        if not filters:
            typer.echo("Нет сохранённых фильтров")
            return
        for f in filters:
            typer.echo(f"{f.name}: {f.params}")

@app.command("apply")
def filter_apply(ctx: typer.Context, name: str = typer.Argument(...)):
    """Применить фильтр и выполнить поиск"""
    asyncio.run(_filter_apply_async(ctx, name))

async def _filter_apply_async(ctx, name):
    async with get_session() as session:
        result = await session.execute(select(Filter).filter(Filter.name == name))
        f = result.scalar_one_or_none()
        if not f:
            typer.secho(f"Фильтр '{name}' не найден", fg="red")
            raise typer.Exit(1)
    params = f.params

    await search_async(
        ctx,
        source=params["source"],
        type=params["type"],
        limit=params.get("limit", 10),
        after=params.get("after"),
        before=params.get("before"),
        min_likes=params.get("min_likes"),
    )

@app.command("delete")
def filter_delete(ctx: typer.Context, name: str = typer.Argument(...)):
    """Удалить фильтр по имени"""
    asyncio.run(_filter_delete_async(ctx, name))

async def _filter_delete_async(ctx, name):
    async with get_session() as session:
        result = await session.execute(select(Filter).filter(Filter.name == name))
        f = result.scalar_one_or_none()
        if not f:
            typer.secho(f"Фильтр '{name}' не найден", fg="red")
            raise typer.Exit(1)
        await session.delete(f)
        await session.commit()
    logger.info(f"Фильтр '{name}' удалён")