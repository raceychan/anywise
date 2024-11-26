from anywise.mark import mark


class UserCommand: ...


class CreateUser(UserCommand): ...


class UserService:

    def __init__(self):
        self.name = "name"

    @mark
    def create_user(self, cmd: CreateUser) -> str:
        return "hello"


def test():
    UserService().create_user(CreateUser())
