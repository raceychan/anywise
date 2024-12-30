# Anywise

Decouples the intention behind the execution of application services from the application service itself, whether subjective (via Command) or objective (via Event).

Eliminates direct dependencies on implementation details.

Improves development speed, reduces testing complexity, and enhances the overall reusability of the program.

## Install

```py
pip install anywise
```

## Quick Start

Let start with defining messages:

```py
from anywise import Anywise, MessageRegistry, use

class UserCommand: ...
class CreateUser(UserCommand): ...
class UserEvent: ...
class UserCreated(UserEvent): ...
```

Next step, Register command handler and event listeners.

## Command Handler / Event Listeners

### Function-based handler/listener

```py
registry = MessageRegistry(command_base=UserCommand, event_base=UserEvent)

@registry 
async def create_user(
     command: CreateUser, 
     anywise: Anywise, 
     service: UserService = use(user_service_factory)
):
    await users.signup(command.username, command.user_email)
    await anywise.publish(UserCreated(command.username, command.user_email))

@registry
async def notify_user(event: UserCreated, service: EmailSender):
     await service.send_greeting(command.user_email)

# you can also menually register many handler at once

registry.register_all(create_user, notify_user)
```

### Example usage with fastapi

```py
from anywise import Anywise
from anywise.integration.fastapi import FastWise

@app.post("/users")
async def signup(command: CreateUser, anywise: FastWise) -> User:
    return await anywise.send(command)
```

## Rationale

Anywise is designed and built to:

1. promote best practices and enterprise architecture in python.
2. isolating bussiness logic from input ports, encapsulate application core, maxmize reusability of logic, allowing one app for web api, kafka, flink, etc.
3. let you write less code than other wise
