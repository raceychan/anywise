from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


def uuid_factory() -> str:
    return str(uuid4())


@dataclass
class TodoCommand: ...


@dataclass
class TodoEvent: ...


@dataclass(kw_only=True)
class CreateTodo(TodoCommand):
    id: str = field(default_factory=uuid_factory)
    title: str
    content: str

@dataclass
class ListTodos(TodoCommand):
    ...

@dataclass(kw_only=True)
class TodoCreated(TodoEvent):
    id: str = field(default_factory=uuid_factory)
    todo_id: str
    title: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
