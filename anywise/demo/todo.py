import typing as ty
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql import insert

from ..anywise import Anywise, HandlerRegistry
from .db import Todos
from .model import CreateTodo, TodoCommand

registry = HandlerRegistry(TodoCommand)


@registry.factory
def engine_factory() -> AsyncEngine:
    url = "sqlite+aiosqlite://"
    return create_async_engine(url)


@registry
async def create_todo(
    command: CreateTodo,
    context: dict[str, ty.Any],
    engine: AsyncEngine,
    anywise: Anywise,
):
    # BUG, a new anywise is created in sender
    new_engine = await anywise.resolve(AsyncEngine)

    stmt = insert(Todos).values(
        id=str(uuid4()), title=command.title, content=command.content
    )
    async with engine.begin() as cursor:
        res = await cursor.execute(stmt)

    return res.fetchone()


# @registry
# class TodoService:
#     def __init__(self, engine: AsyncEngine, anywise: Anywise):
#         self._engine = engine
#         self._anywise = anywise

#     async def create_todo(
#         self,
#         command: CreateTodo,
#         context: dict[str, ty.Any],
#     ):
#         # BUG, a new anywise is created in sender
#         new_engine = await self._anywise.resolve(AsyncEngine)

#         stmt = insert(Todos).values(
#             id=str(uuid4()), title=command.title, content=command.content
#         )
#         async with self._engine.begin() as cursor:
#             res = await cursor.execute(stmt)

#         return res.fetchone()


"""
bug with entry: does not reuse solved dependency

probably has something todo with use_scope
"""
