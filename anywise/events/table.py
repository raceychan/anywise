from typing import Any, Mapping

import sqlalchemy as sa
from sqlalchemy import orm as sa_orm
from sqlalchemy.ext import asyncio as saio
from sqlalchemy.sql import func

from .model import Event, get_event_cls, type_id

TABLE_RESERVED_VARS: set[str] = {
    "version",
    "source",
    "event_type",
    "event_body",
    "gmt_created",
    "gmt_modified",
}
"Values that exist in event table but no needed for event model"

RENAME: dict[str, str] = {"id": "event_id"}
"Map column name to even model field name, if they are different."


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
    id = sa.Column("id", sa.String, primary_key=True)
    event_type = sa.Column("event_type", sa.String, index=True)
    event_body = sa.Column("event_body", sa.JSON)
    source = sa.Column("source", sa.String)
    aggregate_id = sa.Column("aggregate_id", sa.String, index=True)
    timestamp = sa.Column("timestamp", sa.String)
    version = sa.Column("version", sa.String, index=True)


class OutBoxEvents(Events):
    consumed_at = sa.Column(sa.DateTime, nullable=True)


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)


def event_to_mapping(event: Event) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    mapping["event_type"] = type_id(event.__class__)
    mapping["version"] = event.__version__
    mapping["source"] = event.__source__ or "demo"

    reserved_field = Event.__struct_fields__
    body = {}
    for f in event.__struct_fields__:
        if f not in reserved_field:
            body[f] = getattr(event, f)
        else:
            mapping[f] = getattr(event, f)
    mapping["event_body"] = body
    mapping["id"] = mapping.pop("event_id")
    return mapping


def mapping_to_event(row_mapping: Mapping[Any, Any]) -> Event:
    type_id = row_mapping["event_type"]
    event_cls = get_event_cls(type_id)
    mapping = {
        RENAME.get(k, k): v
        for k, v in row_mapping.items()
        if k not in TABLE_RESERVED_VARS
    }
    body = row_mapping["event_body"]
    return event_cls(**mapping, **body)
