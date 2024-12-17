import json
import typing as ty

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.sql import insert, select

from anywise import Anywise, MessageRegistry

from .db import Events, Todos
from .model import CreateTodo, ListTodos, TodoCommand, TodoCreated, TodoEvent

registry = MessageRegistry(command_base=TodoCommand, event_base=TodoEvent)


@registry.factory
def engine_factory() -> AsyncEngine:
    url = "sqlite+aiosqlite:///demo/db.db"
    return create_async_engine(url)


@registry.factory
async def trans_conn(engine: AsyncEngine) -> ty.AsyncGenerator[AsyncConnection, None]:
    async with engine.begin() as cursor:
        yield cursor


@registry
async def add_new_todo(
    command: CreateTodo,
    conn: AsyncConnection,
    anywise: Anywise,
):
    stmt = insert(Todos).values(
        id=command.id, title=command.title, content=command.content
    )
    await conn.execute(stmt)
    event = TodoCreated(
        todo_id=command.id, title=command.title, content=command.content
    )
    await anywise.publish(event)
    return command.id


@registry
async def list_todos(_: ListTodos, conn: AsyncConnection):
    stmt = select(Events)
    cursor = await conn.execute(stmt)
    res = cursor.mappings()
    return res


@registry
async def listen_todo_created(
    event: TodoCreated, context: dict[str, ty.Any], conn: AsyncConnection
):
    body = json.dumps(event.__dict__)
    stmt = insert(Events).values(
        id=event.id,
        event_type="TodoCreated",
        event_body=body,
        entity_id=event.todo_id,
        version=1,
    )
    await conn.execute(stmt)
