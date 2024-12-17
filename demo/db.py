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


class Events(TableBase):
    __tablename__: str = "events"
    id = sa.Column("id", sa.String, primary_key=True)
    event_type = sa.Column("event_type", sa.String, index=True)
    event_body = sa.Column("event_body", sa.JSON)
    entity_id = sa.Column("entity_id", sa.String, index=True)
    version = sa.Column("version", sa.String, index=True)
    # consumed_at: sa.DateTime, nullable=True


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)
