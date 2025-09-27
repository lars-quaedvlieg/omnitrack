from __future__ import annotations

from typing import Any, Dict, List, Optional

from .context import current
from .session import LogSession  # for type hints only

_DEFAULT_STEP = "global"


def record(
    *,
    exclude: list[str] = None,
    include: list[str] = None,
    step_name: str = _DEFAULT_STEP,
    **metrics,
):
    ctx = current()
    if ctx is None:
        return
    step_val = ctx.get_step(step_name)
    session: Optional[LogSession] = getattr(ctx, "_session", None)
    if session:
        session.emit_metrics(
            metrics, step_name=step_name, step_value=step_val, exclude=exclude, include=include
        )


def step(value: Optional[int] = None, name: str = _DEFAULT_STEP):
    ctx = current()
    if ctx is None:
        return
    last = ctx.get_step(name, -1)
    if value is None:
        value = last + 1
    elif value <= last:
        raise ValueError(f"Step for {name} must be > {last}, got {value}")
    ctx.set_step(name, value)


def push_config(*, exclude: list[str] = None, include: list[str] = None, config: Dict[str, Any]):
    ctx = current()
    if ctx is None:
        return
    session: Optional[LogSession] = getattr(ctx, "_session", None)
    if session is None:
        return
    session.emit_config(config, exclude=exclude, include=include)


def set_tags(*, exclude: list[str] = None, include: list[str] = None, **tags: str):
    ctx = current()
    if ctx is None:
        return
    session: Optional[LogSession] = getattr(ctx, "_session", None)
    if session is None:
        return
    session.emit_tags(tags, exclude=exclude, include=include)


def push(step_names: Optional[List[str]] = None):
    """Push current logs to sinks immediately.

    Args:
        step_names: If provided, only push metrics with these step names.
                   If None, push all accumulated data.
    """
    ctx = current()
    if ctx is None:
        return
    session: Optional[LogSession] = getattr(ctx, "_session", None)
    if session is None:
        return
    session.push(step_names)
