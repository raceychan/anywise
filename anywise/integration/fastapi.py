from dataclasses import dataclass
from typing import Annotated, ClassVar, Literal, Protocol, TypedDict

from fastapi import APIRouter, Depends, Request

from ..anywise import Anywise


def get_anywise(r: Request) -> Anywise:
    anywise = r.scope["state"]["anywise"]
    return anywise


FastWise = Annotated[Anywise, Depends(get_anywise)]


class FastAPISourceConfig(TypedDict):
    path: str
    http_method: Literal["GET", "POST", "PATCH", "DELETE"]

    # return_type: type
    # response_class: type


class FastAPICommand(Protocol):
    __source_config__: ClassVar[FastAPISourceConfig]


@dataclass
class UserCommand: ...


@dataclass
class CreateUser(UserCommand):
    __source_config__ = FastAPISourceConfig(path="/users", http_method="POST")

    """
    converts this to 
    router = APIRouter()

    @router.post("/users")
    async def create_user(command: CreateUser, anywise: AnyWise):
        await anywise.send(command)
    """


@dataclass
class UpdateUser(UserCommand):
    entity_id: str  # Field(alias="user_id")

    __source_config__ = FastAPISourceConfig(
        path="/users/{entity_id}", http_method="PATCH"
    )
    """
    converts this to 
    router = APIRouter()

    @router.patch("/users/{entity_id}")
    async def update_user(command: UpdateUser, anywise: AnyWise):
        await anywise.send(command)
    """


def autoroute(message: FastAPICommand):
    """
    generate routes from registry

    app = FastAPI()
    app.include_router(autoroute(UserCommand))
    app.include_router(autoroute(InventoryCommand))
    """

    try:
        config = message.__source_config__
    except AttributeError:
        raise

    # APIRoute
    route = router.add_api_route()

    """
    for base in type(message).__mro__:
        merge_config(base.__source_config__)

    base_mapping: dict[type, Router]
    for base in type(message).__mro__:
        ...

    generate APIRoute based on Message.__source_config__
    include route in router

    UserCommand -> APIRouter
    CreateUser -> APIRoute


    type CommandGraph = dict[type, list[CommandGraph]]

    command_graph: CommandGraph = {
        UserCommand: [
            {
                CreateUser: [
                    {CreateUserSub: []}
                ]
            }
        ]
    }
    """
