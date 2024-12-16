from typing import Annotated

from fastapi import Depends, Request

from ..anywise import Anywise


def get_anywise(r: Request) -> Anywise:
    state = r.scope["state"]
    anywise: Anywise = state["anywise"]
    print(f"at dep {anywise}")
    return anywise


FastWise = Annotated[Anywise, Depends(get_anywise)]
