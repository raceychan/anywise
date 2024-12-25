from datetime import UTC, datetime
from typing import Any, ClassVar, Final, Protocol, TypedDict, cast
from uuid import uuid4

__EventTypeRegistry__: Final[dict[str, type]] = {}


def uuid_factory() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def type_id(cls: type["Event"]) -> str:
    """
    generate a type_id based on event class

    e.g.
    "demo.domain.event:UserCreated"
    """
    return f"{cls.__module__}:{cls.__name__}"


def all_subclasses(cls: type) -> set[type]:
    return set(cls.__subclasses__()).union(
        *[all_subclasses(c) for c in cls.__subclasses__()]
    )


def _init_type_registry():
    __EventTypeRegistry__.update({type_id(cls): cls for cls in all_subclasses(Event)})


def get_event_cls(type_id: str) -> type["Event"]:
    try:
        return __EventTypeRegistry__[type_id]
    except KeyError:
        _init_type_registry()
        # if fail again just raise

    try:
        return __EventTypeRegistry__[type_id]
    except KeyError:
        raise UnregisteredEventError(type_id)


class UnregisteredEventError(Exception):
    def __init__(self, type_id: str):
        _, name = type_id.split(":")
        super().__init__(f"event {name} is not registered")


class IEvent(Protocol):
    @property
    def event_id(self) -> str: ...

    @property
    def aggregate_id(self) -> str: ...

    @property
    def timestamp(self) -> str: ...


class NormalizedEvent(TypedDict):
    # classfields
    event_type: str
    source: str
    version: str

    # base fields
    event_id: str
    aggregate_id: str
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
        __source__: ClassVar[str] = ""  # project name, like demo
        __version__: ClassVar[str] = "1"  # specversion

        aggregate_id: str
        event_id: str = msgspec_field(default_factory=uuid_factory)
        timestamp: str = msgspec_field(default_factory=utc_now)

        def __table_mapping__(self) -> NormalizedEvent:
            base_fields = Event.__struct_fields__
            current_only_fields = self.__struct_fields__[: -len(base_fields)]

            mapping = {f: getattr(self, f) for f in base_fields}
            event_body = {f: getattr(self, f) for f in current_only_fields}

            mapping["event_type"] = type_id(self.__class__)
            mapping["version"] = self.__version__
            mapping["source"] = self.__source__ or "demo"
            mapping["event_body"] = event_body
            return cast(NormalizedEvent, mapping)


# TODO: pydantic version
