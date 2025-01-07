# Anywise

Anywise provides a universal and flexible API for your application by abstracting function calls into message passing, 
make it easy to build scalable, maintainable, and testable applications.

- Eliminates direct dependencies on implementation details.
- Improves development speed, reduces testing complexity, and enhances the reusability of the application as a whole.
- Promotes best practices and loose coupling.


## Features

- minimal change to existing code, easy to adopt.
- integrated dependency injection system, automatically inject dependency at runtime.
- type-based message system
- strong support to AOP, middlewares, decorators, etc. 

---

Documentation: https://raceychan.github.io/anywise/

Source Code: https://github.com/raceychan/anywise

---

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

Next step, Register command handler and event listeners.

### handler/listener

for simplicity, we will use `function-based` handler here

```py
from anywise import MessageRegistr, BaseGuard
registry = MessageRegistry(command_base=UserCommand, event_base=UserEvent)

async def create_user(
    command: CreateUser, 
    anywise: Anywise, 
    service: UserService = use(user_service_factory)
):
    await users.signup(command.username, command.user_email)
    await anywise.publish(UserCreated(command.username, command.user_email))

async def notify_user(event: UserCreated, service: EmailSender):
    await service.send_greeting(command.user_email)

class IPContext(TypeDict):
    ip: str

class IPLimiter(BaseGuard):
    def __init__(self, throttle_list: tuple[str], white_lst: WhiteList):
        self._lst = throttle_list
        self._white_lst = white_lst

    async def __call__(self, command: UserCommand, context: IPContext):
        if not await self._white_lst.should_pass(command.user_id):
            if context["ip"] in self._lst:
                return ThrottleResponse()

registry.register(IPLimiter, create_user, notify_user)
```

NOTE: you can also use `registry` as a decorator to register handler/listeners.

### Message Source

Message source is where you can your message from.

Here we use fastapi as our message source, but it can be other choices.

```py
from anywise import Anywise
from anywise.integration.fastapi import FastWise

@app.post("/users")
async def signup(command: CreateUser, anywise: FastWise) -> User:
    return await anywise.send(command)
```
