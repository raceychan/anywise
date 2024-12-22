from dataclasses import dataclass, field
from datetime import datetime
from functools import singledispatch
from typing import Any, ClassVar, Sequence
from uuid import uuid4


def all_subclasses(cls: type) -> set[type]:
    return set(cls.__subclasses__()).union(
        *[all_subclasses(c) for c in cls.__subclasses__()]
    )


# App Layer

"""
class Event[Payload]:
    version: ClassVar[str]
    event_type: ClassVar[str]

    id: str # generated str uuid
    timestamp: str # generated isoformat
    entity_id: str
    payload: Payload
"""


def uuid_factory() -> str:
    return str(uuid4())


@dataclass
class TodoCommand: ...


@dataclass(frozen=True, kw_only=True)
class Event:
    version: ClassVar[str] = "1"

    id: str = field(default_factory=uuid_factory)
    aggregate_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def body(self) -> dict[str, Any]:
        reserved = {"id", "aggregate_id", "timestamp"}
        return {k: v for k, v in self.__dict__.items() if k not in reserved}

    # def normalize(self) -> dict[str, Any]:
    #     # database friendly transform
    #     return {
    #         "id": self.id,
    #         "entity_id": self.entity_id,
    #         "timestamp": self.timestamp,
    #         "body": self.body(),
    #     }


@dataclass(frozen=True, kw_only=True)
class TodoEvent(Event): ...


@dataclass(kw_only=True)
class CreateTodo(TodoCommand):
    id: str = field(default_factory=uuid_factory)
    title: str
    content: str


@dataclass
class ListTodos(TodoCommand): ...


@dataclass(frozen=True, kw_only=True)
class TodoCreated(TodoEvent):
    version: ClassVar[str] = "1"

    title: str
    content: str


@dataclass
class Todo:
    todo_id: str  # uuid
    title: str
    content: str
    is_completed: bool = False

    @classmethod
    def rebuild(cls, events: Sequence[TodoEvent]) -> "Todo":
        create, rest = events[0], events[1:]
        self = cls.apply(create)

        for e in rest:
            self.apply(e)

        return self

    @classmethod
    @singledispatch
    def apply(cls, event: TodoCreated) -> "Todo":
        return cls(
            todo_id=event.aggregate_id,
            title=event.title,
            content=event.content,
        )
