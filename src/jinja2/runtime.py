"""The runtime functions and state used by compiled templates."""
import functools
import sys
import typing as t
from collections import abc
from itertools import chain
from markupsafe import escape
from markupsafe import Markup
from markupsafe import soft_str
from .async_utils import auto_aiter
from .async_utils import auto_await
from .exceptions import TemplateNotFound
from .exceptions import TemplateRuntimeError
from .exceptions import UndefinedError
from .nodes import EvalContext
from .utils import _PassArg
from .utils import concat
from .utils import internalcode
from .utils import missing
from .utils import Namespace
from .utils import object_type_repr
from .utils import pass_eval_context
V = t.TypeVar('V')
F = t.TypeVar('F', bound=t.Callable[..., t.Any])
if t.TYPE_CHECKING:
    import logging
    import typing_extensions as te
    from .environment import Environment


    class LoopRenderFunc(te.Protocol):

        def __call__(self, reciter: t.Iterable[V], loop_render_func:
            'LoopRenderFunc', depth: int=0) ->str:
            ...
exported = ['LoopContext', 'TemplateReference', 'Macro', 'Markup',
    'TemplateRuntimeError', 'missing', 'escape', 'markup_join', 'str_join',
    'identity', 'TemplateNotFound', 'Namespace', 'Undefined', 'internalcode']
async_exported = ['AsyncLoopContext', 'auto_aiter', 'auto_await']


def identity(x: V) ->V:
    """Returns its argument. Useful for certain things in the
    environment.
    """
    pass


def markup_join(seq: t.Iterable[t.Any]) ->str:
    """Concatenation that escapes if necessary and converts to string."""
    pass


def str_join(seq: t.Iterable[t.Any]) ->str:
    """Simple args to string conversion and concatenation."""
    pass


def new_context(environment: 'Environment', template_name: t.Optional[str],
    blocks: t.Dict[str, t.Callable[['Context'], t.Iterator[str]]], vars: t.
    Optional[t.Dict[str, t.Any]]=None, shared: bool=False, globals: t.
    Optional[t.MutableMapping[str, t.Any]]=None, locals: t.Optional[t.
    Mapping[str, t.Any]]=None) ->'Context':
    """Internal helper for context creation."""
    pass


class TemplateReference:
    """The `self` in templates."""

    def __init__(self, context: 'Context') ->None:
        self.__context = context

    def __getitem__(self, name: str) ->t.Any:
        blocks = self.__context.blocks[name]
        return BlockReference(name, self.__context, blocks, 0)

    def __repr__(self) ->str:
        return f'<{type(self).__name__} {self.__context.name!r}>'


@abc.Mapping.register
class Context:
    """The template context holds the variables of a template.  It stores the
    values passed to the template and also the names the template exports.
    Creating instances is neither supported nor useful as it's created
    automatically at various stages of the template evaluation and should not
    be created by hand.

    The context is immutable.  Modifications on :attr:`parent` **must not**
    happen and modifications on :attr:`vars` are allowed from generated
    template code only.  Template filters and global functions marked as
    :func:`pass_context` get the active context passed as first argument
    and are allowed to access the context read-only.

    The template context supports read only dict operations (`get`,
    `keys`, `values`, `items`, `iterkeys`, `itervalues`, `iteritems`,
    `__getitem__`, `__contains__`).  Additionally there is a :meth:`resolve`
    method that doesn't fail with a `KeyError` but returns an
    :class:`Undefined` object for missing variables.
    """

    def __init__(self, environment: 'Environment', parent: t.Dict[str, t.
        Any], name: t.Optional[str], blocks: t.Dict[str, t.Callable[[
        'Context'], t.Iterator[str]]], globals: t.Optional[t.MutableMapping
        [str, t.Any]]=None):
        self.parent = parent
        self.vars: t.Dict[str, t.Any] = {}
        self.environment: 'Environment' = environment
        self.eval_ctx = EvalContext(self.environment, name)
        self.exported_vars: t.Set[str] = set()
        self.name = name
        self.globals_keys = set() if globals is None else set(globals)
        self.blocks = {k: [v] for k, v in blocks.items()}

    def super(self, name: str, current: t.Callable[['Context'], t.Iterator[
        str]]) ->t.Union['BlockReference', 'Undefined']:
        """Render a parent block."""
        pass

    def get(self, key: str, default: t.Any=None) ->t.Any:
        """Look up a variable by name, or return a default if the key is
        not found.

        :param key: The variable name to look up.
        :param default: The value to return if the key is not found.
        """
        pass

    def resolve(self, key: str) ->t.Union[t.Any, 'Undefined']:
        """Look up a variable by name, or return an :class:`Undefined`
        object if the key is not found.

        If you need to add custom behavior, override
        :meth:`resolve_or_missing`, not this method. The various lookup
        functions use that method, not this one.

        :param key: The variable name to look up.
        """
        pass

    def resolve_or_missing(self, key: str) ->t.Any:
        """Look up a variable by name, or return a ``missing`` sentinel
        if the key is not found.

        Override this method to add custom lookup behavior.
        :meth:`resolve`, :meth:`get`, and :meth:`__getitem__` use this
        method. Don't call this method directly.

        :param key: The variable name to look up.
        """
        pass

    def get_exported(self) ->t.Dict[str, t.Any]:
        """Get a new dict with the exported variables."""
        pass

    def get_all(self) ->t.Dict[str, t.Any]:
        """Return the complete context as dict including the exported
        variables.  For optimizations reasons this might not return an
        actual copy so be careful with using it.
        """
        pass

    @internalcode
    def call(__self, __obj: t.Callable[..., t.Any], *args: t.Any, **kwargs:
        t.Any) ->t.Union[t.Any, 'Undefined']:
        """Call the callable with the arguments and keyword arguments
        provided but inject the active context or environment as first
        argument if the callable has :func:`pass_context` or
        :func:`pass_environment`.
        """
        pass

    def derived(self, locals: t.Optional[t.Dict[str, t.Any]]=None) ->'Context':
        """Internal helper function to create a derived context.  This is
        used in situations where the system needs a new context in the same
        template that is independent.
        """
        pass
    keys = _dict_method_all(dict.keys)
    values = _dict_method_all(dict.values)
    items = _dict_method_all(dict.items)

    def __contains__(self, name: str) ->bool:
        return name in self.vars or name in self.parent

    def __getitem__(self, key: str) ->t.Any:
        """Look up a variable by name with ``[]`` syntax, or raise a
        ``KeyError`` if the key is not found.
        """
        item = self.resolve_or_missing(key)
        if item is missing:
            raise KeyError(key)
        return item

    def __repr__(self) ->str:
        return f'<{type(self).__name__} {self.get_all()!r} of {self.name!r}>'


class BlockReference:
    """One block on a template reference."""

    def __init__(self, name: str, context: 'Context', stack: t.List[t.
        Callable[['Context'], t.Iterator[str]]], depth: int) ->None:
        self.name = name
        self._context = context
        self._stack = stack
        self._depth = depth

    @property
    def super(self) ->t.Union['BlockReference', 'Undefined']:
        """Super the block."""
        pass

    @internalcode
    def __call__(self) ->str:
        if self._context.environment.is_async:
            return self._async_call()
        rv = concat(self._stack[self._depth](self._context))
        if self._context.eval_ctx.autoescape:
            return Markup(rv)
        return rv


class LoopContext:
    """A wrapper iterable for dynamic ``for`` loops, with information
    about the loop and iteration.
    """
    index0 = -1
    _length: t.Optional[int] = None
    _after: t.Any = missing
    _current: t.Any = missing
    _before: t.Any = missing
    _last_changed_value: t.Any = missing

    def __init__(self, iterable: t.Iterable[V], undefined: t.Type[
        'Undefined'], recurse: t.Optional['LoopRenderFunc']=None, depth0: int=0
        ) ->None:
        """
        :param iterable: Iterable to wrap.
        :param undefined: :class:`Undefined` class to use for next and
            previous items.
        :param recurse: The function to render the loop body when the
            loop is marked recursive.
        :param depth0: Incremented when looping recursively.
        """
        self._iterable = iterable
        self._iterator = self._to_iterator(iterable)
        self._undefined = undefined
        self._recurse = recurse
        self.depth0 = depth0

    @property
    def length(self) ->int:
        """Length of the iterable.

        If the iterable is a generator or otherwise does not have a
        size, it is eagerly evaluated to get a size.
        """
        pass

    def __len__(self) ->int:
        return self.length

    @property
    def depth(self) ->int:
        """How many levels deep a recursive loop currently is, starting at 1."""
        pass

    @property
    def index(self) ->int:
        """Current iteration of the loop, starting at 1."""
        pass

    @property
    def revindex0(self) ->int:
        """Number of iterations from the end of the loop, ending at 0.

        Requires calculating :attr:`length`.
        """
        pass

    @property
    def revindex(self) ->int:
        """Number of iterations from the end of the loop, ending at 1.

        Requires calculating :attr:`length`.
        """
        pass

    @property
    def first(self) ->bool:
        """Whether this is the first iteration of the loop."""
        pass

    def _peek_next(self) ->t.Any:
        """Return the next element in the iterable, or :data:`missing`
        if the iterable is exhausted. Only peeks one item ahead, caching
        the result in :attr:`_last` for use in subsequent checks. The
        cache is reset when :meth:`__next__` is called.
        """
        pass

    @property
    def last(self) ->bool:
        """Whether this is the last iteration of the loop.

        Causes the iterable to advance early. See
        :func:`itertools.groupby` for issues this can cause.
        The :func:`groupby` filter avoids that issue.
        """
        pass

    @property
    def previtem(self) ->t.Union[t.Any, 'Undefined']:
        """The item in the previous iteration. Undefined during the
        first iteration.
        """
        pass

    @property
    def nextitem(self) ->t.Union[t.Any, 'Undefined']:
        """The item in the next iteration. Undefined during the last
        iteration.

        Causes the iterable to advance early. See
        :func:`itertools.groupby` for issues this can cause.
        The :func:`jinja-filters.groupby` filter avoids that issue.
        """
        pass

    def cycle(self, *args: V) ->V:
        """Return a value from the given args, cycling through based on
        the current :attr:`index0`.

        :param args: One or more values to cycle through.
        """
        pass

    def changed(self, *value: t.Any) ->bool:
        """Return ``True`` if previously called with a different value
        (including when called for the first time).

        :param value: One or more values to compare to the last call.
        """
        pass

    def __iter__(self) ->'LoopContext':
        return self

    def __next__(self) ->t.Tuple[t.Any, 'LoopContext']:
        if self._after is not missing:
            rv = self._after
            self._after = missing
        else:
            rv = next(self._iterator)
        self.index0 += 1
        self._before = self._current
        self._current = rv
        return rv, self

    @internalcode
    def __call__(self, iterable: t.Iterable[V]) ->str:
        """When iterating over nested data, render the body of the loop
        recursively with the given inner iterable data.

        The loop must have the ``recursive`` marker for this to work.
        """
        if self._recurse is None:
            raise TypeError(
                "The loop must have the 'recursive' marker to be called recursively."
                )
        return self._recurse(iterable, self._recurse, depth=self.depth)

    def __repr__(self) ->str:
        return f'<{type(self).__name__} {self.index}/{self.length}>'


class AsyncLoopContext(LoopContext):
    _iterator: t.AsyncIterator[t.Any]

    def __aiter__(self) ->'AsyncLoopContext':
        return self

    async def __anext__(self) ->t.Tuple[t.Any, 'AsyncLoopContext']:
        if self._after is not missing:
            rv = self._after
            self._after = missing
        else:
            rv = await self._iterator.__anext__()
        self.index0 += 1
        self._before = self._current
        self._current = rv
        return rv, self


class Macro:
    """Wraps a macro function."""

    def __init__(self, environment: 'Environment', func: t.Callable[...,
        str], name: str, arguments: t.List[str], catch_kwargs: bool,
        catch_varargs: bool, caller: bool, default_autoescape: t.Optional[
        bool]=None):
        self._environment = environment
        self._func = func
        self._argument_count = len(arguments)
        self.name = name
        self.arguments = arguments
        self.catch_kwargs = catch_kwargs
        self.catch_varargs = catch_varargs
        self.caller = caller
        self.explicit_caller = 'caller' in arguments
        if default_autoescape is None:
            if callable(environment.autoescape):
                default_autoescape = environment.autoescape(None)
            else:
                default_autoescape = environment.autoescape
        self._default_autoescape = default_autoescape

    @internalcode
    @pass_eval_context
    def __call__(self, *args: t.Any, **kwargs: t.Any) ->str:
        if args and isinstance(args[0], EvalContext):
            autoescape = args[0].autoescape
            args = args[1:]
        else:
            autoescape = self._default_autoescape
        arguments = list(args[:self._argument_count])
        off = len(arguments)
        found_caller = False
        if off != self._argument_count:
            for name in self.arguments[len(arguments):]:
                try:
                    value = kwargs.pop(name)
                except KeyError:
                    value = missing
                if name == 'caller':
                    found_caller = True
                arguments.append(value)
        else:
            found_caller = self.explicit_caller
        if self.caller and not found_caller:
            caller = kwargs.pop('caller', None)
            if caller is None:
                caller = self._environment.undefined('No caller defined',
                    name='caller')
            arguments.append(caller)
        if self.catch_kwargs:
            arguments.append(kwargs)
        elif kwargs:
            if 'caller' in kwargs:
                raise TypeError(
                    f'macro {self.name!r} was invoked with two values for the special caller argument. This is most likely a bug.'
                    )
            raise TypeError(
                f'macro {self.name!r} takes no keyword argument {next(iter(kwargs))!r}'
                )
        if self.catch_varargs:
            arguments.append(args[self._argument_count:])
        elif len(args) > self._argument_count:
            raise TypeError(
                f'macro {self.name!r} takes not more than {len(self.arguments)} argument(s)'
                )
        return self._invoke(arguments, autoescape)

    def __repr__(self) ->str:
        name = 'anonymous' if self.name is None else repr(self.name)
        return f'<{type(self).__name__} {name}>'


class Undefined:
    """The default undefined type.  This undefined type can be printed and
    iterated over, but every other access will raise an :exc:`UndefinedError`:

    >>> foo = Undefined(name='foo')
    >>> str(foo)
    ''
    >>> not foo
    True
    >>> foo + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    """
    __slots__ = ('_undefined_hint', '_undefined_obj', '_undefined_name',
        '_undefined_exception')

    def __init__(self, hint: t.Optional[str]=None, obj: t.Any=missing, name:
        t.Optional[str]=None, exc: t.Type[TemplateRuntimeError]=UndefinedError
        ) ->None:
        self._undefined_hint = hint
        self._undefined_obj = obj
        self._undefined_name = name
        self._undefined_exception = exc

    @property
    def _undefined_message(self) ->str:
        """Build a message about the undefined value based on how it was
        accessed.
        """
        pass

    @internalcode
    def _fail_with_undefined_error(self, *args: t.Any, **kwargs: t.Any
        ) ->'te.NoReturn':
        """Raise an :exc:`UndefinedError` when operations are performed
        on the undefined value.
        """
        pass

    @internalcode
    def __getattr__(self, name: str) ->t.Any:
        if name[:2] == '__':
            raise AttributeError(name)
        return self._fail_with_undefined_error()
    __add__ = __radd__ = __sub__ = __rsub__ = _fail_with_undefined_error
    __mul__ = __rmul__ = __div__ = __rdiv__ = _fail_with_undefined_error
    __truediv__ = __rtruediv__ = _fail_with_undefined_error
    __floordiv__ = __rfloordiv__ = _fail_with_undefined_error
    __mod__ = __rmod__ = _fail_with_undefined_error
    __pos__ = __neg__ = _fail_with_undefined_error
    __call__ = __getitem__ = _fail_with_undefined_error
    __lt__ = __le__ = __gt__ = __ge__ = _fail_with_undefined_error
    __int__ = __float__ = __complex__ = _fail_with_undefined_error
    __pow__ = __rpow__ = _fail_with_undefined_error

    def __eq__(self, other: t.Any) ->bool:
        return type(self) is type(other)

    def __ne__(self, other: t.Any) ->bool:
        return not self.__eq__(other)

    def __hash__(self) ->int:
        return id(type(self))

    def __str__(self) ->str:
        return ''

    def __len__(self) ->int:
        return 0

    def __iter__(self) ->t.Iterator[t.Any]:
        yield from ()

    async def __aiter__(self) ->t.AsyncIterator[t.Any]:
        for _ in ():
            yield

    def __bool__(self) ->bool:
        return False

    def __repr__(self) ->str:
        return 'Undefined'


def make_logging_undefined(logger: t.Optional['logging.Logger']=None, base:
    t.Type[Undefined]=Undefined) ->t.Type[Undefined]:
    """Given a logger object this returns a new undefined class that will
    log certain failures.  It will log iterations and printing.  If no
    logger is given a default logger is created.

    Example::

        logger = logging.getLogger(__name__)
        LoggingUndefined = make_logging_undefined(
            logger=logger,
            base=Undefined
        )

    .. versionadded:: 2.8

    :param logger: the logger to use.  If not provided, a default logger
                   is created.
    :param base: the base class to add logging functionality to.  This
                 defaults to :class:`Undefined`.
    """
    pass


class ChainableUndefined(Undefined):
    """An undefined that is chainable, where both ``__getattr__`` and
    ``__getitem__`` return itself rather than raising an
    :exc:`UndefinedError`.

    >>> foo = ChainableUndefined(name='foo')
    >>> str(foo.bar['baz'])
    ''
    >>> foo.bar['baz'] + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined

    .. versionadded:: 2.11.0
    """
    __slots__ = ()

    def __html__(self) ->str:
        return str(self)

    def __getattr__(self, _: str) ->'ChainableUndefined':
        return self
    __getitem__ = __getattr__


class DebugUndefined(Undefined):
    """An undefined that returns the debug info when printed.

    >>> foo = DebugUndefined(name='foo')
    >>> str(foo)
    '{{ foo }}'
    >>> not foo
    True
    >>> foo + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    """
    __slots__ = ()

    def __str__(self) ->str:
        if self._undefined_hint:
            message = f'undefined value printed: {self._undefined_hint}'
        elif self._undefined_obj is missing:
            message = self._undefined_name
        else:
            message = (
                f'no such element: {object_type_repr(self._undefined_obj)}[{self._undefined_name!r}]'
                )
        return f'{{{{ {message} }}}}'


class StrictUndefined(Undefined):
    """An undefined that barks on print and iteration as well as boolean
    tests and all kinds of comparisons.  In other words: you can do nothing
    with it except checking if it's defined using the `defined` test.

    >>> foo = StrictUndefined(name='foo')
    >>> str(foo)
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    >>> not foo
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    >>> foo + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    """
    __slots__ = ()
    __iter__ = __str__ = __len__ = Undefined._fail_with_undefined_error
    __eq__ = __ne__ = __bool__ = __hash__ = (Undefined.
        _fail_with_undefined_error)
    __contains__ = Undefined._fail_with_undefined_error


del (Undefined.__slots__, ChainableUndefined.__slots__, DebugUndefined.
    __slots__, StrictUndefined.__slots__)
