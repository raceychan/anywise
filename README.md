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

Anywise integrates [ididi](https://github.com/raceychan/ididi) for dependency injection.
define your dependency after the message parameter, they will be resolved when you send a command or publish an event.

```py
from anywise import Anywise, handler_registry, inject

class UserCommand: ...
class CreateUser(UserCommand): ...
class UserEvent: ...
class UserCreated(UserEvent): ...

registry = MessageRegistry(command_base=UserCommand, event_base= UserEvent)

@registry
async def create_user(
     command: CreateUser, 
     anywise: Anywise, 
     service: UserService = inject(user_service_factory)
):
     await service.create_user(command.username, command.user_email)
     await anywise.publish(UserCreated(command.username, command.user_email))

@registry
async def notify_user(event: UserCreated, service: EmailSender):
     await service.send_greeting(command.user_email)

# at your client code

async def main():
     anywise = AnyWise()
     anywise.include(user_registry)
     result = await anywise.send(CreateUser())
```

## Tutorial

### register command handler / event listeners with MessageRegistry

```py
registry = MessageRegistry(UserCommand)
registry(hanlder_func)
```

use MessageRegistry to decorate / register a function or a class as handlers of a command.

when a function is registered, anywise will can through its signature, if any param is annotated as a subclass of the base command type, it will be registered as a handler of the command.

when a class is registered, anywise will scan through its pulic methods, then repeat the steps to functions.

### use `Guard` to intercept command handling.

```py
from anywise import AnyWise, GuardRegistry, handler_registry

user_registry = MessageRegistry(command_base=UserCommand)

@user_registry
async def handler_create(create_user: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "done"


@user_registry
async def handler_update(update_user: UpdateUser, context: dict[str, ty.Any]):
    return "done"
```

#### Guard that guard for a base command will handle all subcommand of the base command

```py
@user_registry.pre_handle
async def mark(command: UserCommand, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")
```

in this case, `mark` will be called before `handler_update` or `handler_create` gets called.

a handler can also handle multiple command type

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

- builtin dependency injection
- handler guards
- framework integration
- remote handler

## Current limitations

- currently `Anywise.send` does not provide accurate typing information, but annotated as return `typing.Any`
This have no runtime effect, but is a good to have feature.
It is expected to be solved before anywise v1.0.0

## FAQ

On its way here...
