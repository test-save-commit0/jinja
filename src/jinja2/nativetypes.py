import typing as t
import sys
from ast import literal_eval
from ast import parse
from itertools import chain
from itertools import islice
from types import GeneratorType
from . import nodes
from .compiler import CodeGenerator
from .compiler import Frame
from .compiler import has_safe_repr
from .environment import Environment
from .environment import Template


def native_concat(values: t.Iterable[t.Any]) ->t.Optional[t.Any]:
    """Return a native Python type from the list of compiled nodes. If
    the result is a single node, its value is returned. Otherwise, the
    nodes are concatenated as strings. If the result can be parsed with
    :func:`ast.literal_eval`, the parsed value is returned. Otherwise,
    the string is returned.

    :param values: Iterable of outputs to concatenate.
    """
    result = list(values)
    if not result:
        return None
    if len(result) == 1:
        return result[0]
    
    try:
        return literal_eval("".join(str(v) for v in result))
    except (ValueError, SyntaxError):
        return "".join(str(v) for v in result)


class NativeCodeGenerator(CodeGenerator):
    """A code generator which renders Python types by not adding
    ``str()`` around output nodes.
    """


class NativeEnvironment(Environment):
    """An environment that renders templates to native Python types."""
    code_generator_class = NativeCodeGenerator
    concat = staticmethod(native_concat)


class NativeTemplate(Template):
    environment_class = NativeEnvironment

    def render(self, *args: t.Any, **kwargs: t.Any) ->t.Any:
        """Render the template to produce a native Python type. If the
        result is a single node, its value is returned. Otherwise, the
        nodes are concatenated as strings. If the result can be parsed
        with :func:`ast.literal_eval`, the parsed value is returned.
        Otherwise, the string is returned.
        """
        ctx = self.new_context(dict(*args, **kwargs))
        try:
            return self.environment.concat(self.root_render_func(ctx))
        except Exception:
            exc_info = sys.exc_info()
            return self.environment.handle_exception(exc_info, True)


NativeEnvironment.template_class = NativeTemplate
