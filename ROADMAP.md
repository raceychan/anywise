# ROADMAP

## Versions

### version 0.1.x

- basic usage and core functionality, command, event handlers, command guards, etc.
- docs
- tutorials

### version 0.2.x

- basic typing support
- web framework integration

## version 0.3.x

introduce the concept of "source"
adding more source

## version 0.4.x

introduce the concept of "sink"

event sink

## version 0.5.x

improve compatibility

## version 0.6.x

remote handler

## version 1.0.x

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

### config typecheker in pyproject.toml

#### Config pyright

in your project root, create a `pyproject.toml` file

```toml
[tool.pyright]
typeCheckingMode = "strict"
extraPaths = ["path/to/typings"]
```

#### Config mypy

`stubPath [path, optional]`
Path to a directory that contains custom type stubs. Each package's type stub file(s) are expected to be in its own subdirectory. The default value of this setting is "./typings". (typingsPath is now deprecated)

Configure mypy:

`MYPYPATH`

If you have created your own stubs or placed them in a non-standard location,
use the MYPYPATH environment variable to tell mypy where to find them.

