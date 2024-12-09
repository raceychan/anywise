import typing as ty

from anywise import AnyWise, handler_registry

# from anywise.guard import MarkGuard
from anywise._registry import GuardFunc, GuardRegistry
from tests.conftest import CreateUser

guard_maker = GuardRegistry()
cmd_handler = handler_registry(CreateUser)


@cmd_handler
async def handler_str(create_user: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "done"


@guard_maker.register(CreateUser)  # pre handle
async def mark(create_user: CreateUser, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")


async def test_guard():
    aw = AnyWise()
    aw.include([cmd_handler, guard_maker])
    await aw.send(CreateUser("1", "2"))
