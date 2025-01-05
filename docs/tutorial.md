# Tutorial

## Message Registry

Use `MessageRegistry` to decorate / register a function as a handler of a command.

```py
from anywise import MessageRegistry

registry = MessageRegistry(command_base=UserCommand)

registry.register(hanlder_func)
```

Use `registry.factory` to declear how a dependency should be resolved

```py
@registry.factory
async def conn(engine=use(engine_factory)) -> AsyncGenerator[AsyncConnection, None]:
    async with engine.begin() as conn:
        yield conn
```

- factory must declear return type
- factory declear with generator/async generator would be considered as a `resource`
- resource will be opened / closed automatically across message
- declear `reuse=False` to config if the factory should be reused across handler/listeners.

checkout [ididi-github](https://github.com/raceychan/ididi) for more details

## Command

### Command handler

a handler `h` for command `c` can be either a method or a function

- For fucntion handler, dependency will be injected into `h` the handler during `anywise.send(c)`
- For method handler, dependency will be injected into its owner type during `anywise.send(c)`

```py
registry = MessageRegistry(command_base=UserEvent)

@registry
class UserService:
    def __init__(self, users: UserRepository=use(user_repo_factory), anywise: Anywise):
        self._users = users
        self._anywise = anywise

    async def create_user(self, command: CreateUser, context: Mapping[str, Any]):
        await self._users.add(User(command.user_name, command.user_email))
        await self._anywise.publish(UserCreated(**comand))
```

- Function/Method that declear a subclass of the command base in its signature will be treated as a handler to that command and its subcommand.
- If two or more handlers that handle the same command are registered, only the lastly registered one will be used.

### Command Guard

you might use Guard to intercept command handling

It is recommended to

- Encapsulate non-business logic inside guards, such as logging, rate-limiting, etc.
- Store non-business related context info in a mutable `context`, such as `request-id`, `x-country`, etc.
- Use inheritance-hierarchy to assign targets for guads.

#### guard target

- The first non-self parameter is regarded as the guard target, which should be a command.
- targeting a base command means targeting all its subcommand, and the base command itself.
- targeting `typing.Any` or `object` to make a global command guard.
- global command guard will always be executed than normal guards

#### Function-based Guard

- use `MessageRegistry.pre_handle` to register a function that only gets called before the command is handled.

```py
@registry.pre_handle
async def validate_command(command: UserCommand, context: dict[str, ty.Any]) -> None:
    if not context["user"]:
        raise InvalidAuthError
```

- use `MessageRegistry.post_handle` to register a function that only gets called after the command is handled

```py
@registry.post_handle
async def log_result(command: UserCommand, context: dict[str, ty.Any], response: R) -> R:
    logger.info(f"{command} is handled with {response=}")
    return response
```

- Guard that guards for a base command will handle all subcommand of the base command

```py
from anywise import AnyWise, MessageRegistry

user_registry = MessageRegistry(command_base=UserCommand)

# in this case, `mark` will be called before `handler_update` or `handler_create` gets called.

@user_registry.pre_handle
async def mark(command: UserCommand, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")

@user_registry
async def handler_create(command: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "done"

@user_registry
async def handler_update(command: UpdateUser, context: dict[str, ty.Any]):
    return "done"

```

Guard that guards for a base command will handle all subcommand of the base command

#### Advanced class-based Guard

Example:

#### class-based Guard

Inherit from `BaseGuard` to make a class-based command guard

```py
from anywise import BaseGuard

class LogginGuard(BaseGuard):
    _next_guard: GuardFunc

    def __init__(self, logger: ty.Any):
        super().__init__()
        self._logger = logger

    async def __call__(self, command: Any, context: dict[str, object]):
        if (request_id := context.get("request_id")) is None:
            context["request_id"] = request_id = str(uuid4())

        with logger.contextualize(request_id=request_id):
            try:
                response = await self._next_guard(command, context)
            except Exception as exc:
                logger.error(exc)
                response =  ErrorResponse(command, context, self._next_guard)
            else:
                logger.success(
                    f"Logging request: {request_id}, got response `{response}`"
                )
            finally:
                return response

# you can add either an instance of LoggingGuard:
user_registry.add_guard(LogginGuard(logger=logger), targets=[UserCommand])

# or the LoggingGuard class, which will be dynamically injected during anywise.send
user_registry.add_guard(LogginGuard, targets=[UserCommand])
```

## Event

## Event Listeners

- same register rule, but each event can have multiple listeners
- event listener can declear `context` in its signature, if so, a immutable `context` object will be shared between listeners.
- event handler is supposed to return `None`, if it returns a value, it will be ignored.

```py
registry = MessageRegistry(event_base=UserEvent)
@registry
async def notify_user(event: UserCreated, context: Mapping[str, Any], email: EmailSender) -> None:
    await email.greet_user(event.user_name, event.user_email)

@registry
async def validate_payment(event: UserCreated, context: Mapping[str, Any], payment: PaymentService) -> None:
    await payment.validte_user_payment(event.user_name, event.user_email)
```

### Provide Startegy to alter send and publish behavior

- Provide an async callble `SendStrategy` or `PublishStrategy` to change the default behavior of how anywise send or publish message
- You might provide strategy like a class with dependencies and async def __call__ for more advanced usage.

```py
from anywise import Anywise, MessageRegistry, concurrent_publish, EventListeners

anywise = Anywise(user_message_registry, publisher=concurrent_publish)

# now all event listeners that listen to type(event) will be called concurrently
await anywise.publish(event) 
```

## Inspect

anywise provide a simple api for inspection, make debugging easy.

Use `Anywise.inspect` to inspect registered handler / listeners

```py
print(anywise.inspect[UserCreated])

>>> [<function react_to_event at 0x7fe032786020>]
```