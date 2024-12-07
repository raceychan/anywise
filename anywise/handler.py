import queue

# import asyncio
import threading
import typing as ty


class Actor[State, Message]:
    "A future proof actor, would be more useful after python 3.13"
    state: State
    message: Message

    type Handler = ty.Callable[[State, Message], State]

    def __init__(self, state: State, handler: Handler):
        self._state = state
        self._handler = handler

        # Queue for messages
        self._message_queue = queue.Queue[Message]()
        # Lock to ensure only one thread processes messages at a time
        self._lock = threading.Lock()

    def handle(self, message: Message):
        self._handler(self._state, message)

    def send(self, message: Message):
        state = self.handle(message)


class WorkUnit[Context, Message]:
    type Handler = ty.Callable[[Context, Message], Context]

    def __init__(self, context: Context, message_type: type[Message], handler: Handler):
        self.context = context
        self.message_type = message_type
        self.handler = handler