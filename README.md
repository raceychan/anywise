# Anywise

Anywise is a framework designed to decouple the business logic of your application from its infrastructure, enabling you to use the same code to handle messages from various sources such as web APIs, message queues, AWS Lambda, and more.

Despite being inspired by Hexagonal Architecture and Event-Driven Architecture, Anywise does not bind itself to any specific purpose.

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

