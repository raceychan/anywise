import typing as ty

from anywise import Anywise, GuardRegistry, make_registry
from tests.conftest import CreateUser, UpdateUser, UserCommand

guard_registry = GuardRegistry()
user_registry = make_registry(command_base=UserCommand)


@guard_registry.pre_handle
async def mark(command: UserCommand, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")

    print("\n", command)


@guard_registry.pre_handle
async def timer(command: CreateUser, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["2"]
    else:
        context["processed_by"].append("2")


@user_registry
async def handler_create(create_user: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"] == ["1", "2"]
    return "created"


@user_registry
async def handler_update(update_user: UpdateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "updated"


@guard_registry.post_handle
async def post(
    create_user: CreateUser, context: dict[str, ty.Any], response: str
) -> str:
    assert response in ("created", "updated")
    return response


async def test_guard():
    aw = Anywise()
    aw.include([user_registry, guard_registry])
    await aw.send(CreateUser("1", "2"))
    await aw.send(UpdateUser("1", "2", "3"))
