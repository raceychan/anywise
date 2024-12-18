class UserCommand:
    pass


class CreateUser(UserCommand):
    pass


class UpdateUser(UserCommand):
    pass


class CreateUserSub(CreateUser):
    pass


class UpdateUserSub(UpdateUser):
    pass


type CommandGraph = dict[type, list[CommandGraph]]


class GraphBuilder:
    def __init__(self):
        self.graph: CommandGraph = {}

    def build_graph(self, command: type) -> CommandGraph:
        """Recursively build a graph of command classes and their subclasses."""
        subgraph: CommandGraph = {command: []}

        # Get all direct subclasses
        subclasses = self._get_subclasses(command)

        # For each subclass, build its subgraph and add to parent's children
        for subclass in subclasses:
            subclass_graph = self.build_graph(subclass)
            subgraph[command].append(subclass_graph)

        return subgraph

    def _get_subclasses(self, class_type: type) -> list[type]:
        """Get the direct subclasses of a given class."""
        return [cls for cls in class_type.__subclasses__()]


# def test_graph():
#     builder = GraphBuilder()
#     graph = builder.build_graph(UserCommand)

#     from pprint import pprint

#     pprint(graph)
