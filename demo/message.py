from dataclasses import dataclass, field
from datetime import datetime
from functools import singledispatch
from typing import Sequence
from uuid import uuid4

# App Layer

"""
class Event[Payload]:
    version: ClassVar[str]
    event_type: ClassVar[str]

    id: str
    entity_id: str
    timestamp: str
    payload: Payload
"""


def uuid_factory() -> str:
    return str(uuid4())


@dataclass
class TodoCommand: ...


@dataclass
class TodoEvent:
    id: str
    entity_id: str
    timestamp: str


@dataclass(kw_only=True)
class CreateTodo(TodoCommand):
    id: str = field(default_factory=uuid_factory)
    title: str
    content: str


@dataclass
class ListTodos(TodoCommand): ...


@dataclass(kw_only=True)
class TodoCreated(TodoEvent):
    id: str = field(default_factory=uuid_factory)
    entity_id: str
    title: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


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
            todo_id=event.entity_id,
            title=event.title,
            content=event.content,
        )
