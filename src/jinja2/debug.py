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
    exc_type, exc_value, tb = sys.exc_info()
    if isinstance(exc_value, TemplateSyntaxError) and source is not None:
        exc_value.source = source
    
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == '<template>':
            filename = exc_value.filename
            lineno = exc_value.lineno
            
            # Create a fake traceback
            new_tb = fake_traceback(exc_value, tb, filename, lineno)
            
            # Replace the old traceback with the new one
            exc_value.__traceback__ = new_tb
            break
        
        tb = tb.tb_next
    
    return exc_value


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
    if tb is None:
        raise exc_value

    locals = get_template_locals(tb.tb_frame.f_locals)
    globals = tb.tb_frame.f_globals

    # Create a fake code object
    code = CodeType(
        0,                      # argcount
        0,                      # kwonlyargcount
        0,                      # nlocals
        0,                      # stacksize
        0,                      # flags
        b'',                    # bytecode
        (),                     # constants
        (),                     # names
        (),                     # varnames
        filename,               # filename
        '<template>',           # name
        lineno,                 # firstlineno
        b'',                    # lnotab
        (),                     # freevars
        ()                      # cellvars
    )

    # Create a fake frame
    fake_frame = tb.tb_frame.__class__(code, globals, locals)
    fake_frame.f_lineno = lineno

    # Create a new traceback object
    return TracebackType(None, fake_frame, fake_frame.f_lasti, fake_frame.f_lineno)


def get_template_locals(real_locals: t.Mapping[str, t.Any]) ->t.Dict[str, t.Any
    ]:
    """Based on the runtime locals, get the context that would be
    available at that point in the template.
    """
    context = real_locals.get('context')
    if isinstance(context, Context):
        return {
            'context': context,
            'environment': context.environment,
            'resolver': context.environment.resolver,
            **context.get_all()
        }
    return {}
