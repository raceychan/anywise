from loguru import logger

from anywise import Anywise, BaseGuard, Context, IContext, MessageRegistry
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


async def mark(command: UserCommand, context: IContext) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")


async def timer(command: CreateUser, context: IContext) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["2"]
    else:
        context["processed_by"].append("2")


async def handler_create(
    _: CreateUser, context: Context[dict[str, str]], anywise: Anywise
):
    assert context["processed_by"] == ["1", "2"]
    return "created"


async def handler_update(update_user: UpdateUser, context: Context[dict[str, str]]):
    assert context["processed_by"]
    return "updated"


async def post[R](create_user: CreateUser, context: IContext, response: R) -> R:
    assert response in ("created", "updated")
    return response


user_registry.register(
    LogginGuard,
    handler_create,
    handler_update,
    pre_hanldes=[mark, timer],
    post_handles=[post],
)


async def test_guard():
    aw = Anywise(user_registry, sink=InMemorySink())
    await aw.send(CreateUser("1", "2"))
    await aw.send(UpdateUser("1", "2", "3"))
