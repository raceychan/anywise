type CommandGraph = dict[type, list[CommandGraph]]


class GraphBuilder:
    def __init__(self):
        self.graph: CommandGraph = {}

    def build_graph(self, command: type) -> CommandGraph:
        """Recursively build a graph of command classes and their subclasses."""

        # TODO: currently only work top to bottom, e.g.: build_graph(UserCommand)
        # make it work bottom to top as well, e.g.: build_graph(CreateUserSub)

        subgraph: CommandGraph = {command: []}

        # Get all direct subclasses
        subclasses = [cls for cls in command.__subclasses__()]

        # For each subclass, build its subgraph and add to parent's children
        for subclass in subclasses:
            subclass_graph = self.build_graph(subclass)
            subgraph[command].append(subclass_graph)

        return subgraph
