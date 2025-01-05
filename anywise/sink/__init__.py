from asyncio.queues import Queue
from typing import Protocol, Sequence

from ..messages import IEvent

# class AbstractSink:
#     def sink(self, event: IEvent) -> None:
#         raise NotImplementedError

# class EventSink:
#     """
#     anywise = Anywise(sink=FileSink())

#     """

#     def sink(self, event: IEvent) -> None: ...


# class FileSink(EventSink):
#     "send event to a file"
#     ...


# class WebSink(EventSink):
#     "send event to a remote http service"
#     ...


# class KafkaSink(EventSink):
#     "send event to kafka"


# class DBSink(EventSink):
#     "save events to database"


class IEventSink[EventType](Protocol):

    async def sink(self, event: EventType | Sequence[EventType]):
        """
        sink an event or a sequence of events to corresponding event sink
        """

    # async def encode(self, event: IEvent) -> str:
    #     ...



class InMemorySink[EventType](IEventSink[EventType]):
    def __init__(self, volume: int = 100):
        self._queue = Queue[IEvent](volume)

    async def sink(self, event: IEvent | Sequence[IEvent]):
        print(f"logging {event}")
        if isinstance(event, Sequence):
            for e in event:
                await self._queue.put(e)
        else:
            await self._queue.put(event)
