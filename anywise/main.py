import typing as ty
from dataclasses import dataclass
import inspect
import sys
from ._itypes import ICommand

type IHandler = ty.Callable[[ICommand], None]

class AnyWise:
    def __init__(self):
        self._handlers: dict[type[ICommand], IHandler] = {}

    def _register_function(self, func: IHandler) -> None:
        """Register a single function as a handler."""
        if not inspect.isfunction(func):
            return

        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if inspect.isclass(param.annotation) and issubclass(param.annotation, ICommand):
                self._handlers[param.annotation] = func
                break

    def _register_class(self, cls: type) -> None:
        """Register all methods in a class that handle commands."""
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            self._register_function(method)

    def _register_module(self, module) -> None:
        """Register all classes and functions in a module."""
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and not issubclass(obj, ICommand):
                self._register_class(obj)
            elif inspect.isfunction(obj):
                self._register_function(obj)

    def register(self, target: ty.Union[ty.Callable, type, str, object]) -> None:
        """
        Register handlers from various sources:
        - Function/method
        - Class
        - Module (as string or module object)
        """
        if isinstance(target, str):
            # Register by module name
            try:
                module = sys.modules[target]
                self._register_module(module)
            except KeyError:
                raise ValueError(f"Module {target} not found")
            
        elif inspect.ismodule(target):
            # Register a module object
            self._register_module(target)
            
        elif inspect.isclass(target):
            # Register a class
            self._register_class(target)
            
        elif inspect.isfunction(target) or inspect.ismethod(target):
            # Register a function or method
            self._register_function(target)
            
        elif isinstance(target, object):
            # Register an instance's methods
            self._register_class(target.__class__)
        
        else:
            raise ValueError(f"Cannot register {target} of type {type(target)}")

    def send(self, command: ICommand):
        """Send a command to its registered handler."""
        try:
            handler = self._handlers[type(command)]
        except KeyError:
            raise ValueError(f"No handler registered for command type {type(command)}")
        
        return handler(command)

# Example usage:

@dataclass
class SignupUser(ICommand):
    user_name: str = ""
    user_email: str = ""

# Example handler class
class UserHandlers:
    def handle_signup(self, command: SignupUser):
        print(f"Signing up user: {command.user_name} ({command.user_email})")

# Example handler function
def handle_signup(command: SignupUser):
    print(f"Function handling signup: {command.user_name}")

def test():
    anywise = AnyWise()
    
    # Register a function
    anywise.register(handle_signup)
    
    # Register a class
    anywise.register(UserHandlers)
    
    # Register an instance
    handlers = UserHandlers()
    anywise.register(handlers)
    
    # Register current module
    anywise.register(__name__)
    
    # Test sending a command
    command = SignupUser(user_name="John", user_email="john@example.com")
    anywise.send(command)

if __name__ == "__main__":
    test()