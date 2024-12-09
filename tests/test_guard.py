import typing as ty

from anywise import AnyWise, handler_registry

# from anywise.guard import MarkGuard
from anywise._registry import GuardRegistry
from tests.conftest import CreateUser

guard_maker = GuardRegistry()
cmd_handler = handler_registry(CreateUser)


@cmd_handler
async def handler_str(create_user: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "done"


@guard_maker.pre_handle(CreateUser)  # pre handle
async def mark(create_user: CreateUser, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")


@guard_maker.pre_handle(CreateUser)  # pre handle
async def timer(create_user: CreateUser, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["2"]
    else:
        context["processed_by"].append("2")


@guard_maker.post_handle(CreateUser)
async def post(
    create_user: CreateUser, context: dict[str, ty.Any], response: str
) -> str:
    return response


async def test_guard():
    aw = AnyWise()
    aw.include([cmd_handler, guard_maker])
    await aw.send(CreateUser("1", "2"))
