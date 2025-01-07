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

@reigstry
class ProductService:
    def __init__(self, repo: ProductRepository, aw: Anywise):
        self._repo = repo
        self._aw = aw

    async def add_item(self, command: AddItem):
        item = Item(sku=command.sku, name="item")
        await self._repo.add(item)
        await self._aw.publish(ItemAdded(sku=item.sku, name=item.name))

    async def on_item_added(self, event: ItemAdded):
        product = await self._repo.get(event.sku)
        if len(product.items) >= 1:
            product.status = "available"
        await self._repo.update(prodct)
```

you can use `registry` as a decorator to register handler/listeners

or you can register many handler at once using `MessageRegistry.register_all`

```py
registry.register_all(create_user, notify_user)
```

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
