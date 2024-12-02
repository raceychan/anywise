concept

use anywise to implement hexagonal architecture

# Features

## use mark to mark a handler with command

### mark a module

```py
# app/features/app.py

from app.features import user

# this would recursively search for all classes and functions
mark(UserCommand)(user)

```

### mark a class

```py
def mark(base_command: type, guards: list[ty.Callable] | None = None):
    ...


class UserCommand: ...

class CreateUser(UserCommand):
    user_email: str
    user_name: str

user_handler = mark(UserCommand)
# this would detect all sub commands of user command

@user_handler 
class UserService:
    def __init__(self, user_repo: UserRepo):
        self._user_repo = user_repo

    @user_handler.guard
    async def validate_user(self):
        ...

    async def create_user(cmd: CreateUser):
        ...

    async def remove_user(cmd: RemoveUser):
        ...

    @user_handler.unpack(ChangeUserEmail) 
    async def change_user_email(user_email: str):
        ...
```

### mark a function

```py
base_handler = mark(ICommand)

@base_handler.guard
async def logging:
    ...
```

## usage with fastapi

```bash
pip install `anywise[fastapi]`
```

```py
from anywise import AnyWise
from anywise.plugins.fastapi import autoroute, inject
from app.features.user import user_handler

async def liespan():
    aw = AnyWise(handlers=[user_handler])
    return {"aw": aw}


@app.post("users")
@inject
async def create_user(aw: AnyWise, command: CreateUser):
    await aw.send(command)


@app.get("users")
@inject
async def get_user(aw: AnyWise, query: UserQuery[UserInfo]):
    return await aw.ask(query)
```

### autoroute

```py
class CreateUser:
    web_config = WebConfig(
        "users"
    )

or 

autoroute("users", CreateUser)

# ======= Client =======

app = FastAPI(
    title="app",
    description="my app",
    lifespan=lifespan,
)
app.include_router(autorouter())
```

## sink

transfer your events to correspnding sinks

AWS SQS Sink # forward message to AWS SQS
Kafka Sink # to kafka
HTTP Sink # to a http api
Database Sink # store to database

```py
sink = AWSEventSink(
    queue_url="test-queue",
    region_name="eu-central-1"
)

class UserCreatedEvent:
    ...


sink.add_event(UserCreatedEvent)
aw = AnyWise(
    event_sinks = [AWSEventSink]
)

await aw.publish(UserCreatedEvent)
# this goes directly to corresponding sink
```

## Port

Ports are source of data to our domain

Kafka port
FastAPI port
Rabbit port

```py
import uvloop
from aiokafka import Kafka
from anywise.source import KafkaSource

broker = Kafka(connect_info)
source = KafkaSource(broker)


async def main():
    aw = AnyWise(
        source = KafkaSource
    )

    await aw.listen()
```

### Generate doc

integrate exceptions
integrate openapi
integrate https://www.asyncapi.com/en

## Source-Service-Sink Architecture

     Command      Event
Source  ->  Service  ->  Sink

we receive command from source
service handles commands and generate side-effect
we record these side-effect with events.
then redirect these events to sink.

reference:

https://medium.com/ssense-tech/hexagonal-architecture-there-are-always-two-sides-to-every-story-bc0780ed7d9c

