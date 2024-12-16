from dataclasses import dataclass


@dataclass
class TodoCommand: ...


@dataclass
class CreateTodo(TodoCommand):
    title: str
    content: str
