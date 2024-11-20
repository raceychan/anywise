import types
import typing as ty
from uuid import uuid4


class AnyWised(ty.Protocol):
    __anywised__: bool


def anywise(t: types.ModuleType | ty.Callable | type) -> ty.TypeGuard[AnyWised]:
    setattr(t, "__anywised__", True)
    return t

@ty.runtime_checkable
class ICommand(ty.Protocol): 
    # message id, event id
    ...


class IQuery(ty.Protocol): ...


class IEvent(ty.Protocol): ...


type IMessage = ICommand | IQuery | IEvent



class IRequest(ty.Protocol): ...


class IReturn(ty.Protocol): ...


class IHandler(ty.Protocol):
    ...