import sqlalchemy as sa
from sqlalchemy.ext import asyncio as saio

from anywise.events.table import TableBase


class Todos(TableBase):
    __tablename__: str = "todos"

    id = sa.Column("id", sa.String, primary_key=True)
    title = sa.Column("title", sa.String, unique=False, index=True)
    content = sa.Column("content", sa.String, unique=False, index=False)
    is_completed = sa.Column("is_completed", sa.Boolean, default=False)


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)
