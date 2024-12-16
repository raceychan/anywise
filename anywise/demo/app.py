import typing as ty

import uvicorn
from fastapi import FastAPI

from ..anywise import Anywise
from .todo import todo_router


class AppState(ty.TypedDict):
    anywise: Anywise


async def lifespan(app: FastAPI) -> ty.AsyncGenerator[AppState, None]:
    anywise = Anywise()
    # anywise.include()
    yield {"anywise": anywise}


def app_factory():
    VERSION = "1"
    root_path = f"/api/v{VERSION}"
    app = FastAPI(lifespan=lifespan, version=VERSION, root_path=root_path)

    app.include_router(todo_router)
    return app


if __name__ == "__main__":
    uvicorn.run(app_factory)
