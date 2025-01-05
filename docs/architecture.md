# Architecture

we will talk about how to use anywise for applying architectural patterns in event driven microservices

## Terms and concepts

Before we start, let's clearify some terms and concept, so that you know what do we mean when we use these words.

- A `Message` is a pure data object that is used to carry data that is needed for our application to respond. Also known as data transfer object.

- A `Message` class often contains no behavior(method), and is immutable.

### Command, Query and Event

- `Command` carries pre-define intend, each command should have a corresponding `handler` that will mutate state, in the context of DDD, each command will always trigger a behavior of an aggregate root.

- `Query` is a subclass of Command, where it also carry pre-define intend, but instead of mutate state, it will be responded by a present state of the application.

In other words, command and query corresponds to write and read.

- `Event` carries a record of an interested domain-related activity, often captures the side effect caused by a `Command`. an `Event` can have zero to many `listener`s

### DDD

anywise can be used to publish domain events, without specifically collect events from entity

reference: https://github.com/cosmicpython/code/blob/master/src/allocation/service_layer/unit_of_work.py

```py
def collect_new_events(self):
    for product in self.products.seen:
        while product.events:
            yield product.events.pop(0)
```


### Vertical slicing

we can use anywise to avoid direct dependent on other slices.


for example, given two slice, order and payment, 
we want order to process once payment is finished


```py
from fastapi import APIRouter, Depends
from app.base.auth import AuthService
from app.payments.message import CreatePayment, PaymentResponse
from app.payments.services import PaymentService

router = APIRouter()

@router.post("/", response_model=PaymentResponseSchema)
def create_payment(
    create_payment: CreatePayment, current_user: str = Depends(AuthService.get_current_user)
):
    res = await anywise.send(create_payment, dict(user=current_user))
    event = PaymentCreatedEvent(payment_id=res.id)
    await anywise.publish(event)
    return res
```

in order service, we can listen to the event

```py
from app.order.service import OrderService

@events.listen(PaymentCreatedEvent)
async def start_order(event: PaymentCreatedEvent):
    await order_service.start_order(event.payment_id)
```


### CQRS


### Event Sourcing


### Choreography, Orchestration

