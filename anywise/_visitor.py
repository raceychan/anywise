import ast
import inspect
import typing as ty


class ExceptionFinder(ast.NodeVisitor):
    def __init__(self):
        self.exceptions: list[str] = []

    def visit_Raise(self, node: ast.Raise):
        if node.exc:  # If there is an exception being raised
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                # Example: `raise ValueError("...")`
                self.exceptions.append(node.exc.func.id)
            elif isinstance(node.exc, ast.Name):
                # Example: `raise CustomException`
                self.exceptions.append(node.exc.id)
        self.generic_visit(node)


def collect_exceptions[**P, T](func: ty.Callable[P, T]) -> list[Exception]:
    """
    TODO: recursively search for function call,
    diffierentiate customized exception and builtin exception
    only collect customized exception
    """
    source = inspect.getsource(func)
    tree = ast.parse(source)
    finder = ExceptionFinder()
    finder.visit(tree)
    excs: list[Exception] = []
    for e in finder.exceptions:
        if exc := getattr(__builtins__, e, None):
            excs.append(exc)
        else:
            exc = func.__globals__[e]
            excs.append(exc)
    return excs
