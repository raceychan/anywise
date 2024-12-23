from typing import Any

from ._itypes import IGuard


class AnyWiseError(Exception): ...


class MessageHandlerNotFoundError(AnyWiseError): ...


class NotSupportedHandlerTypeError(AnyWiseError): ...


class UnregisteredMessageError(AnyWiseError):
    def __init__(self, msg: Any):
        super().__init__(f"Handler for {msg} is not found")


class DunglingGuardError(AnyWiseError):
    def __init__(self, guard: IGuard):
        super().__init__(f"Dangling guard {guard}, most likely a bug")
