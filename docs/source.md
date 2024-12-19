
## Features

## use mark to mark a handler with command

### mark a module

```py
# app/features/app.py

from app.features import user

# this would recursively search for all classes and functions
mark(UserCommand)(user)

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
