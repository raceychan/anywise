import typing as ty


class IEnvelope(ty.Protocol):
    """
    Meta data of event
    encryption type, schema, key, and serialization format. etc.
    """

    headers: "EventMeta"
    event: "IEvent"


class EventMeta(ty.TypedDict):
    """
    event_type: anywise.utils.Event
    # could be 'application_id:module_name:class_name'

    """

    event_type: str  # used to ser/deser event
    event_version: str  # use to compat events
    event_source: str  # events/event_type/v1, where user can checkout openapi schema


class IEvent(ty.Protocol):
    """
    {
        "specversion" : "1.0",
        "type" : "com.github.pull_request.opened",
        "source" : "https://github.com/cloudevents/spec/pull",
        "datacontenttype" : "text/xml",
        --- metas

        "subject" : "123",
        "id" : "A234-1234-1234",
        "time" : "2018-04-05T17:31:00Z",
        "comexampleextension1" : "value",
        "comexampleothervalue" : 5,
        "data" : "<much wow=\"xml\"/>"
    }
    """

    event_id: str  # uuid
    entity_id: str  # uuid
    timestamp: str  # iso-format utc datetime str


class EventSink:
    def send(self, event: IEvent) -> None: ...


class FileSink(EventSink):
    "send event to a file"
    ...


class WebSink(EventSink):
    "send event to http service"
    ...


class KafkaSink(EventSink):
    "send event to kafka"


class EmailSink(EventSink): ...
"""
@notify(UserCreated, to_sink=True)
async send_email(service: EmailService, event: UserCreated):
    ...


class PGEventStore(Sink):
    def write(self, event: Event):
        update(events).where(event_id=event.id).values(is_consumed=True)
"""


class DBSink(EventSink):
    "save events to database"
