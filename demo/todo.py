import typing as ty

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.sql import insert, select, update

from anywise import Anywise, MessageRegistry
from anywise.messages import EventStore, NormalizedEvent

from .message import (
    CreateTodo,
    ListTodoEvents,
    ListTodos,
    RenameTodo,
    Todo,
    TodoCommand,
    TodoCreated,
    TodoEvent,
    TodoRetitled,
)
from .table import TodoTable

# App layer

registry = MessageRegistry(command_base=TodoCommand, event_base=TodoEvent)


@registry.factory
def engine_factory() -> AsyncEngine:
    url = "sqlite+aiosqlite:///demo/db.db"
    logger.success("engine created")
    return create_async_engine(url)


@registry.factory
async def trans_conn(engine: AsyncEngine) -> ty.AsyncGenerator[AsyncConnection, None]:
    logger.success("conn created")
    async with engine.begin() as conn:
        yield conn


class TodoRepository:
    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    async def add(self, todo: Todo):
        stmt = insert(TodoTable).values(
            todo_id=todo.todo_id,
            title=todo.title,
            content=todo.content,
            is_completed=todo.is_completed,
        )

        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def get(self, todo_id: str) -> Todo | None:
        stmt = select(TodoTable).where(TodoTable.todo_id == todo_id)
        async with self._engine.begin() as conn:
            cursor = await conn.execute(stmt)
            mapping = cursor.mappings().one_or_none()

        if mapping:
            return Todo(
                todo_id=mapping["todo_id"],
                title=mapping["title"],
                content=mapping["content"],
                is_completed=mapping["is_completed"],
            )
        return None

    async def retitle(self, todo_id: str, title: str) -> None:
        stmt = update(TodoTable).values(title=title).where(TodoTable.todo_id == todo_id)
        async with self._engine.begin() as conn:
            await conn.execute(stmt)


async def list_events(query: ListTodoEvents, es: EventStore) -> list[NormalizedEvent]:
    events = await es.list_events(query.todo_id)
    return [e.__normalized__() for e in events]


class TodoService:
    def __init__(
        self,
        anywise: Anywise,
        repo: TodoRepository,
        es: EventStore,
    ):
        self._repo = repo
        self._es = es
        self._aw = anywise

    async def add_new_todo(self, command: CreateTodo):
        event = TodoCreated(
            entity_id=command.id, title=command.title, content=command.content
        )
        todo = Todo.apply(event)
        await self._repo.add(todo)
        await self._es.add(event)
        await self._aw.publish(event)
        return command.id

    async def rename_todo(self, command: RenameTodo):
        event = TodoRetitled(title=command.title, entity_id=command.todo_id)
        todo = await self._repo.get(command.todo_id)
        if not todo:
            raise KeyError(f"todo with {command.todo_id=} not found")
        todo.apply(event)

        # TODO: make these three a transaction
        await self._repo.retitle(todo.todo_id, todo.title)
        await self._es.add(event)
        await self._aw.publish(event)

    async def list_todos(self, _: ListTodos) -> list[Todo]:
        todos: list[Todo] = []
        async for stream in self._es.all_event_streams():
            todos.append(Todo.rebuild(stream))
        return todos


registry.register(list_events, TodoService)
