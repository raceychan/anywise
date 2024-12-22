import typing as ty

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from anywise import Anywise
from anywise.integration.fastapi import FastWise

from .message import CreateTodo, ListTodos, Todo
from .table import create_tables
from .todo import registry

todo_router = APIRouter()


# class DB: ...


# def getdb():
#     db = DB()
#     yield db


# class Service:
#     def __init__(self, db: DB = Depends(getdb)):
#         self.db = db


@todo_router.get("/todos")
async def read_todos(anywise: FastWise) -> list[Todo]:
    res = await anywise.send(ListTodos())
    return res


@todo_router.post("/todos")
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
