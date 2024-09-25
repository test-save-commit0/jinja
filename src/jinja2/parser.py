"""Parse tokens from the lexer into nodes for the compiler."""
import typing
import typing as t
from . import nodes
from .exceptions import TemplateAssertionError
from .exceptions import TemplateSyntaxError
from .lexer import describe_token
from .lexer import describe_token_expr
if t.TYPE_CHECKING:
    import typing_extensions as te
    from .environment import Environment
_ImportInclude = t.TypeVar('_ImportInclude', nodes.Import, nodes.Include)
_MacroCall = t.TypeVar('_MacroCall', nodes.Macro, nodes.CallBlock)
_statement_keywords = frozenset(['for', 'if', 'block', 'extends', 'print',
    'macro', 'include', 'from', 'import', 'set', 'with', 'autoescape'])
_compare_operators = frozenset(['eq', 'ne', 'lt', 'lteq', 'gt', 'gteq'])
_math_nodes: t.Dict[str, t.Type[nodes.Expr]] = {'add': nodes.Add, 'sub':
    nodes.Sub, 'mul': nodes.Mul, 'div': nodes.Div, 'floordiv': nodes.
    FloorDiv, 'mod': nodes.Mod}


class Parser:
    """This is the central parsing class Jinja uses.  It's passed to
    extensions and can be used to parse expressions or statements.
    """

    def __init__(self, environment: 'Environment', source: str, name: t.
        Optional[str]=None, filename: t.Optional[str]=None, state: t.
        Optional[str]=None) ->None:
        self.environment = environment
        self.stream = environment._tokenize(source, name, filename, state)
        self.name = name
        self.filename = filename
        self.closed = False
        self.extensions: t.Dict[str, t.Callable[['Parser'], t.Union[nodes.
            Node, t.List[nodes.Node]]]] = {}
        for extension in environment.iter_extensions():
            for tag in extension.tags:
                self.extensions[tag] = extension.parse
        self._last_identifier = 0
        self._tag_stack: t.List[str] = []
        self._end_token_stack: t.List[t.Tuple[str, ...]] = []

    def fail(self, msg: str, lineno: t.Optional[int]=None, exc: t.Type[
        TemplateSyntaxError]=TemplateSyntaxError) ->'te.NoReturn':
        """Convenience method that raises `exc` with the message, passed
        line number or last line number as well as the current name and
        filename.
        """
        if lineno is None:
            lineno = self.stream.current.lineno
        raise exc(msg, lineno, self.name, self.filename)

    def fail_unknown_tag(self, name: str, lineno: t.Optional[int]=None
        ) ->'te.NoReturn':
        """Called if the parser encounters an unknown tag.  Tries to fail
        with a human readable error message that could help to identify
        the problem.
        """
        if lineno is None:
            lineno = self.stream.current.lineno
        if name in ('endif', 'endfor', 'endblock', 'endmacro', 'endcall'):
            self.fail(f'Unexpected end of block tag {name!r}', lineno)
        elif name in _statement_keywords:
            self.fail(f'Block tag {name!r} expected', lineno)
        self.fail(f'Unknown tag {name!r}', lineno)

    def fail_eof(self, end_tokens: t.Optional[t.Tuple[str, ...]]=None,
        lineno: t.Optional[int]=None) ->'te.NoReturn':
        """Like fail_unknown_tag but for end of template situations."""
        if end_tokens is not None:
            expected = ' or '.join(repr(x) for x in end_tokens)
            msg = f'Unexpected end of template. Expected {expected}.'
        else:
            msg = 'Unexpected end of template.'
        self.fail(msg, lineno)

    def is_tuple_end(self, extra_end_rules: t.Optional[t.Tuple[str, ...]]=None
        ) ->bool:
        """Are we at the end of a tuple?"""
        if self.stream.current.type in ('variable_end', 'block_end', 'rparen'):
            return True
        if extra_end_rules is not None:
            return self.stream.current.test_any(extra_end_rules)
        return False

    def free_identifier(self, lineno: t.Optional[int]=None
        ) ->nodes.InternalName:
        """Return a new free identifier as :class:`~jinja2.nodes.InternalName`."""
        self._last_identifier += 1
        rv = object.__new__(nodes.InternalName)
        rv.name = f'fi{self._last_identifier}'
        rv.lineno = lineno
        return rv

    def parse_statement(self) ->t.Union[nodes.Node, t.List[nodes.Node]]:
        """Parse a single statement."""
        token = self.stream.current
        if token.type != 'name':
            return self.parse_expression()
        if token.value in _statement_keywords:
            return getattr(self, f'parse_{token.value}')()
        if token.value == 'call':
            return self.parse_call_block()
        if token.value == 'filter':
            return self.parse_filter_block()
        return self.parse_expression()

    def parse_statements(self, end_tokens: t.Tuple[str, ...], drop_needle:
        bool=False) ->t.List[nodes.Node]:
        """Parse multiple statements into a list until one of the end tokens
        is reached.  This is used to parse the body of statements as it also
        parses template data if appropriate.  The parser checks first if the
        current token is a colon and skips it if there is one.  Then it checks
        for the block end and parses until if one of the `end_tokens` is
        reached.  Per default the active token in the stream at the end of
        the call is the matched end token.  If this is not wanted `drop_needle`
        can be set to `True` and the end token is removed.
        """
        result = []
        while 1:
            if self.stream.current.type == 'data':
                result.append(nodes.Output([self.parse_tuple(with_condexpr=True)]))
            elif self.stream.current.type == 'block_begin':
                self.stream.next()
                if self.stream.current.test_any(end_tokens):
                    if drop_needle:
                        self.stream.next()
                    return result
                result.append(self.parse_statement())
            else:
                break
        self.fail_eof(end_tokens)

    def parse_set(self) ->t.Union[nodes.Assign, nodes.AssignBlock]:
        """Parse an assign statement."""
        pass

    def parse_for(self) ->nodes.For:
        """Parse a for loop."""
        pass

    def parse_if(self) ->nodes.If:
        """Parse an if construct."""
        pass

    def parse_assign_target(self, with_tuple: bool=True, name_only: bool=
        False, extra_end_rules: t.Optional[t.Tuple[str, ...]]=None,
        with_namespace: bool=False) ->t.Union[nodes.NSRef, nodes.Name,
        nodes.Tuple]:
        """Parse an assignment target.  As Jinja allows assignments to
        tuples, this function can parse all allowed assignment targets.  Per
        default assignments to tuples are parsed, that can be disable however
        by setting `with_tuple` to `False`.  If only assignments to names are
        wanted `name_only` can be set to `True`.  The `extra_end_rules`
        parameter is forwarded to the tuple parsing function.  If
        `with_namespace` is enabled, a namespace assignment may be parsed.
        """
        pass

    def parse_expression(self, with_condexpr: bool=True) ->nodes.Expr:
        """Parse an expression.  Per default all expressions are parsed, if
        the optional `with_condexpr` parameter is set to `False` conditional
        expressions are not parsed.
        """
        pass

    def parse_tuple(self, simplified: bool=False, with_condexpr: bool=True,
        extra_end_rules: t.Optional[t.Tuple[str, ...]]=None,
        explicit_parentheses: bool=False) ->t.Union[nodes.Tuple, nodes.Expr]:
        """Works like `parse_expression` but if multiple expressions are
        delimited by a comma a :class:`~jinja2.nodes.Tuple` node is created.
        This method could also return a regular expression instead of a tuple
        if no commas where found.

        The default parsing mode is a full tuple.  If `simplified` is `True`
        only names and literals are parsed.  The `no_condexpr` parameter is
        forwarded to :meth:`parse_expression`.

        Because tuples do not require delimiters and may end in a bogus comma
        an extra hint is needed that marks the end of a tuple.  For example
        for loops support tuples between `for` and `in`.  In that case the
        `extra_end_rules` is set to ``['name:in']``.

        `explicit_parentheses` is true if the parsing was triggered by an
        expression in parentheses.  This is used to figure out if an empty
        tuple is a valid expression or not.
        """
        pass

    def parse(self) ->nodes.Template:
        """Parse the whole template into a `Template` node."""
        pass
