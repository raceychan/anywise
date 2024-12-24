import typing as ty

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.sql import insert

from anywise import Anywise, MessageRegistry, use
from anywise.events import EventStore

from .message import CreateTodo, ListTodos, Todo, TodoCommand, TodoCreated, TodoEvent
from .table import Todos

# App layer

registry = MessageRegistry(command_base=TodoCommand, event_base=TodoEvent)

from loguru import logger


def engine_factory() -> AsyncEngine:
    url = "sqlite+aiosqlite:///demo/db.db"
    logger.success("engine created")
    return create_async_engine(url)


async def trans_conn(engine: AsyncEngine) -> ty.AsyncGenerator[AsyncConnection, None]:
    logger.success("conn created")
    async with engine.begin() as conn:
        yield conn


class TodoRepository:
    def __init__(self, engine: AsyncEngine = use(engine_factory)):
        self._engine = engine

    async def add(self, todo: Todo):
        stmt = insert(Todos).values(
            id=todo.todo_id,
            title=todo.title,
            content=todo.content,
            is_completed=todo.is_completed,
        )

        async with self._engine.begin() as conn:
            await conn.execute(stmt)


@registry
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
            aggregate_id=command.id, title=command.title, content=command.content
        )
        todo = Todo.apply(event)
        await self._repo.add(todo)
        await self._es.add(event)
        await self._aw.publish(event)
        return command.id

    async def list_todos(self, _: ListTodos) -> list[Todo]:
        todos: list[Todo] = []
        async for stream in self._es.event_streams():
            todos.append(Todo.rebuild(stream))
        return todos


# async def listen_todo_created(self, event: TodoCreated, context: dict[str, ty.Any]):
#     print(f"listen_todo_created: {event=}")
