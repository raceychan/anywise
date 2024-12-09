from typing import Any, Callable

"""
reference:
https://www.starlette.io/middleware/#pure-asgi-middleware
"""

# type Context = MutableMapping[str, Any]

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
"""

type GuardFunc = Callable[[Any, dict[str, Any]], Any]
type PostHandle = Callable[[Any, dict[str, Any], Any], Any]


class Guard:
    def __init__(
        self,
        nxt: GuardFunc | None = None,
        *,
        pre_handle: GuardFunc | None = None,
        post_handle: PostHandle | None = None,
    ):
        self.nxt = nxt
        self.pre_handle = pre_handle
        self.post_handle = post_handle

    async def __call__(self, message: Any, context: dict[str, Any]) -> Any:
        # we should accept handler here so we can add decorator to it
        if self.pre_handle:
            await self.pre_handle(message, context)

        if self.nxt:
            response = await self.nxt(message, context)
            if self.post_handle:
                return await self.post_handle(message, context, response)
            return response

    def bind(self, command: type | list[type]): ...


class MarkGuard(Guard):
    def __init__(self, nxt: GuardFunc):
        super().__init__(nxt, pre_handle=self.pre_handle)

    def pre_handle(self, message: Any, context: dict[str, Any]) -> Any:
        if not context.get("processed_by"):
            context["processed_by"] = [self]
        else:
            context["processed_by"].append(self)


"""
class AuthService:
    def validate_user(self):
        ...


user_handler = mark(UserCommand)

@user_handler
class UserService:

    async def remove_user(self, cmd: RemoveUser):
        ...

product_handler = mark(ProductCommand)

product_handler.add_guard(AuthService.validate_user)

@producer_handler
class ProductService:
    ...
"""


# async def login(login_form):
#     user = authenticate_user(fake_users_db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(status_code=400, detail="Incorrect username or password")
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user.username, "scopes": form_data.scopes},
#         expires_delta=access_token_expires,
#     )
#     return Token(access_token=access_token, token_type="bearer")


# class AuthenticatedCommand:
#     token: str


# def validate_token(command: AuthenticatedCommand) -> AccessToken:
#     try:
#         token_dict = decrypt_jwt(command.token)
#         return AccessToken.model_validate(token_dict)
#     except (JWTError, ValidationError) as e:
#         raise InvalidCredentialError(
#             "Your access token is invalid, check for expiry"
#         ) from e


# async def get_current_user(aut_repo: AuthRepo, jwt_token: str) -> User:
#     token = validate_token(jwt_token)
#     user_id = token.sub
#     user = await self._auth_repo.get(user_id)
#     if not user:
#         raise UserNotFoundError(user_id=user_id)
#     return user
