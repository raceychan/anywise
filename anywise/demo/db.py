import sqlalchemy as sa
from sqlalchemy import orm as sa_orm
from sqlalchemy.ext import asyncio as saio
from sqlalchemy.sql import func


def declarative(cls: type) -> type[sa_orm.DeclarativeBase]:
    """
    A more pythonic way to declare a sqlalchemy table
    """

    return sa_orm.declarative_base(cls=cls)


@declarative
class TableBase:
    gmt_modified = sa.Column(
        "gmt_modified", sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    gmt_created = sa.Column("gmt_created", sa.DateTime, server_default=func.now())


class Todos(TableBase):
    __tablename__: str = "todos"

    id = sa.Column("id", sa.String, primary_key=True)
    title = sa.Column("title", sa.String, unique=False, index=True)
    content = sa.Column("content", sa.String, unique=False, index=False)


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)
