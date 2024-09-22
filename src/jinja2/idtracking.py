import typing as t
from . import nodes
from .visitor import NodeVisitor
VAR_LOAD_PARAMETER = 'param'
VAR_LOAD_RESOLVE = 'resolve'
VAR_LOAD_ALIAS = 'alias'
VAR_LOAD_UNDEFINED = 'undefined'


class Symbols:

    def __init__(self, parent: t.Optional['Symbols']=None, level: t.
        Optional[int]=None) ->None:
        if level is None:
            if parent is None:
                level = 0
            else:
                level = parent.level + 1
        self.level: int = level
        self.parent = parent
        self.refs: t.Dict[str, str] = {}
        self.loads: t.Dict[str, t.Any] = {}
        self.stores: t.Set[str] = set()


class RootVisitor(NodeVisitor):

    def __init__(self, symbols: 'Symbols') ->None:
        self.sym_visitor = FrameSymbolVisitor(symbols)
    visit_Template = _simple_visit
    visit_Block = _simple_visit
    visit_Macro = _simple_visit
    visit_FilterBlock = _simple_visit
    visit_Scope = _simple_visit
    visit_If = _simple_visit
    visit_ScopedEvalContextModifier = _simple_visit


class FrameSymbolVisitor(NodeVisitor):
    """A visitor for `Frame.inspect`."""

    def __init__(self, symbols: 'Symbols') ->None:
        self.symbols = symbols

    def visit_Name(self, node: nodes.Name, store_as_param: bool=False, **
        kwargs: t.Any) ->None:
        """All assignments to names go through this function."""
        pass

    def visit_Assign(self, node: nodes.Assign, **kwargs: t.Any) ->None:
        """Visit assignments in the correct order."""
        pass

    def visit_For(self, node: nodes.For, **kwargs: t.Any) ->None:
        """Visiting stops at for blocks.  However the block sequence
        is visited as part of the outer scope.
        """
        pass

    def visit_AssignBlock(self, node: nodes.AssignBlock, **kwargs: t.Any
        ) ->None:
        """Stop visiting at block assigns."""
        pass

    def visit_Scope(self, node: nodes.Scope, **kwargs: t.Any) ->None:
        """Stop visiting at scopes."""
        pass

    def visit_Block(self, node: nodes.Block, **kwargs: t.Any) ->None:
        """Stop visiting at blocks."""
        pass

    def visit_OverlayScope(self, node: nodes.OverlayScope, **kwargs: t.Any
        ) ->None:
        """Do not visit into overlay scopes."""
        pass
