VERSION = "0.1.0"


from ididi import inject as inject

from ._registry import handler_registry as handler_registry
from ._registry import listener_registry as listener_registry
from .anywise import AnyWise as AnyWise
from .anywise import ConcurrentPublisher as ConcurrentPublisher
