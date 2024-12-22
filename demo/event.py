from datetime import UTC, datetime
from functools import singledispatchmethod
from typing import Any, ClassVar
from uuid import uuid4

from msgspec import Struct, field


def uuid_factory() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class EventMeta(Struct, frozen=True):
    event_type: str  # type
    source: str  # project name, like demo
    version: str = "1"  # specversion


class Event(Struct, frozen=True, kw_only=True):
    meta: ClassVar[EventMeta]
    event_id: str = field(default_factory=uuid_factory)
    aggregate_id: str  # aggregate_id
    timestamp: str = field(default_factory=utc_now)

    def __init_subclass__(cls) -> None:
        type_id = f"{cls.__module__}.{cls.__name__}"
        cls.meta = EventMeta(event_type=type_id, source="demo", version="1")

    def __normalize__(self) -> dict[str, Any]: 
        """
        to be table compatible
        """
        ...



# Order Events
class ItemAdded(Event):
    quantity: int
    item_name: str


class Item(Struct):
    name: str
    quantity: int


class Order(Struct):
    order_id: str = field(default_factory=uuid_factory)
    items: list[Item] = field(default_factory=list)

    def add_item(self, item: Item) -> ItemAdded:
        event = ItemAdded(
            aggregate_id=self.order_id, item_name=item.name, quantity=item.quantity
        )
        self.apply(event)
        return event

    @singledispatchmethod
    def apply(self, event: object) -> None:
        raise NotImplementedError

    @apply.register
    def _(self, item_added: ItemAdded) -> None:
        self.items.append(Item(item_added.item_name, item_added.quantity))
