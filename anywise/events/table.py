from typing import Any, Mapping

import sqlalchemy as sa
from sqlalchemy import orm as sa_orm
from sqlalchemy.ext import asyncio as saio
from sqlalchemy.sql import func

from .model import Event, NormalizedEvent, get_event_cls

TABLE_RESERVED_VARS: set[str] = {
    "id",  # primary key
    "version",
    "source",
    "event_type",
    "event_body",
    "gmt_created",
    "gmt_modified",
}
"Values that exist in event table but should be ignored to rebuild the event model."


def declarative(cls: type) -> type[sa_orm.DeclarativeBase]:
    """
    A more pythonic way to declare a sqlalchemy table
    """

    return sa_orm.declarative_base(cls=cls)


@declarative
class TableBase:
    "Exert constraints on table creation, and reduce duplicate code"
    gmt_modified = sa.Column(
        "gmt_modified", sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    gmt_created = sa.Column("gmt_created", sa.DateTime, server_default=func.now())


class Events(TableBase):
    __tablename__: str = "events"
    __table_args__: tuple[Any] = (
        sa.Index("idx_events_aggregate_id_version", "aggregate_id", "version"),
    )

    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    event_id = sa.Column(
        "event_id", sa.String, index=False, nullable=False, unique=True
    )
    event_type = sa.Column("event_type", sa.String)
    event_body = sa.Column("event_body", sa.JSON)
    source = sa.Column("source", sa.String, nullable=False)
    aggregate_id = sa.Column("aggregate_id", sa.String, index=True, nullable=False)
    timestamp = sa.Column("timestamp", sa.String)
    version = sa.Column("version", sa.String)


# class OutBoxEvents(Events):
#     __tablename__: str = "outbox_events"
#     consumed_at = sa.Column(sa.DateTime, nullable=True)


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)


def event_to_mapping(event: Event) -> NormalizedEvent:
    return event.__table_mapping__()


def mapping_to_event(row_mapping: Mapping[Any, Any]) -> Event:
    type_id = row_mapping["event_type"]
    event_cls = get_event_cls(type_id)
    mapping = {k: v for k, v in row_mapping.items() if k not in TABLE_RESERVED_VARS}
    body = row_mapping["event_body"]
    return event_cls(**mapping, **body)
