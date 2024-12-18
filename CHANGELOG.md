# ChangeLog

## Versions

### version 0.1.1

- contexted handler
- command guard

## version 0.1.2

replace GuardRegistry, ListenerRegistry, HandlerRegistry with a new `MessageRegistry`
reduce boilerplace code, make api easier to work with

now will build guards before send, now the order of anywise.include(guard_registry) does not matter

### version 1.0.0

- create a cli stub generator for anywise.send, something like
(similar to pyright createstub, or mypy stubgen)

```bash
# in project root
anywise stub-gen .
```

This should scan functions decorated with

```py
@command_handler
async def create_user(cmd: CreateUser) -> str:
    ...
```

then generate project_folder/typings/anywise.pyi

```py
# anywise.pyi
from typing import overload
from project.commands import CreateUser

class Anywise:
    @overload
    async def send(self, message: CreateUser) -> str:
        ...

    @overload
    async def send(self, message: ListTodos) -> dict[str, list[Any]]:
        ...
```

then config typecheker in pyproject.toml

#### pyright

pyproject.toml
[tool.pyright]
typeCheckingMode = "strict"
extraPaths = ["path/to/typings"]

`stubPath [path, optional]`
Path to a directory that contains custom type stubs. Each package's type stub file(s) are expected to be in its own subdirectory. The default value of this setting is "./typings". (typingsPath is now deprecated)

Configure mypy:

`MYPYPATH`

If you have created your own stubs or placed them in a non-standard location,
use the MYPYPATH environment variable to tell mypy where to find them.

bugs

1. dependency graph look up scope, but not found
2. dependency graph merge lost information about factory
