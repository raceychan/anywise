from typing import Any


class AnyWiseError(Exception): ...


class MessageHandlerNotFoundError(AnyWiseError): ...


class NotSupportedHandlerTypeError(AnyWiseError): ...


class UnregisteredMessageError(AnyWiseError):
    def __init__(self, msg: Any):
        super().__init__(f"Handler for {msg} is not found")
