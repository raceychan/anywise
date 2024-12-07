import typing as ty

"""
provide a mechanism that

1. execute before the handler, return nothing
2. wrap the handler, works like a decorator
"""

type State = dict[str, ty.Any]
type Message = ty.Any
type Handler = ty.Callable[[Message], ty.Any]


type MessageGuard = ty.Callable[[State, Message], State]

"""
State is a mutable object that carry state
guard can use it to store side-effects of functions
"""


class Guard[MessageType]:
    def __init__(self, guard: MessageGuard): ...

    def __call__(self, message: MessageType): ...


# this acts like a decorator
class Interceptor[MessageType]:
    def __init__(self, message_type: MessageType):
        self.message_type = message_type

    def __call__[
        **P, R
    ](self, next: ty.Callable[P, R], *args: P.args, **kwargs: P.kwargs,):
        resp = next(*args, **kwargs)


# premier = compose(logging, caching, timeout, retry)

# can we add guard as well?
# product_handler.add_interceptors(
#   [logging, caching, timeout]
# )

# async def dispatch(self, message: MessageType, call_next: HandlerFunction):
# response = await call_next(request)


"""

class AuthService:
    def validate_user(self):
        ...


user_handler = mark(UserCommand)

@user_handler
class UserService:

    @user_handler.guard(AuthService.validate_user)
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
