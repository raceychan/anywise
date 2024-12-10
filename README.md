# Anywise

Anywise let you write your application anywise.

---

Source Code: https://github.com/raceychan/anywise

Documentation: On its way here...

---

## Goals

1. isolating bussiness logic from input ports
2. let you write less code than other wise
3. promote best practices and clean code
4. runtime-performance

## Philosophy

1. Non-intrusive
2. dead simple
3. minimalist

## Quck Start

```py
from anywise import Anywise, handler_registry, inject

class UserCommand: ...
class CreateUser(UserCommand): ...
class UserEvent: ...
class UserCreated(UserEvent): ...

userhandler = handler_registry(UserCommand)
userlistener = listener_registry(UserEvent)

@userhandler
async def create_user(
     command: CreateUser, 
     anywise: Anywise, 
     service: UserService = inject(user_service_factory)
):
     await service.create_user(command.username, command.user_email)
     await anywise.publish(UserCreated(command.username, command.user_email))

@userlistener
async def notify_user(event: UserCreated, service: EmailSender):
     await service.send_greeting(command.user_email)

# at your client code

async def main():
     anywise = AnyWise()
     anywise.include([userhandler, userlistener])
     command = CreateUser()
     result = await anywise.send(command)
```

## Tutorial

### register handler with HandlerRegistry

```py
userhandler = handler_registry(UserCommand)
userhanlder(hanlder_func)
```

use HandlerRegistry to decorate / register a function or a class as handlers of a command.

when a function is registered, anywise will can through its signature, if any param is annotated as a subclass of the base command type, it will be registered as a handler of the command.

when a class is registered, anywise will scan through its pulic methods, then repeat the steps to functions.

### use CommandGuard to intercept handler call

```py
from anywise import AnyWise, GuardRegistry, handler_registry

guard_registry = GuardRegistry()
user_registry = handler_registry(UserCommand)


@user_registry
async def handler_create(create_user: CreateUser, context: dict[str, ty.Any]):
    assert context["processed_by"]
    return "done"


@user_registry
async def handler_update(update_user: UpdateUser, context: dict[str, ty.Any]):
    return "done"


@guard_registry.pre_handle
async def mark(command: UserCommand, context: dict[str, ty.Any]) -> None:
    if not context.get("processed_by"):
        context["processed_by"] = ["1"]
    else:
        context["processed_by"].append("1")
```

in this case, `mark` will be called before `handler_update` or `handler_create` gets called.

## Features

- builtin dependency injection
- handler guards
- framework integration
- remote handler

## FAQ

On its way here...
