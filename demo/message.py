from dataclasses import dataclass, field
from functools import singledispatch
from typing import Sequence
from uuid import uuid4

from anywise.events import Event


# App Layer
def uuid_factory() -> str:
    return str(uuid4())


@dataclass
class TodoCommand: ...


class TodoEvent(Event): ...


@dataclass(kw_only=True)
class CreateTodo(TodoCommand):
    id: str = field(default_factory=uuid_factory)
    title: str
    content: str


@dataclass
class ListTodos(TodoCommand): ...


class TodoCreated(TodoEvent):
    title: str
    content: str


@dataclass
class Todo:
    todo_id: str  # uuid
    title: str
    content: str
    is_completed: bool = False

    @classmethod
    def rebuild(cls, events: Sequence[Event]) -> "Todo":
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
