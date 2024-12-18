import typing as ty

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from anywise import Anywise
from anywise.integration.fastapi import FastWise

from .db import create_tables
from .model import CreateTodo, ListTodos
from .todo import registry

todo_router = APIRouter(prefix="/todos")


@todo_router.get("/")
async def read_todos(anywise: FastWise) -> list[dict[str, ty.Any]]:
    res = await anywise.send(ListTodos())
    return res


@todo_router.post("/")
async def _(command: CreateTodo, anywise: FastWise) -> str:
    res = await anywise.send(command)
    return res


class AppState(ty.TypedDict):
    anywise: Anywise


async def lifespan(app: FastAPI) -> ty.AsyncGenerator[AppState, None]:
    anywise = Anywise()
    anywise.include(registry)
    async with anywise.scope("app") as app_scope:
        app_scope.register_dependent(anywise, Anywise)
        engine = await app_scope.resolve(AsyncEngine)
        await create_tables(engine)
        yield {"anywise": anywise}


def app_factory():
    VERSION = "1"
    root_path = f"/api/v{VERSION}"
    app = FastAPI(lifespan=lifespan, version=VERSION, root_path=root_path)
    app.include_router(todo_router)
    return app
