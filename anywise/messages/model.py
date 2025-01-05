from datetime import UTC, datetime
from functools import singledispatchmethod
from typing import Any, ClassVar, Final, Protocol, Self, Sequence, TypedDict, cast
from uuid import uuid4

__EventTypeRegistry__: Final[dict[str, type]] = {}

# TODO: rename to folder message
# add a Command Model, with type registry


def uuid_factory() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def deafult_typeid(cls: type["Event"]) -> str:
    """
    generate a type_id based on event class

    e.g.
    "demo.domain.event:UserCreated"
    """
    # return cls.__type_id__()
    return f"{cls.__module__}:{cls.__name__}"


def all_subclasses(cls: type) -> set[type]:
    return set(cls.__subclasses__()).union(
        *[all_subclasses(c) for c in cls.__subclasses__()]
    )


def get_event_cls(event_type_id: str) -> type["Event"]:
    try:
        return __EventTypeRegistry__[event_type_id]
    except KeyError:
        __EventTypeRegistry__.update(
            {deafult_typeid(cls): cls for cls in all_subclasses(Event)}
        )
        # if fail again just raise

    try:
        return __EventTypeRegistry__[event_type_id]
    except KeyError:
        raise UnregisteredEventError(event_type_id)


class UnregisteredEventError(Exception):
    def __init__(self, type_id: str):
        name = type_id.replace(":", ".")
        super().__init__(f"event {name} is not registered")


class IEvent(Protocol):
    @property
    def event_id(self) -> str: ...

    @property
    def entity_id(self) -> str: ...

    @property
    def timestamp(self) -> str: ...

    @classmethod
    def __type_id__(cls) -> str: ...

    def __normalized__(self) -> "NormalizedEvent": ...


class NormalizedEvent(TypedDict):
    # classfields
    event_type: str
    source: str
    version: str

    # base fields
    event_id: str
    entity_id: str
    timestamp: str

    # current only fields
    event_body: dict[str, Any]


try:
    from msgspec import Struct
except ImportError:
    pass
else:

    from msgspec import field as msgspec_field

    class Event(Struct, frozen=True, kw_only=True):
        __source__: ClassVar[str] = "unspecified"  # project name, like demo
        __version__: ClassVar[str] = "1"  # specversion

        entity_id: str
        event_id: str = msgspec_field(default_factory=uuid_factory)
        timestamp: str = msgspec_field(default_factory=utc_now)

        @classmethod
        def __type_id__(cls) -> str:
            "generate a unique id for event type, e.g. 'demo.domain.event:UserCreated', if class is renamed make sure to update this method"
            return deafult_typeid(cls)

        def __normalized__(self) -> NormalizedEvent:
            base_fields = Event.__struct_fields__
            current_only_fields = self.__struct_fields__[: -len(base_fields)]

            mapping = {f: getattr(self, f) for f in base_fields}
            event_body = {f: getattr(self, f) for f in current_only_fields}

            mapping["event_type"] = deafult_typeid(self.__class__)
            mapping["version"] = self.__version__
            mapping["source"] = self.__source__
            mapping["event_body"] = event_body
            return cast(NormalizedEvent, mapping)

    class Entity(Struct, kw_only=True):
        entity_id: str

        @singledispatchmethod
        @classmethod
        def apply(cls, event: Event) -> "Self":
            raise NotImplementedError

        @apply.register
        def _(self, _: object) -> "Self":
            raise NotImplementedError

        @classmethod
        def rebuild(cls, events: Sequence[Event]) -> "Self":
            create, rest = events[0], events[1:]
            self = cls.apply(create)

            for e in rest:
                self.apply(e)

            return self


# TODO: pydantic version
