import typing as ty

from loguru import logger

from anywise import Anywise, BaseGuard, GuardFunc, MessageRegistry
from tests.conftest import CreateUser, UpdateUser, UserCommand

user_registry = MessageRegistry(command_base=UserCommand)


from uuid import uuid4


class LogginGuard(BaseGuard):
    _next_guard: GuardFunc

    def __init__(self, *, logger: ty.Any):
        super().__init__()
        self._logger = logger

    async def __call__(self, message: object, context: dict[str, object]):
        if (request_id := context.get("request_id")) is None:
            context["request_id"] = request_id = str(uuid4())

        with logger.contextualize(request_id=request_id):
            try:
                response = await self._next_guard(message, context)
            except Exception as exc:
                logger.error(exc)
            else:
                logger.success(
                    f"Logging request: {request_id}, got response `{response}`"
                )
                return response


user_registry.add_guard([UserCommand], LogginGuard(logger=logger))


@user_registry.pre_handle
async def mark(command: UserCommand, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")

    print(f"\n in guard, {command=}")


# class TimeContext(ty.TypedDict):
#     processed_by: list[str]


@user_registry.pre_handle
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


@user_registry.post_handle
async def post(
    create_user: CreateUser, context: dict[str, ty.Any], response: str
) -> str:
    assert response in ("created", "updated")
    return response


async def test_guard():
    aw = Anywise()
    aw.include(user_registry)
    await aw.send(CreateUser("1", "2"))
    await aw.send(UpdateUser("1", "2", "3"))
