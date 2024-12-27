from ..events import IEvent

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
