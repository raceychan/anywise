from typing import Any, Mapping

import sqlalchemy as sa
from sqlalchemy import orm as sa_orm
from sqlalchemy.ext import asyncio as saio
from sqlalchemy.sql import func

from .model import IEvent, NormalizedEvent, get_event_cls

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
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    gmt_modified = sa.Column(
        "gmt_modified", sa.DateTime, server_default=func.now(), onupdate=func.now()
    )
    gmt_created = sa.Column("gmt_created", sa.DateTime, server_default=func.now())


class EventTable(TableBase):
    __tablename__: str = "events"
    __table_args__: tuple[Any] = (
        sa.Index("idx_events_entity_id_version", "entity_id", "version"),
    )

    event_id = sa.Column(
        "event_id", sa.String, index=False, nullable=False, unique=True
    )  # entity_id of the aggregate root
    event_type = sa.Column("event_type", sa.String)
    event_body = sa.Column("event_body", sa.JSON)
    source = sa.Column("source", sa.String, nullable=False)
    entity_id = sa.Column("entity_id", sa.String, index=True, nullable=False)
    timestamp = sa.Column("timestamp", sa.String)
    version = sa.Column("version", sa.String)
    # version of the aggregate root entity


# class OutBoxEvents(TableBase):
#     """
#     id BIGINT PRIMARY KEY AUTO_INCREMENT,       -- Unique outbox record ID
#     event_id BIGINT NOT NULL,                   -- Foreign key to the events table
#     status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',  -- Delivery status
#     processed_at TIMESTAMP NULL,                -- Timestamp when the event was processed or sent
#     retry_count INT DEFAULT 0,                  -- Number of retries
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When the outbox record was created
#     CONSTRAINT fk_event_id FOREIGN KEY (event_id) REFERENCES events(id) -- Link to the event table
#     """

#     __tablename__: str = "outbox_events"

#     event_id = sa.Column(
#         "event_id", sa.String, index=False, nullable=False, unique=True
#     )
#     status = sa.Column(sa.Enum("pending", "sent", "failed"), default="pending")
#     processed_at = sa.Column("processed_at", sa.DateTime, nullable=True)
#     retry = sa.Column("retry", sa.Integer, default=0)


async def create_tables(engine: saio.AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(TableBase.metadata.create_all)


def event_to_mapping(event: IEvent) -> NormalizedEvent:
    return event.__normalized__()


def mapping_to_event(row_mapping: Mapping[Any, Any]) -> IEvent:
    type_id = row_mapping["event_type"]
    event_cls = get_event_cls(type_id)
    mapping = {k: v for k, v in row_mapping.items() if k not in TABLE_RESERVED_VARS}
    body = row_mapping["event_body"]
    return event_cls(**mapping, **body)
