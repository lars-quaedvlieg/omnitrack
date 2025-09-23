import contextvars
from typing import Dict, Optional

from .types import RunId

_current_ctx: contextvars.ContextVar["RunContext|None"] = contextvars.ContextVar(
    "omnitrack_ctx", default=None
)


class RunContext:
    def __init__(self, run_id: RunId):
        self.run_id = run_id
        self.steps: Dict[str, int] = {}  # named counters

    def set_step(self, name: str, value: int):
        self.steps[name] = value

    def get_step(self, name: str, default: int = -1) -> Optional[int]:
        return self.steps.get(name, default)


def set_current(ctx: Optional[RunContext]):
    _current_ctx.set(ctx)


def current() -> Optional[RunContext]:
    return _current_ctx.get()
