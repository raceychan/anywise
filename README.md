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

## Quck Start

Let start with defining messages:

```py
from anywise import Anywise, MessageRegistry, use

class UserCommand: ...
class CreateUser(UserCommand): ...
class UserEvent: ...
class UserCreated(UserEvent): ...
```

register command handler and event listeners.

```py
registry = MessageRegistry(command_base=UserCommand, event_base=UserEvent)


@registry # this is equivalent to registry.register(create_user)
async def create_user(
     command: CreateUser, 
     anywise: Anywise, 
     service: UserService = use(user_service_factory)
):
     await service.create_user(command.username, command.user_email)
     await anywise.publish(UserCreated(command.username, command.user_email))


@registry
async def notify_user(event: UserCreated, service: EmailSender):
     await service.send_greeting(command.user_email)

# you can also menually register many handler at once

registry.register_all(create_user, notify_user)
```

Example usage with fastapi

```py
from anywise import Anywise
from anywise.integration.fastapi import FastWise

@app.post("/users")
async def signup(command: CreateUser, anywise: FastWise) -> User:
    return await anywise.send(command)
```

## Tutorial

### register command handler / event listeners with MessageRegistry

```py
from ididi import MessageRegistry

registry = MessageRegistry(UserCommand)

registry.register(hanlder_func)
```

use MessageRegistry to decorate / register a function or a class as handlers of a command.

#### Command handler

- function that declear a subclass of the command base in its signature will be treated as a handler to the command.

- class that contains a series of methods that declear a subclass of the command base in its signature, each method will be treated as a handler to the corresponding command.

- if two handlers with same command are registered, only lastly registered one will be used.

#### Event listeners

same register rule, but each event can have multiple listeners

### use `Guard` to intercept command handling

```py
from anywise import AnyWise, GuardRegistry, handler_registry

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

#### Guard that guard for a base command will handle all subcommand of the base command

A handler can handle multiple command type

```py
@user_registry
async def handle_multi(command: CreateUser | UpdateUser, context: dict[str, ty.Any]):
    ...
```

in this case, `handle_multi` will handle either `CreateUser` or `UpdateUser`

#### Advanced user-defined Guard

You might define a more advanced stateful guard by inheriting from BaseGuard

Example:

```py
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

user_registry.add_guard([UserCommand], LogginGuard(logger=logger))
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
