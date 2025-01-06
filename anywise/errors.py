from typing import Any, Callable

from ._itypes import IGuard


class AnyWiseError(Exception): ...


class NotSupportedHandlerTypeError(AnyWiseError):
    def __init__(self, handler: Any):
        super().__init__(f"{handler} of type {type(handler)} is not supported")


class HandlerRegisterFailError(AnyWiseError): ...


class InvalidMessageTypeError(HandlerRegisterFailError):
    def __init__(self, msg_type: type):
        super().__init__(f"{msg_type} is not a valid message type")


class MessageHandlerNotFoundError(HandlerRegisterFailError):
    def __init__(self, base_type: Any, handler: Any):
        super().__init__(f"can't find param of type `{base_type}` in {handler}")


class InvalidHandlerError(HandlerRegisterFailError):
    def __init__(self, basetype: type, msg_type: type, handler: Callable[..., Any]):
        msg = f"{handler} is receiving {msg_type}, which is not a valid subclass of {basetype}"
        super().__init__(msg)


class UnregisteredMessageError(AnyWiseError):
    def __init__(self, msg: Any):
        super().__init__(f"Handler for message {msg} is not found")


class DunglingGuardError(AnyWiseError):
    def __init__(self, guard: IGuard):
        super().__init__(f"Dangling guard {guard}, most likely a bug")
