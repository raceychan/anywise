import typing as ty

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..anywise import Anywise


def engine_factory() -> AsyncEngine:
    url = "sqlite://"
    return create_async_engine(url)


def get_anywise(r: Request) -> Anywise:
    return r.state.anywise


AnyWise = ty.Annotated[Anywise, Depends(get_anywise)]


class TodoCommand: ...


class CreateTodo(TodoCommand): ...


todo_router = APIRouter(prefix="/todos")


@todo_router.get("/")
async def read_todos(anywise: AnyWise):
    return "hello, world"
