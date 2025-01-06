import typing as ty

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from anywise import Anywise
from anywise.integration.fastapi import FastWise

from .message import CreateTodo, ListTodoEvents, ListTodos, RenameTodo, Todo
from .table import create_tables
from .todo import registry

todo_router = APIRouter()


@todo_router.get("/todos")
async def read_todos(anywise: FastWise) -> list[Todo]:
    res = await anywise.send(ListTodos())
    return res


@todo_router.get("/events")
async def read_todo_events(todo_id: str, anywise: FastWise) -> list[dict[str, ty.Any]]:
    return await anywise.send(ListTodoEvents(todo_id=todo_id))


@todo_router.post("/todos")
async def _(command: CreateTodo, anywise: FastWise) -> str:
    res = await anywise.send(command)
    return res


@todo_router.put("/todos/{todo_id}")
async def _(command: RenameTodo, anywise: FastWise):
    return await anywise.send(command)


class AppState(ty.TypedDict):
    anywise: Anywise


async def lifespan(app: FastAPI) -> ty.AsyncGenerator[AppState, None]:
    anywise = Anywise()
    anywise.include(registry)
    async with anywise.scope("app") as app_scope:
        app_scope.register_singleton(anywise, Anywise)
        engine = await app_scope.resolve(AsyncEngine)
        await create_tables(engine)
        yield {"anywise": anywise}


def app_factory():
    VERSION = "1"
    root_path = f"/api/v{VERSION}"
    app = FastAPI(lifespan=lifespan, version=VERSION, root_path=root_path)
    app.include_router(todo_router)
    return app
