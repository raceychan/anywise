import typing as ty
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.sql import insert, select

from anywise import Anywise, MessageRegistry, use

from .message import CreateTodo, ListTodos, Todo, TodoCommand, TodoCreated, TodoEvent
from .table import Events, Todos

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


def mapping_to_event(mapping: ty.Mapping[ty.Any, ty.Any]) -> TodoEvent:
    body = mapping["event_body"]
    event = TodoCreated(
        aggregate_id=mapping["aggregate_id"],
        title=body["title"],
        content=body["content"],
        timestamp=mapping["timestamp"],
    )
    return event


class EventStore:
    def __init__(self, engine: AsyncEngine = use(engine_factory)):
        self._engine = engine

    async def add(self, event: TodoEvent):
        stmt = insert(Events).values(
            id=event.id,
            event_type=event.__class__.__name__,
            event_body=event.body(),
            aggregate_id=event.aggregate_id,
            version=event.__class__.version,
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def list_streams(self) -> defaultdict[str, list[TodoEvent]]:
        stmt = select(Events)
        async with self._engine.begin() as conn:
            cursor = await conn.execute(stmt)
            res = cursor.mappings().all()

        grouped_events: defaultdict[str, list[TodoEvent]] = defaultdict(list)
        for r in res:
            e = mapping_to_event(r)
            grouped_events[e.aggregate_id].append(e)
        return grouped_events


@registry
class TodoService:
    def __init__(
        self,
        anywise: Anywise,
        repo: TodoRepository,
        es: EventStore,
    ):
        logger.info(f"created {self}")

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
        grouped_events = await self._es.list_streams()
        todos = [Todo.rebuild(events) for _, events in grouped_events.items()]
        return todos


# async def listen_todo_created(self, event: TodoCreated, context: dict[str, ty.Any]):
#     print(f"listen_todo_created: {event=}")
