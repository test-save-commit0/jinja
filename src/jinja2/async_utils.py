import inspect
import typing as t
from functools import WRAPPER_ASSIGNMENTS
from functools import wraps
from .utils import _PassArg
from .utils import pass_eval_context
V = t.TypeVar('V')
_common_primitives = {int, float, bool, str, list, dict, tuple, type(None)}
