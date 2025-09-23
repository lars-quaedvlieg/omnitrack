from functools import wraps
from typing import Any, Callable

from ..core.api import record


def autolog(fn: Callable) -> Callable:
    """
    Decorator that normalizes legacy return values into `record()` calls.

    Accepted return forms:
      - value
      - (value, {"metric": ...})
      - {"metric": ...}  (no value, just metrics)
    """

    @wraps(fn)
    def wrapper(*args, **kwargs) -> Any:
        out = fn(*args, **kwargs)

        value, metrics = out, None
        if isinstance(out, tuple) and len(out) == 2 and isinstance(out[1], dict):
            value, metrics = out
        elif isinstance(out, dict):
            value, metrics = None, out

        if metrics:
            record(**metrics)
        return value

    return wrapper
