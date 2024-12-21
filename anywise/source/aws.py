# https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html

# Define some functions to perform the CRUD operations
import typing as ty

import asyncio
from ..anywise import Anywise

Event = ty.NewType("Event", dict[str, ty.Any])
Context = ty.NewType("Context", dict[str, ty.Any])
type LambdaHandler = ty.Callable[[Event, Context], ty.Any]

anywise = Anywise()

class UserCreated: ...

def lambda_handler(event: UserCreated, context: Context):
    """Provide an event that contains the following keys:
    - operation: one of the operations in the operations dict below
    - payload: a JSON object containing parameters to pass to the
      operation being performed
    """

    # operation = event["operation"]
    # payload = event["payload"]

    asyncio.run(anywise.send(event))
