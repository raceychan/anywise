from dataclasses import dataclass, field
from functools import singledispatchmethod
from typing import Self, Sequence
from uuid import uuid4

from anywise.messages import Event, IEvent


# App Layer
def uuid_factory() -> str:
    return str(uuid4())


@dataclass
class TodoCommand: ...


@dataclass
class ListTodoEvents(TodoCommand):
    todo_id: str


class TodoEvent(Event): ...


@dataclass(kw_only=True)
class CreateTodo(TodoCommand):
    id: str = field(default_factory=uuid_factory)
    title: str
    content: str


@dataclass
class RenameTodo(TodoCommand):
    todo_id: str
    title: str


@dataclass
class ListTodos(TodoCommand): ...


class TodoCreated(TodoEvent):
    title: str
    content: str


class TodoRetitled(TodoEvent):
    title: str


@dataclass
class Todo:
    todo_id: str  # uuid
    title: str
    content: str
    is_completed: bool = False

    @classmethod
    def rebuild(cls, events: Sequence[IEvent]) -> "Todo":
        create, rest = events[0], events[1:]
        self = cls.apply(create)

        for e in rest:
            self.apply(e)

        return self

    @singledispatchmethod
    @classmethod
    def apply(cls, event: TodoCreated) -> "Self":
        return cls(
            todo_id=event.entity_id,
            title=event.title,
            content=event.content,
        )

    @apply.register
    def _(self, event: TodoRetitled) -> "Self":
        self.title = event.title
        return self
