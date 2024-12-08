from anywise import AnyWise
from tests.conftest import CreateUser, RemoveUser, UpdateUser, UserCreated


def test_send_to_method(anywise: AnyWise):
    cmd = CreateUser("1", "user")
    res = anywise.send(cmd)
    assert res == "hello"

    rm_cmd = RemoveUser("1", "user")
    res = anywise.send(rm_cmd)
    assert res == "goodbye"


def test_send_to_function(anywise: AnyWise):
    cmd = UpdateUser("1", "user", "new")
    res = anywise.send(cmd)
    assert res == "new"


def test_event_handler(anywise: AnyWise):
    event = UserCreated("new_name")
    anywise.publish(event)
