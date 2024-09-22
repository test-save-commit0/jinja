"""A sandbox layer that ensures unsafe operations cannot be performed.
Useful when the template itself comes from an untrusted source.
"""
import operator
import types
import typing as t
from collections import abc
from collections import deque
from string import Formatter
from _string import formatter_field_name_split
from markupsafe import EscapeFormatter
from markupsafe import Markup
from .environment import Environment
from .exceptions import SecurityError
from .runtime import Context
from .runtime import Undefined
F = t.TypeVar('F', bound=t.Callable[..., t.Any])
MAX_RANGE = 100000
UNSAFE_FUNCTION_ATTRIBUTES: t.Set[str] = set()
UNSAFE_METHOD_ATTRIBUTES: t.Set[str] = set()
UNSAFE_GENERATOR_ATTRIBUTES = {'gi_frame', 'gi_code'}
UNSAFE_COROUTINE_ATTRIBUTES = {'cr_frame', 'cr_code'}
UNSAFE_ASYNC_GENERATOR_ATTRIBUTES = {'ag_code', 'ag_frame'}
_mutable_spec: t.Tuple[t.Tuple[t.Type[t.Any], t.FrozenSet[str]], ...] = ((
    abc.MutableSet, frozenset(['add', 'clear', 'difference_update',
    'discard', 'pop', 'remove', 'symmetric_difference_update', 'update'])),
    (abc.MutableMapping, frozenset(['clear', 'pop', 'popitem', 'setdefault',
    'update'])), (abc.MutableSequence, frozenset(['append', 'reverse',
    'insert', 'sort', 'extend', 'remove'])), (deque, frozenset(['append',
    'appendleft', 'clear', 'extend', 'extendleft', 'pop', 'popleft',
    'remove', 'rotate'])))


def safe_range(*args: int) ->range:
    """A range that can't generate ranges with a length of more than
    MAX_RANGE items.
    """
    pass


def unsafe(f: F) ->F:
    """Marks a function or method as unsafe.

    .. code-block: python

        @unsafe
        def delete(self):
            pass
    """
    pass


def is_internal_attribute(obj: t.Any, attr: str) ->bool:
    """Test if the attribute given is an internal python attribute.  For
    example this function returns `True` for the `func_code` attribute of
    python objects.  This is useful if the environment method
    :meth:`~SandboxedEnvironment.is_safe_attribute` is overridden.

    >>> from jinja2.sandbox import is_internal_attribute
    >>> is_internal_attribute(str, "mro")
    True
    >>> is_internal_attribute(str, "upper")
    False
    """
    pass


def modifies_known_mutable(obj: t.Any, attr: str) ->bool:
    """This function checks if an attribute on a builtin mutable object
    (list, dict, set or deque) or the corresponding ABCs would modify it
    if called.

    >>> modifies_known_mutable({}, "clear")
    True
    >>> modifies_known_mutable({}, "keys")
    False
    >>> modifies_known_mutable([], "append")
    True
    >>> modifies_known_mutable([], "index")
    False

    If called with an unsupported object, ``False`` is returned.

    >>> modifies_known_mutable("foo", "upper")
    False
    """
    pass


class SandboxedEnvironment(Environment):
    """The sandboxed environment.  It works like the regular environment but
    tells the compiler to generate sandboxed code.  Additionally subclasses of
    this environment may override the methods that tell the runtime what
    attributes or functions are safe to access.

    If the template tries to access insecure code a :exc:`SecurityError` is
    raised.  However also other exceptions may occur during the rendering so
    the caller has to ensure that all exceptions are caught.
    """
    sandboxed = True
    default_binop_table: t.Dict[str, t.Callable[[t.Any, t.Any], t.Any]] = {'+':
        operator.add, '-': operator.sub, '*': operator.mul, '/': operator.
        truediv, '//': operator.floordiv, '**': operator.pow, '%': operator.mod
        }
    default_unop_table: t.Dict[str, t.Callable[[t.Any], t.Any]] = {'+':
        operator.pos, '-': operator.neg}
    intercepted_binops: t.FrozenSet[str] = frozenset()
    intercepted_unops: t.FrozenSet[str] = frozenset()

    def __init__(self, *args: t.Any, **kwargs: t.Any) ->None:
        super().__init__(*args, **kwargs)
        self.globals['range'] = safe_range
        self.binop_table = self.default_binop_table.copy()
        self.unop_table = self.default_unop_table.copy()

    def is_safe_attribute(self, obj: t.Any, attr: str, value: t.Any) ->bool:
        """The sandboxed environment will call this method to check if the
        attribute of an object is safe to access.  Per default all attributes
        starting with an underscore are considered private as well as the
        special attributes of internal python objects as returned by the
        :func:`is_internal_attribute` function.
        """
        pass

    def is_safe_callable(self, obj: t.Any) ->bool:
        """Check if an object is safely callable. By default callables
        are considered safe unless decorated with :func:`unsafe`.

        This also recognizes the Django convention of setting
        ``func.alters_data = True``.
        """
        pass

    def call_binop(self, context: Context, operator: str, left: t.Any,
        right: t.Any) ->t.Any:
        """For intercepted binary operator calls (:meth:`intercepted_binops`)
        this function is executed instead of the builtin operator.  This can
        be used to fine tune the behavior of certain operators.

        .. versionadded:: 2.6
        """
        pass

    def call_unop(self, context: Context, operator: str, arg: t.Any) ->t.Any:
        """For intercepted unary operator calls (:meth:`intercepted_unops`)
        this function is executed instead of the builtin operator.  This can
        be used to fine tune the behavior of certain operators.

        .. versionadded:: 2.6
        """
        pass

    def getitem(self, obj: t.Any, argument: t.Union[str, t.Any]) ->t.Union[
        t.Any, Undefined]:
        """Subscribe an object from sandboxed code."""
        pass

    def getattr(self, obj: t.Any, attribute: str) ->t.Union[t.Any, Undefined]:
        """Subscribe an object from sandboxed code and prefer the
        attribute.  The attribute passed *must* be a bytestring.
        """
        pass

    def unsafe_undefined(self, obj: t.Any, attribute: str) ->Undefined:
        """Return an undefined object for unsafe attributes."""
        pass

    def format_string(self, s: str, args: t.Tuple[t.Any, ...], kwargs: t.
        Dict[str, t.Any], format_func: t.Optional[t.Callable[..., t.Any]]=None
        ) ->str:
        """If a format call is detected, then this is routed through this
        method so that our safety sandbox can be used for it.
        """
        pass

    def call(__self, __context: Context, __obj: t.Any, *args: t.Any, **
        kwargs: t.Any) ->t.Any:
        """Call an object from sandboxed code."""
        pass


class ImmutableSandboxedEnvironment(SandboxedEnvironment):
    """Works exactly like the regular `SandboxedEnvironment` but does not
    permit modifications on the builtin mutable objects `list`, `set`, and
    `dict` by using the :func:`modifies_known_mutable` function.
    """


class SandboxedFormatter(Formatter):

    def __init__(self, env: Environment, **kwargs: t.Any) ->None:
        self._env = env
        super().__init__(**kwargs)


class SandboxedEscapeFormatter(SandboxedFormatter, EscapeFormatter):
    pass
