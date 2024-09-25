"""The optimizer tries to constant fold expressions and modify the AST
in place so that it should be faster to evaluate.

Because the AST does not contain all the scoping information and the
compiler has to find that out, we cannot do all the optimizations we
want. For example, loop unrolling doesn't work because unrolled loops
would have a different scope. The solution would be a second syntax tree
that stored the scoping rules.
"""
import typing as t
from . import nodes
from .visitor import NodeTransformer
if t.TYPE_CHECKING:
    from .environment import Environment


def optimize(node: nodes.Node, environment: 'Environment') ->nodes.Node:
    """The context hint can be used to perform an static optimization
    based on the context given."""
    optimizer = Optimizer(environment)
    return optimizer.visit(node)


class Optimizer(NodeTransformer):

    def __init__(self, environment: 't.Optional[Environment]') ->None:
        self.environment = environment

    def visit_Const(self, node: nodes.Const) ->nodes.Node:
        """Optimize constant nodes."""
        return node

    def visit_List(self, node: nodes.List) ->nodes.Node:
        """Optimize list nodes."""
        node.items = [self.visit(item) for item in node.items]
        return node

    def visit_Dict(self, node: nodes.Dict) ->nodes.Node:
        """Optimize dict nodes."""
        node.items = [(self.visit(key), self.visit(value)) for key, value in node.items]
        return node

    def visit_Getitem(self, node: nodes.Getitem) ->nodes.Node:
        """Optimize getitem nodes."""
        node.node = self.visit(node.node)
        node.arg = self.visit(node.arg)
        return node

    def visit_Getattr(self, node: nodes.Getattr) ->nodes.Node:
        """Optimize getattr nodes."""
        node.node = self.visit(node.node)
        return node

    def visit_Call(self, node: nodes.Call) ->nodes.Node:
        """Optimize call nodes."""
        node.node = self.visit(node.node)
        node.args = [self.visit(arg) for arg in node.args]
        node.kwargs = [(key, self.visit(value)) for key, value in node.kwargs]
        return node

    def visit_Filter(self, node: nodes.Filter) ->nodes.Node:
        """Optimize filter nodes."""
        node.node = self.visit(node.node)
        node.args = [self.visit(arg) for arg in node.args]
        node.kwargs = [(key, self.visit(value)) for key, value in node.kwargs]
        return node

    def visit_Test(self, node: nodes.Test) ->nodes.Node:
        """Optimize test nodes."""
        node.node = self.visit(node.node)
        node.args = [self.visit(arg) for arg in node.args]
        node.kwargs = [(key, self.visit(value)) for key, value in node.kwargs]
        return node

    def visit_CondExpr(self, node: nodes.CondExpr) ->nodes.Node:
        """Optimize conditional expression nodes."""
        node.test = self.visit(node.test)
        node.expr1 = self.visit(node.expr1)
        node.expr2 = self.visit(node.expr2)
        return node

    def generic_visit(self, node: nodes.Node) ->nodes.Node:
        """Visit a node."""
        return super().generic_visit(node)
