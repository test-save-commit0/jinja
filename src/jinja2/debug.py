import sys
import typing as t
from types import CodeType
from types import TracebackType
from .exceptions import TemplateSyntaxError
from .utils import internal_code
from .utils import missing
if t.TYPE_CHECKING:
    from .runtime import Context


def rewrite_traceback_stack(source: t.Optional[str]=None) ->BaseException:
    """Rewrite the current exception to replace any tracebacks from
    within compiled template code with tracebacks that look like they
    came from the template source.

    This must be called within an ``except`` block.

    :param source: For ``TemplateSyntaxError``, the original source if
        known.
    :return: The original exception with the rewritten traceback.
    """
    pass


def fake_traceback(exc_value: BaseException, tb: t.Optional[TracebackType],
    filename: str, lineno: int) ->TracebackType:
    """Produce a new traceback object that looks like it came from the
    template source instead of the compiled code. The filename, line
    number, and location name will point to the template, and the local
    variables will be the current template context.

    :param exc_value: The original exception to be re-raised to create
        the new traceback.
    :param tb: The original traceback to get the local variables and
        code info from.
    :param filename: The template filename.
    :param lineno: The line number in the template source.
    """
    pass


def get_template_locals(real_locals: t.Mapping[str, t.Any]) ->t.Dict[str, t.Any
    ]:
    """Based on the runtime locals, get the context that would be
    available at that point in the template.
    """
    pass
