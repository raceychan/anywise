import typing as ty

from loguru import logger

from anywise import Anywise, BaseGuard, IContext, MessageRegistry
from anywise.sink import InMemorySink
from tests.conftest import CreateUser, UpdateUser, UserCommand

user_registry = MessageRegistry(command_base=UserCommand)

from uuid import uuid4


class LogginGuard(BaseGuard):

    def __init__(self):
        super().__init__()
        self._logger = logger

    async def __call__(self, command: UserCommand | CreateUser, context: IContext):
        if (request_id := context.get("request_id")) is None:
            context["request_id"] = request_id = str(uuid4())

        with logger.contextualize(request_id=request_id):
            try:
                response = await super().__call__(command, context)
            except Exception as exc:
                logger.error(exc)
                raise
            else:
                logger.success(
                    f"Logging request: {request_id}, got response `{response}`"
                )
                return response


user_registry.add_guards(LogginGuard)


@user_registry.pre_handle
async def mark(command: UserCommand, context: IContext) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")


class TimeContext(ty.TypedDict):
    processed_by: list[str]


@user_registry.pre_handle
async def timer(command: CreateUser, context: IContext) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["2"]
    else:
        context["processed_by"].append("2")


@user_registry
async def handler_create(_: CreateUser, context: TimeContext, anywise: Anywise):
    assert context["processed_by"] == ["1", "2"]
    return "created"


@user_registry
async def handler_update(update_user: UpdateUser, context: TimeContext):
    assert context["processed_by"]
    return "updated"


@user_registry.post_handle
async def post[R](create_user: CreateUser, context: IContext, response: R) -> R:
    assert response in ("created", "updated")
    return response


async def test_guard():
    aw = Anywise(user_registry, sink=InMemorySink())
    await aw.send(CreateUser("1", "2"))
    await aw.send(UpdateUser("1", "2", "3"))
