from dataclasses import dataclass
from typing import Literal, TypedDict


class FastAPIConfig(TypedDict):
    path: str  # "/users/{user_id}"
    http_method: Literal["GET", "POST", "PATCH", "DELETE"]


@dataclass
class UserCommand: ...


@dataclass
class CreateUser(UserCommand):
    __command_meta__ = FastAPIConfig(path="/users", http_method="POST")

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

    __command_meta__ = FastAPIConfig(path="/users/{entity_id}", http_method="PATCH")
    """
    converts this to 
    router = APIRouter()

    @router.patch("/users/{entity_id}")
    async def update_user(command: UpdateUser, anywise: AnyWise):
        await anywise.send(command)
    """
