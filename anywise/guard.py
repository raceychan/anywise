from typing import Any

from ._itypes import GuardFunc, PostHandle

"""
reference:
https://www.starlette.io/middleware/#pure-asgi-middleware
"""


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


class Guard:
    def __init__(
        self,
        guard: GuardFunc | None = None,
        /,
        *,
        pre_handle: GuardFunc | None = None,
        post_handle: PostHandle | None = None,
    ):
        self.guard = guard
        self.pre_handle = pre_handle
        self.post_handle = post_handle

    def __repr__(self):
        base = f"Guard("
        if self.pre_handle:
            base += f"pre_handle={self.pre_handle}"
        if self.post_handle:
            base += f"post_handle={self.post_handle}"
        return base

    async def __call__(self, message: Any, context: dict[str, Any]) -> Any:
        # we should accept handler here so we can add decorator to it
        if self.pre_handle:
            await self.pre_handle(message, context)

        if self.guard:
            response = await self.guard(message, context)
            if self.post_handle:
                return await self.post_handle(message, context, response)
            return response

    def chain_next(self, guard: GuardFunc) -> None:
        self.guard = guard

    def bind(self, command: type | list[type]) -> None:
        """
        bind commands to current guard
        """
