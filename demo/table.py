import sqlalchemy as sa
from sqlalchemy.ext import asyncio as saio

from anywise.messages.table import TableBase


class TodoTable(TableBase):
    __tablename__: str = "todos"

    todo_id = sa.Column("todo_id", sa.String, unique=True, nullable=False, index=True)
    title = sa.Column("title", sa.String, unique=False, nullable=False)
    content = sa.Column("content", sa.String, unique=False)
    is_completed = sa.Column("is_completed", sa.Boolean, default=False)


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)
