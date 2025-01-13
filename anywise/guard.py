from abc import ABC
from typing import Any

from .errors import DunglingGuardError
from .Interface import GuardFunc, IContext, PostHandle

"""
class AuthContext(TypedDict):
    token: str
    user: User

@guard(UserCommand)
class AuthService:
    def validate_user(context: AuthContext, command: UserCommand):
        user = self._get_user(context.token.sub)
        if user.user_id != command.user_id:
            raise ValidationError
        context["user"] = user

async def login(login_form):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer"

class AuthenticatedCommand:
    token: st

def validate_token(command: AuthenticatedCommand) -> AccessToken:
    try:
        token_dict = decrypt_jwt(command.token)
        return AccessToken.model_validate(token_dict)
    except (JWTError, ValidationError) as e:
        raise InvalidCredentialError(
            "Your access token is invalid, check for expiry"
        ) from 

async def get_current_user(aut_repo: AuthRepo, jwt_token: str) -> User:
    token = validate_token(jwt_token)
    user_id = token.sub
    user = await self._auth_repo.get(user_id)
    if not user:
        raise UserNotFoundError(user_id=user_id)
    return user
"""


class BaseGuard(ABC):
    """
    An abstract class for advanced user-defined guard.

    Example
    ---

    ```py
    from typing import Any, MutableMapping
    from loguru import Logger

    type Context = MutableMapping[str, Any]


    class LogginGuard(BaseGuard):
        _next_guard: GuardFunc

        def __init__(self, next_guard: GuardFunc | None = None, *, logger: Any):
            super().__init__(next_guard)
            self._logger = logger

        async def __call__(self, message: Any, context: Context):
            if (request_id := context.get("request_id")) is None:
                context["request_id"] = request_id = str(uuid4())

            with logger.contextualize(request_id=request_id):
                try:
                    response = await self._next_guard(message, context)
                except Exception as exc:
                    logger.error(exc)
                else:
                    logger.success(f"request: {request_id}, got response `{response}`")
                    return response
    ```
    """

    _next_guard: GuardFunc | None

    def __init__(self, next_guard: GuardFunc | None = None):
        self._next_guard = next_guard

    @property
    def next_guard(self) -> GuardFunc | None:
        return self._next_guard

    def __repr__(self):
        base = f"{self.__class__.__name__}("
        if self._next_guard:
            base += f"next_guard={self._next_guard}"
        base += ")"
        return base

    def chain_next(self, next_guard: GuardFunc, /) -> None:
        self._next_guard = next_guard

    async def __call__(self, command: Any, context: IContext) -> Any:
        """
        subclass of `BaseGuard` should override __call__ similar to following:

        ```py
        async def __call__(self, message: Any, context: IContext):
            # write your pre-handle logic
            response = await super().__call__(message, context)
            # write your post-handle logic
            return response
        ```
        """
        if not self._next_guard:
            raise DunglingGuardError(self)
        return await self._next_guard(command, context)


class Guard(BaseGuard):
    def __init__(
        self,
        next_guard: GuardFunc | None = None,
        /,
        *,
        pre_handle: GuardFunc | None = None,
        post_handle: PostHandle[Any] | None = None,
    ):
        super().__init__(next_guard)
        self.pre_handle = pre_handle
        self.post_handle = post_handle

    async def __call__(self, command: Any, context: IContext) -> Any:
        if self.pre_handle:
            await self.pre_handle(command, context)

        if not self._next_guard:
            raise DunglingGuardError(self)

        response = await self._next_guard(command, context)
        if self.post_handle:
            return await self.post_handle(command, context, response)
        return response
