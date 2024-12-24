from datetime import UTC, datetime
from typing import Any, ClassVar, Final
from uuid import uuid4

__EventTypeRegistry__: Final[dict[str, type]] = {}


def uuid_factory() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def type_id(cls: type["Event"]) -> str:
    return f"{cls.__module__}:{cls.__name__}:v{cls.__version__}"


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
        _, name, _ = type_id.split(":")
        super().__init__(f"event {name} is not registered")


try:
    from msgspec import Struct
    from msgspec import field as msgspec_field
except ImportError:
    pass
else:

    class Event(Struct, frozen=True, kw_only=True):
        __source__: ClassVar[str] = ""  # project name, like demo
        __version__: ClassVar[str] = "1"  # specversion

        event_id: str = msgspec_field(default_factory=uuid_factory)
        aggregate_id: str
        timestamp: str = msgspec_field(default_factory=utc_now)

        def to_dict(self) -> dict[str, Any]:
            reserved_field = Event.__struct_fields__
            all_fields: dict[str, Any] = {}
            body = {}
            for f in self.__struct_fields__:
                if f not in reserved_field:
                    body[f] = getattr(self, f)
                else:
                    all_fields[f] = getattr(self, f)
            all_fields["event_body"] = body
            return all_fields
