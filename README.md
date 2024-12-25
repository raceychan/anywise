# Anywise

Anywise is a framework designed to decouple the business logic of your application from its infrastructure, enabling you to use the same code to handle messages from various sources such as web APIs, message queues, AWS Lambda, and more.

Despite being inspired by Hexagonal Architecture and Event-Driven Architecture, Anywise does not bind itself to any specific purpose.

---

Source Code: https://github.com/raceychan/anywise

Documentation: On its way here...

---

## Rationale

Anywise is designed and built to:

1. promote best practices and enterprise architecture in python.
2. isolating bussiness logic from input ports, encapsulate application core, maxmize reusability of logic, allowing one app for web api, kafka, flink, etc.
3. avoid redundant scripts
4. let you write less code than other wise

## Install

```py
pip install anywise
```

## Quick Start

Let start with defining messages:

You can define messages however you like, it just needs to be a class, our recommendations are:

- `msgspec.Struct`
- `pydantic.BaseModel`
- `dataclasses.dataclass`

```py
class UserCommand: ...
class CreateUser(UserCommand): ...
class UserEvent: ...
class UserCreated(UserEvent): ...
```

Next step, Register command handler and event listeners.

### Function-based handler/listener

```py
from anywise import Anywise, MessageRegistry, use
# if only command_base is provided, then it will only register command handlers, same logic for event_base
registry = MessageRegistry(command_base=UserCommand, event_base=UserEvent)

@registry 
async def create_user(
    command: CreateUser, 
    anywise: Anywise, 
    users: UserRepository=use(users_factory)
):
    await users.signup(command.username, command.user_email)
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
        users: UserRepository=use(users_factory),
        anywise: Anywise
    ):
        self._email_sender = email_sender
        self._users = users
        self._anywise = anywise

    async def create_user(self, command: CreateUser, anywise: Anywise):
        await self._users.signup(command.username, command.user_email)
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

### Use MessageRegistry to decorate / register a function or a class as handlers of a command

use `MessageRegistry` to decorate / register a function as a handler of a command.

```py
from anywise import MessageRegistry

registry = MessageRegistry(command_base=UserCommand)

registry.register(hanlder_func)
```

<<<<<<< HEAD
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

=======
>>>>>>> version/0.1.5
#### Command handler

a handler `h` for command `c` can be either a method or a function

<<<<<<< HEAD
```py
@registry
async def signup(command: CreateUser)
```

- class that contains a series of methods that declear a subclass of the command base in its signature, each method will be treated as a handler to the corresponding command.
=======
- For fucntion handler, dependency will be injected into `h` the handler during `anywise.send(c)`
- For method handler, dependency will be injected into its owner type during `anywise.send(c)`
>>>>>>> version/0.1.5

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

- Class that contains a series of methods that declear a subclass of the command base in its signature, each method will be treated as a handler to the corresponding command.

- If two or more handlers that handle the same command are registered, only the lastly registered one will be used.

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
<<<<<<< HEAD
- event listener can declear `context` in its signature, if so, a immutable `context` object will be shared between listeners.

```py
context = MappingProxy(dict())
await anywise.publish(event, context)
```
=======
- event listener should return None
>>>>>>> version/0.1.5

```py
registry = MessageRegistry(event_base=UserEvent)
@registry
async def notify_user(event: UserCreated, context: Mapping[str, Any], email: EmailSender) -> None:
    await email.greet_user(event.user_name, event.user_email)

@registry
async def validate_payment(event: UserCreated, context: Mapping[str, Any], payment: PaymentService):
    await payment.validte_user_payment(event.user_name, event.user_email)
```

### Strategy

- Provide an async callble `SendStrategy` or `PublishStrategy` to change the default behavior of how anywise send or publish message
- You might provide strategy like a class with dependencies and async def __call__ for more advanced usage.

```py
from anywise import Anywise, MessageRegistry, concurrent_publish, EventListeners

anywise = Anywise(user_message_registry, publisher=concurrent_publish)

# now all event listeners that listen to type(event) will be called concurrently
await anywise.publish(event) 

```

### Command Guard

you might use Guard to intercept command handling

It is recommended to

- encapsulate non-business logic inside guards, such as logging, rate-limiting, etc.
- store non-business related context info in a mutable `context`, such as `request-id`, `x-country`, etc.
- use inheritance-hierarchy to assign targets for guads.

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
<<<<<<< HEAD
Guard that guards for a base command will handle all subcommand of the base command

#### Advanced class-based Guard

Example:
=======

#### class-based Guard
>>>>>>> version/0.1.5

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


## Features

- builtin dependency injection(powerd by [ididi](https://github.com/raceychan/ididi))
    - Define your dependency after the message parameter, they will be resolved when you send a command or publish an event.
    - For each handler that handles the initial message, a scope will be created to manage resources.
    - Subsequent handlers will share the same scope.

- handler guards
- framework integration
- remote handler

## Terms and concepts

what do we mean when we use these words 

- A `Message` is a pure data object that is used to carry data that is needed for our application to respond. Also known as data transfer object.

- A `Message` class often contains no behavior(method), and is immutable.

### Command, Query and Event

- `Command` carries pre-define intend, each command should have a corresponding `handler` that will mutate state, in the context of DDD, each command will always trigger a behavior of an aggregate root.

- `Query` is a subclass of Command, where it also carry pre-define intend, but instead of mutate state, it will be responded by a present state of the application.

In other words, command and query corresponds to write and read.

- `Event` carries a record of an interested domain-related activity, often captures the side effect caused by a `Command`. an `Event` can have zero to many `listener`s

## Current limitations and planning fix

- currently `Anywise.send` does not provide accurate typing information, but annotated as return `typing.Any`
This have no runtime effect, but is a good to have feature.
It will be solved before anywise v1.0.0

- currently if a handler needs to receive `context`, it must declear the context parameter with name `context`, in future it will be decleared as type.

## FAQ

On its way here...
