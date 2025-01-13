

class People:

    def __init__(self, name: str):
        self.__name = name

    def get_name(self):
        return self.__name


class Student(People):

    def hello(self):
        print(f"hello, i am {self.get_name()}")


def test():
    s = Student("a")
    print(s.get_name())

    s.hello()
