from typing import Any

from ._itypes import IGuard


class AnyWiseError(Exception): ...


class MessageHandlerNotFoundError(AnyWiseError):
    def __init__(self, base_type: Any, handler: Any):
        super().__init__(
            f"can't find param of type `{base_type}` in {handler} signature"
        )


class NotSupportedHandlerTypeError(AnyWiseError): ...


class UnregisteredMessageError(AnyWiseError):
    def __init__(self, msg: Any):
        super().__init__(f"Handler for message {msg} is not found")


class DunglingGuardError(AnyWiseError):
    def __init__(self, guard: IGuard):
        super().__init__(f"Dangling guard {guard}, most likely a bug")
