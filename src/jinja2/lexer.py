"""Implements a Jinja / Python combination lexer. The ``Lexer`` class
is used to do some preprocessing. It filters out invalid operators like
the bitshift operators we don't allow in templates. It separates
template code and python code in expressions.
"""
import re
import typing as t
from ast import literal_eval
from collections import deque
from sys import intern
from ._identifier import pattern as name_re
from .exceptions import TemplateSyntaxError
from .utils import LRUCache
if t.TYPE_CHECKING:
    import typing_extensions as te
    from .environment import Environment
_lexer_cache: t.MutableMapping[t.Tuple, 'Lexer'] = LRUCache(50)
whitespace_re = re.compile('\\s+')
newline_re = re.compile('(\\r\\n|\\r|\\n)')
string_re = re.compile(
    '(\'([^\'\\\\]*(?:\\\\.[^\'\\\\]*)*)\'|"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)")',
    re.S)
integer_re = re.compile(
    """
    (
        0b(_?[0-1])+ # binary
    |
        0o(_?[0-7])+ # octal
    |
        0x(_?[\\da-f])+ # hex
    |
        [1-9](_?\\d)* # decimal
    |
        0(_?0)* # decimal zero
    )
    """
    , re.IGNORECASE | re.VERBOSE)
float_re = re.compile(
    """
    (?<!\\.)  # doesn't start with a .
    (\\d+_)*\\d+  # digits, possibly _ separated
    (
        (\\.(\\d+_)*\\d+)?  # optional fractional part
        e[+\\-]?(\\d+_)*\\d+  # exponent part
    |
        \\.(\\d+_)*\\d+  # required fractional part
    )
    """
    , re.IGNORECASE | re.VERBOSE)
TOKEN_ADD = intern('add')
TOKEN_ASSIGN = intern('assign')
TOKEN_COLON = intern('colon')
TOKEN_COMMA = intern('comma')
TOKEN_DIV = intern('div')
TOKEN_DOT = intern('dot')
TOKEN_EQ = intern('eq')
TOKEN_FLOORDIV = intern('floordiv')
TOKEN_GT = intern('gt')
TOKEN_GTEQ = intern('gteq')
TOKEN_LBRACE = intern('lbrace')
TOKEN_LBRACKET = intern('lbracket')
TOKEN_LPAREN = intern('lparen')
TOKEN_LT = intern('lt')
TOKEN_LTEQ = intern('lteq')
TOKEN_MOD = intern('mod')
TOKEN_MUL = intern('mul')
TOKEN_NE = intern('ne')
TOKEN_PIPE = intern('pipe')
TOKEN_POW = intern('pow')
TOKEN_RBRACE = intern('rbrace')
TOKEN_RBRACKET = intern('rbracket')
TOKEN_RPAREN = intern('rparen')
TOKEN_SEMICOLON = intern('semicolon')
TOKEN_SUB = intern('sub')
TOKEN_TILDE = intern('tilde')
TOKEN_WHITESPACE = intern('whitespace')
TOKEN_FLOAT = intern('float')
TOKEN_INTEGER = intern('integer')
TOKEN_NAME = intern('name')
TOKEN_STRING = intern('string')
TOKEN_OPERATOR = intern('operator')
TOKEN_BLOCK_BEGIN = intern('block_begin')
TOKEN_BLOCK_END = intern('block_end')
TOKEN_VARIABLE_BEGIN = intern('variable_begin')
TOKEN_VARIABLE_END = intern('variable_end')
TOKEN_RAW_BEGIN = intern('raw_begin')
TOKEN_RAW_END = intern('raw_end')
TOKEN_COMMENT_BEGIN = intern('comment_begin')
TOKEN_COMMENT_END = intern('comment_end')
TOKEN_COMMENT = intern('comment')
TOKEN_LINESTATEMENT_BEGIN = intern('linestatement_begin')
TOKEN_LINESTATEMENT_END = intern('linestatement_end')
TOKEN_LINECOMMENT_BEGIN = intern('linecomment_begin')
TOKEN_LINECOMMENT_END = intern('linecomment_end')
TOKEN_LINECOMMENT = intern('linecomment')
TOKEN_DATA = intern('data')
TOKEN_INITIAL = intern('initial')
TOKEN_EOF = intern('eof')
operators = {'+': TOKEN_ADD, '-': TOKEN_SUB, '/': TOKEN_DIV, '//':
    TOKEN_FLOORDIV, '*': TOKEN_MUL, '%': TOKEN_MOD, '**': TOKEN_POW, '~':
    TOKEN_TILDE, '[': TOKEN_LBRACKET, ']': TOKEN_RBRACKET, '(':
    TOKEN_LPAREN, ')': TOKEN_RPAREN, '{': TOKEN_LBRACE, '}': TOKEN_RBRACE,
    '==': TOKEN_EQ, '!=': TOKEN_NE, '>': TOKEN_GT, '>=': TOKEN_GTEQ, '<':
    TOKEN_LT, '<=': TOKEN_LTEQ, '=': TOKEN_ASSIGN, '.': TOKEN_DOT, ':':
    TOKEN_COLON, '|': TOKEN_PIPE, ',': TOKEN_COMMA, ';': TOKEN_SEMICOLON}
reverse_operators = {v: k for k, v in operators.items()}
assert len(operators) == len(reverse_operators), 'operators dropped'
operator_re = re.compile(
    f"({'|'.join(re.escape(x) for x in sorted(operators, key=lambda x: -len(x)))})"
    )
ignored_tokens = frozenset([TOKEN_COMMENT_BEGIN, TOKEN_COMMENT,
    TOKEN_COMMENT_END, TOKEN_WHITESPACE, TOKEN_LINECOMMENT_BEGIN,
    TOKEN_LINECOMMENT_END, TOKEN_LINECOMMENT])
ignore_if_empty = frozenset([TOKEN_WHITESPACE, TOKEN_DATA, TOKEN_COMMENT,
    TOKEN_LINECOMMENT])


def describe_token(token: 'Token') ->str:
    """Returns a description of the token."""
    pass


def describe_token_expr(expr: str) ->str:
    """Like `describe_token` but for token expressions."""
    pass


def count_newlines(value: str) ->int:
    """Count the number of newline characters in the string.  This is
    useful for extensions that filter a stream.
    """
    pass


def compile_rules(environment: 'Environment') ->t.List[t.Tuple[str, str]]:
    """Compiles all the rules from the environment into a list of rules."""
    pass


class Failure:
    """Class that raises a `TemplateSyntaxError` if called.
    Used by the `Lexer` to specify known errors.
    """

    def __init__(self, message: str, cls: t.Type[TemplateSyntaxError]=
        TemplateSyntaxError) ->None:
        self.message = message
        self.error_class = cls

    def __call__(self, lineno: int, filename: str) ->'te.NoReturn':
        raise self.error_class(self.message, lineno, filename)


class Token(t.NamedTuple):
    lineno: int
    type: str
    value: str

    def __str__(self) ->str:
        return describe_token(self)

    def test(self, expr: str) ->bool:
        """Test a token against a token expression.  This can either be a
        token type or ``'token_type:token_value'``.  This can only test
        against string values and types.
        """
        pass

    def test_any(self, *iterable: str) ->bool:
        """Test against multiple token expressions."""
        pass


class TokenStreamIterator:
    """The iterator for tokenstreams.  Iterate over the stream
    until the eof token is reached.
    """

    def __init__(self, stream: 'TokenStream') ->None:
        self.stream = stream

    def __iter__(self) ->'TokenStreamIterator':
        return self

    def __next__(self) ->Token:
        token = self.stream.current
        if token.type is TOKEN_EOF:
            self.stream.close()
            raise StopIteration
        next(self.stream)
        return token


class TokenStream:
    """A token stream is an iterable that yields :class:`Token`\\s.  The
    parser however does not iterate over it but calls :meth:`next` to go
    one token ahead.  The current active token is stored as :attr:`current`.
    """

    def __init__(self, generator: t.Iterable[Token], name: t.Optional[str],
        filename: t.Optional[str]):
        self._iter = iter(generator)
        self._pushed: 'te.Deque[Token]' = deque()
        self.name = name
        self.filename = filename
        self.closed = False
        self.current = Token(1, TOKEN_INITIAL, '')
        next(self)

    def __iter__(self) ->TokenStreamIterator:
        return TokenStreamIterator(self)

    def __bool__(self) ->bool:
        return bool(self._pushed) or self.current.type is not TOKEN_EOF

    @property
    def eos(self) ->bool:
        """Are we at the end of the stream?"""
        pass

    def push(self, token: Token) ->None:
        """Push a token back to the stream."""
        pass

    def look(self) ->Token:
        """Look at the next token."""
        pass

    def skip(self, n: int=1) ->None:
        """Got n tokens ahead."""
        pass

    def next_if(self, expr: str) ->t.Optional[Token]:
        """Perform the token test and return the token if it matched.
        Otherwise the return value is `None`.
        """
        pass

    def skip_if(self, expr: str) ->bool:
        """Like :meth:`next_if` but only returns `True` or `False`."""
        pass

    def __next__(self) ->Token:
        """Go one token ahead and return the old one.

        Use the built-in :func:`next` instead of calling this directly.
        """
        rv = self.current
        if self._pushed:
            self.current = self._pushed.popleft()
        elif self.current.type is not TOKEN_EOF:
            try:
                self.current = next(self._iter)
            except StopIteration:
                self.close()
        return rv

    def close(self) ->None:
        """Close the stream."""
        pass

    def expect(self, expr: str) ->Token:
        """Expect a given token type and return it.  This accepts the same
        argument as :meth:`jinja2.lexer.Token.test`.
        """
        pass


def get_lexer(environment: 'Environment') ->'Lexer':
    """Return a lexer which is probably cached."""
    pass


class OptionalLStrip(tuple):
    """A special tuple for marking a point in the state that can have
    lstrip applied.
    """
    __slots__ = ()

    def __new__(cls, *members, **kwargs):
        return super().__new__(cls, members)


class _Rule(t.NamedTuple):
    pattern: t.Pattern[str]
    tokens: t.Union[str, t.Tuple[str, ...], t.Tuple[Failure]]
    command: t.Optional[str]


class Lexer:
    """Class that implements a lexer for a given environment. Automatically
    created by the environment class, usually you don't have to do that.

    Note that the lexer is not automatically bound to an environment.
    Multiple environments can share the same lexer.
    """

    def __init__(self, environment: 'Environment') ->None:
        e = re.escape

        def c(x: str) ->t.Pattern[str]:
            return re.compile(x, re.M | re.S)
        tag_rules: t.List[_Rule] = [_Rule(whitespace_re, TOKEN_WHITESPACE,
            None), _Rule(float_re, TOKEN_FLOAT, None), _Rule(integer_re,
            TOKEN_INTEGER, None), _Rule(name_re, TOKEN_NAME, None), _Rule(
            string_re, TOKEN_STRING, None), _Rule(operator_re,
            TOKEN_OPERATOR, None)]
        root_tag_rules = compile_rules(environment)
        block_start_re = e(environment.block_start_string)
        block_end_re = e(environment.block_end_string)
        comment_end_re = e(environment.comment_end_string)
        variable_end_re = e(environment.variable_end_string)
        block_suffix_re = '\\n?' if environment.trim_blocks else ''
        self.lstrip_blocks = environment.lstrip_blocks
        self.newline_sequence = environment.newline_sequence
        self.keep_trailing_newline = environment.keep_trailing_newline
        root_raw_re = (
            f'(?P<raw_begin>{block_start_re}(\\-|\\+|)\\s*raw\\s*(?:\\-{block_end_re}\\s*|{block_end_re}))'
            )
        root_parts_re = '|'.join([root_raw_re] + [f'(?P<{n}>{r}(\\-|\\+|))' for
            n, r in root_tag_rules])
        self.rules: t.Dict[str, t.List[_Rule]] = {'root': [_Rule(c(
            f'(.*?)(?:{root_parts_re})'), OptionalLStrip(TOKEN_DATA,
            '#bygroup'), '#bygroup'), _Rule(c('.+'), TOKEN_DATA, None)],
            TOKEN_COMMENT_BEGIN: [_Rule(c(
            f'(.*?)((?:\\+{comment_end_re}|\\-{comment_end_re}\\s*|{comment_end_re}{block_suffix_re}))'
            ), (TOKEN_COMMENT, TOKEN_COMMENT_END), '#pop'), _Rule(c('(.)'),
            (Failure('Missing end of comment tag'),), None)],
            TOKEN_BLOCK_BEGIN: [_Rule(c(
            f'(?:\\+{block_end_re}|\\-{block_end_re}\\s*|{block_end_re}{block_suffix_re})'
            ), TOKEN_BLOCK_END, '#pop')] + tag_rules, TOKEN_VARIABLE_BEGIN:
            [_Rule(c(f'\\-{variable_end_re}\\s*|{variable_end_re}'),
            TOKEN_VARIABLE_END, '#pop')] + tag_rules, TOKEN_RAW_BEGIN: [
            _Rule(c(
            f'(.*?)((?:{block_start_re}(\\-|\\+|))\\s*endraw\\s*(?:\\+{block_end_re}|\\-{block_end_re}\\s*|{block_end_re}{block_suffix_re}))'
            ), OptionalLStrip(TOKEN_DATA, TOKEN_RAW_END), '#pop'), _Rule(c(
            '(.)'), (Failure('Missing end of raw directive'),), None)],
            TOKEN_LINESTATEMENT_BEGIN: [_Rule(c('\\s*(\\n|$)'),
            TOKEN_LINESTATEMENT_END, '#pop')] + tag_rules,
            TOKEN_LINECOMMENT_BEGIN: [_Rule(c('(.*?)()(?=\\n|$)'), (
            TOKEN_LINECOMMENT, TOKEN_LINECOMMENT_END), '#pop')]}

    def _normalize_newlines(self, value: str) ->str:
        """Replace all newlines with the configured sequence in strings
        and template data.
        """
        pass

    def tokenize(self, source: str, name: t.Optional[str]=None, filename: t
        .Optional[str]=None, state: t.Optional[str]=None) ->TokenStream:
        """Calls tokeniter + tokenize and wraps it in a token stream."""
        pass

    def wrap(self, stream: t.Iterable[t.Tuple[int, str, str]], name: t.
        Optional[str]=None, filename: t.Optional[str]=None) ->t.Iterator[Token
        ]:
        """This is called with the stream as returned by `tokenize` and wraps
        every token in a :class:`Token` and converts the value.
        """
        pass

    def tokeniter(self, source: str, name: t.Optional[str], filename: t.
        Optional[str]=None, state: t.Optional[str]=None) ->t.Iterator[t.
        Tuple[int, str, str]]:
        """This method tokenizes the text and returns the tokens in a
        generator. Use this method if you just want to tokenize a template.

        .. versionchanged:: 3.0
            Only ``\\n``, ``\\r\\n`` and ``\\r`` are treated as line
            breaks.
        """
        pass
