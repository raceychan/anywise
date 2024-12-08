# ChangeLog

## Versions

### version 0.2.0

- create a cli stub generator for anywise.send, something like

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

would result in

```py
# anywise.pyi
from typing import overload
from project.commands import CreateUser

class AnyWise[MessageType]:
    @overload
    def send(self, message: CreateUser) -> str:
        ...
```

then config typecheker

Configure mypy:

`MYPYPATH`

If you have created your own stubs or placed them in a non-standard location,
use the MYPYPATH environment variable to tell mypy where to find them.

Configure pyright:

`stubPath [path, optional]`
Path to a directory that contains custom type stubs. Each package's type stub file(s) are expected to be in its own subdirectory. The default value of this setting is "./typings". (typingsPath is now deprecated)
