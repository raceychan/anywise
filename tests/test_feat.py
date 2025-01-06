from typing import TypedDict

from anywise import Anywise, MessageRegistry
from anywise._itypes import EventContext

from .conftest import CreateUser, UserCommand

reg = MessageRegistry(command_base=UserCommand)


class Time(TypedDict):
    name: str


async def signup(cmd: CreateUser, ctx: EventContext[Time]):
    assert isinstance(ctx, dict)


async def test_ctx():
    reg.register(signup)

    aw = Anywise(reg)

    await aw.send(CreateUser("1", "2"))
