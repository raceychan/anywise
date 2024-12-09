import typing as ty

from anywise.guard import MarkGuard


async def handler_str(name: str, context: dict[str, ty.Any]):
    print(context, "done")
    return "done"


def guard[
    **P, R
](message_type: type, guard_class: ty.Callable[P, R] | None = None,):
    """
    register guard into guard registry
    when included in anywise, match handler by command type
    a guard of base command will be added to all handlers of subcommand, meaning

    guard(UserCommand) will be added to handle of CreateUser, UpdateUser,
    etc.



    user_guard = guard(UserCommand)

    @user_guard
    class AuthService:
        def validate_user(command: UserCommand, context: AuthContext):
            user = self._get_user(context.token.sub)
            if user.user_id != command.user_id:
                raise ValidationError
            context["user"] = user

    @user_guard.pre_handle
    def validate_user(self): ...

    """
    ...


async def test_guard():
    m1 = MarkGuard(MarkGuard(MarkGuard(handler_str)))

    # m1.add_new(m2).add_new(m3)
    res = await m1("name", dict())
    assert res == "done"
