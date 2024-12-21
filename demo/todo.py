import json
import typing as ty
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.sql import insert, select

from anywise import Anywise, MessageRegistry

from .message import CreateTodo, ListTodos, Todo, TodoCommand, TodoCreated, TodoEvent
from .table import Events, Todos

# App layer

registry = MessageRegistry(command_base=TodoCommand, event_base=TodoEvent)


@registry.factory
def engine_factory() -> AsyncEngine:
    url = "sqlite+aiosqlite:///demo/db.db"
    print("engine created")
    return create_async_engine(url)


@registry.factory
async def trans_conn(engine: AsyncEngine) -> ty.AsyncGenerator[AsyncConnection, None]:
    async with engine.begin() as conn:
        print("conn created")
        yield conn
    print("conn closed")


class TodoRepository:
    def __init__(self, conn: AsyncConnection):
        self._conn = conn

    async def add(self, todo: Todo):
        stmt = insert(Todos).values(
            id=todo.todo_id,
            title=todo.title,
            content=todo.content,
            is_completed=todo.is_completed,
        )

        await self._conn.execute(stmt)


def mapping_to_event(mapping: ty.Mapping[ty.Any, ty.Any]) -> TodoEvent:
    body = json.loads(mapping["event_body"])
    event = TodoCreated(
        entity_id=mapping["entity_id"],
        title=body["title"],
        content=body["content"],
        timestamp=mapping["timestamp"],
    )
    return event


class EventStore:
    def __init__(self, conn: AsyncConnection):
        self._conn = conn

    async def add(self, event: TodoEvent):
        event_body = event.__dict__.copy()
        event_body.pop("id")
        event_body.pop("entity_id")
        event_body.pop("timestamp")
        body = json.dumps(event_body)
        stmt = insert(Events).values(
            id=event.id,
            event_type=event.__class__.__name__,
            event_body=body,
            entity_id=event.entity_id,
            version=1,
        )
        await self._conn.execute(stmt)

    async def list_streams(self) -> defaultdict[str, list[TodoEvent]]:
        stmt = select(Events)
        cursor = await self._conn.execute(stmt)
        res = cursor.mappings().all()
        grouped_events: defaultdict[str, list[TodoEvent]] = defaultdict(list)
        for r in res:
            e = mapping_to_event(r)
            grouped_events[e.entity_id].append(e)
        return grouped_events


@registry
async def add_new_todo(
    command: CreateTodo,
    repo: TodoRepository,
    es: EventStore,
    anywise: Anywise,
):
    event = TodoCreated(
        entity_id=command.id, title=command.title, content=command.content
    )
    todo = Todo(todo_id=command.id, title=command.title, content=command.content)
    # todo = Todo.apply(event)
    await repo.add(todo)

    await es.add(event)
    await anywise.publish(event)
    return command.id


@registry
async def list_todos(_: ListTodos, es: EventStore) -> list[Todo]:
    grouped_events = await es.list_streams()
    todos = [Todo.rebuild(events) for _, events in grouped_events.items()]
    return todos


@registry
async def listen_todo_created(
    event: TodoCreated, context: dict[str, ty.Any], conn: AsyncConnection
):
    print(f"listen_todo_created: {event=}")
