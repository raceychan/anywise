# Anywise

Anywise is a framework for decoupling the business logic of your application from infrastructures.

This allows you to use the same code to handle message from various message sources, web api, message queue, AWS lambda, etc.

---

Source Code: https://github.com/raceychan/anywise

Documentation: On its way here...

---

## Rationale

1. promote best practices and enterprise architecture in python
2. isolating bussiness logic from input ports, allowing one app for web api, kafka, flink, etc.
3. let you write less code than other wise

## Install

```py
pip install anywise
```

## Quick Start

Let start with defining messages:

you can define messages however you like, it just needs to be a class, our recommendations are:

- `msgspec.Struct`
- `pydantic.BaseModel`
- `dataclasses.dataclass`

```py
class UserCommand: ...
class CreateUser(UserCommand): ...
class UserEvent: ...
class UserCreated(UserEvent): ...
```

register command handler and event listeners.

### Function-based handler/listener

```py
from anywise import Anywise, MessageRegistry, use
# if only command_base is provided, then it will only register command handlers, same logic for event_base
registry = MessageRegistry(command_base=UserCommand, event_base=UserEvent)

# @registry is equivalent to registry.register(create_user)
@registry 
async def create_user(
     command: CreateUser, 
     anywise: Anywise, 
     auth: UserService = use(user_service_factory)
):
     await auth.signup(command.username, command.user_email)
     await anywise.publish(UserCreated(command.username, command.user_email))


@registry
async def notify_user(event: UserCreated, email: EmailSender):
     await email.send_greeting(command.user_email)

# you can also menually register many handler at once
registry.register_all(create_user, notify_user)
```

### Class based handler/listener

You can also register a class, then each public method that declear command in its signature will be registered as handler, the class itself will be resolved at message handling time.

- Declear dependency in class constructor.
- If the registered class does not depends on, directly or indirectly, any resource, it will be reused across messages

```py
@registry 
class UserService:
    def __init__(
        self, 
        email_sender: EmailSender,
        auth_service: AuthService=use(auth_service_factory),
        anywise: Anywise
    ):
        self._email_sender = email_sender
        self._auth_service = auth_service
        self._anywise = anywise

    async def create_user(self, command: CreateUser, anywise: Anywise):
        await self._auth_service.signup_user(command.username, command.user_email)
        await self._anywise.publish(UserCreated(command.username, command.user_email))


    async def notify_user(self, event: UserCreated, service: EmailSender):
        await self._email_sender.greet_user(command.user_email)
```

### Example usage with fastapi

```py
from anywise import Anywise
from anywise.integration.fastapi import FastWise

@app.post("/users")
async def signup(command: CreateUser, anywise: FastWise) -> User:
    return await anywise.send(command)
```

## Tutorial

### register command handler / event listeners with MessageRegistry

use `MessageRegistry` to decorate / register a function as a handler of a command.

```py
from ididi import MessageRegistry

registry = MessageRegistry(UserCommand)

registry.register(hanlder_func)
```

#### use `registry.factory` to declear how a dependency should be resolved

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

#### Command handler

- function that declear a subclass of the command base in its signature will be treated as a handler to the command.

```py
@registry
async def signup(command: CreateUser)
```

- class that contains a series of methods that declear a subclass of the command base in its signature, each method will be treated as a handler to the corresponding command.

- if two handlers with same command are registered, only lastly registered one will be used.

- command handler can declear a `context` parameter in its signature, if so, a mutable dict object will be passed as `context`, `context` is shared between guards and handler.

```py
context = {}
await anywise.send(command, context)
```

- A handler can handle multiple command type

```py
@user_registry
async def handle_multi(command: CreateUser | UpdateUser, context: dict[str, ty.Any]):
    ...
```

in this case, `handle_multi` will handle either `CreateUser` or `UpdateUser`

#### Event listeners

- same register rule, but each event can have multiple listeners
- event listener can declear `context` in its signature, if so, a immutable `context` object will be shared between listeners.

```py
context = MappingProxy(dict())
await anywise.publish(event, context)
```

### use `Guard` to intercept command handling

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
async def handler_create(create_user: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "done"

@user_registry
async def handler_update(update_user: UpdateUser, context: dict[str, ty.Any]):
    return "done"

```
Guard that guards for a base command will handle all subcommand of the base command

#### Advanced class-based Guard

Example:

Inherit from `BaseGuard` to make a class-based command guard

```py
from anywise import BaseGuard

class LogginGuard(BaseGuard):
    _next_guard: GuardFunc

    def __init__(self, logger: ty.Any):
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

# you can add either an instance of LoggingGuard:
user_registry.add_guard([UserCommand], LogginGuard(logger=logger))

# or the LoggingGuard class, which will be dynamically injected during anywise.send
user_registry.add_guard([UserCommand], LogginGuard)
```


## Features

- builtin dependency injection(powerd by [ididi](https://github.com/raceychan/ididi))
    - Define your dependency after the message parameter, they will be resolved when you send a command or publish an event.
    - For each handler that handles the initial message, a scope will be created to manage resources.
    - Subsequent handlers will share the same scope.

- handler guards
- framework integration
- remote handler

## Terms and concepts

- A `Message` is a pure data object that is used to carry data that is needed for our application to respond. Also known as data transfer object.

- A `Message` class often contains no behavior(method), and is immutable.

### Command, Query and Event

- `Command` carries pre-define intend, each command should have a corresponding `handler` that will mutate state, in the context of DDD, each command will always trigger a behavior of an aggregate root.

- `Query` is a subclass of Command, where it also carry pre-define intend, but instead of mutate state, it will be responded by a present state of the application.

In other words, command and query corresponds to write and read.

- `Event` carries a record of an interested domain-related activity, often captures the side effect caused by a `Command`. an `Event` can have zero to many `listener`s

## Current limitations

- currently `Anywise.send` does not provide accurate typing information, but annotated as return `typing.Any`
This have no runtime effect, but is a good to have feature.
It will be solved before anywise v1.0.0

## FAQ

On its way here...
