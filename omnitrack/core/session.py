from __future__ import annotations

from typing import Any, Dict, List, Optional

from .context import RunContext, set_current
from .interfaces import Sink
from .router import Router
from .types import ConfigRecord, MetricRecord, RunId, TagRecord


class LogSession:
    """
    Context manager owning the run lifecycle + router + sinks.
    """

    def __init__(self, sinks: List[Sink], batch_size: int, flush_interval_s: float):
        self.run_id = RunId.new()
        self._ctx = RunContext(self.run_id)
        self._router = Router(sinks=sinks, batch_size=batch_size, flush_interval_s=flush_interval_s)

    def __enter__(self) -> "LogSession":
        set_current(self._ctx)
        self._router.start()
        setattr(self._ctx, "_session", self)  # backpointer for API
        return self

    def __exit__(self, exc_type, exc, tb):
        self._router.stop()
        set_current(None)

    def emit_metrics(
        self, metrics: Dict[str, Any], step_name: str, step_value: Optional[int], exclude: list[str]
    ):
        rec = MetricRecord(
            run_id=self.run_id,
            step_name=step_name,
            step_value=step_value,
            metrics=metrics,
        )
        rec._exclude = exclude  # attach metadata
        self._router.submit_metrics(rec)

    def emit_config(self, cfg: Dict[str, Any], exclude: list[str]):
        rec = ConfigRecord(run_id=self.run_id, config=cfg)
        rec._exclude = exclude  # attach metadata
        self._router.submit_config(rec)

    def emit_tags(self, tags: Dict[str, str], exclude: list[str]):
        rec = TagRecord(run_id=self.run_id, tags=tags)
        rec._exclude = exclude  # attach metadata
        self._router.submit_tags(rec)

    def set_step(self, name: str, value: int):
        self._ctx.set_step(name, value)
