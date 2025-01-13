# # from asyncio import TaskGroup
# from contextvars import ContextVar, Token
# from typing import ClassVar

# # from anyio import create_task_group
# from anyio.abc import TaskGroup
# from ididi import AsyncScope


# class Runtime:
#     _task_ctx: ClassVar[ContextVar[TaskGroup]]
#     _scope_ctx: ClassVar[ContextVar[AsyncScope]]

#     _ctx_token_task: Token[TaskGroup]
#     _ctx_token_scope: Token[AsyncScope]

#     # async __aexit__(self): self._task_ctx.reset(self._ctx_token_task)

#     async def add_task(self, task):
#         """
#         scheduling a background task

#         tg = self._task_ctx.get()
#         tg.start_soon(task)

#         """

#     async def gather_tasks(self):
#         """
#         in starlette

#         tasks = BackgroundTasks()
#         tasks.add_task(anywise.gather_tasks)

#         """
#         # tg = self._task_ctx.get()
#         # await tg.__aexit__
#         ...
