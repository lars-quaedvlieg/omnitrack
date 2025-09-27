from __future__ import annotations

from typing import Any, Dict, List, Optional

from .context import RunContext, set_current
from .interfaces import Sink, SupportsFlush
from .types import ConfigRecord, MetricRecord, RunId, TagRecord


class LogSession:
    """
    Context manager owning the run lifecycle + sinks with direct communication.
    """

    def __init__(self, sinks: List[Sink]):
        self.run_id = RunId.new()
        self._ctx = RunContext(self.run_id)
        self.sinks = sinks
        self._metrics: List[MetricRecord] = []
        self._configs: List[ConfigRecord] = []
        self._tags: List[TagRecord] = []

    def __enter__(self) -> "LogSession":
        set_current(self._ctx)
        # Initialize sinks
        for sink in self.sinks:
            sink.on_open()
        setattr(self._ctx, "_session", self)  # backpointer for API
        return self

    def __exit__(self, exc_type, exc, tb):
        # Flush any remaining metrics
        self.push()
        # Close sinks
        for sink in self.sinks:
            if isinstance(sink, SupportsFlush):
                sink.flush()
            sink.on_close()
        set_current(None)

    def emit_metrics(
        self,
        metrics: Dict[str, Any],
        step_name: str,
        step_value: Optional[int],
        exclude: list[str] = None,
        include: list[str] = None,
    ):
        rec = MetricRecord(
            run_id=self.run_id,
            step_name=step_name,
            step_value=step_value,
            metrics=metrics,
        )
        rec._exclude = exclude or []  # attach metadata
        rec._include = include or []  # attach metadata
        self._metrics.append(rec)

    def emit_config(
        self, cfg: Dict[str, Any], exclude: list[str] = None, include: list[str] = None
    ):
        rec = ConfigRecord(run_id=self.run_id, config=cfg)
        rec._exclude = exclude or []  # attach metadata
        rec._include = include or []  # attach metadata
        self._configs.append(rec)

    def emit_tags(self, tags: Dict[str, str], exclude: list[str] = None, include: list[str] = None):
        rec = TagRecord(run_id=self.run_id, tags=tags)
        rec._exclude = exclude or []  # attach metadata
        rec._include = include or []  # attach metadata
        self._tags.append(rec)

    def set_step(self, name: str, value: int):
        self._ctx.set_step(name, value)

    def push(self, step_names: Optional[List[str]] = None):
        """Push current logs to sinks immediately.

        Args:
            step_names: If provided, only push metrics with these step names.
                       If None, push all accumulated data.
        """
        # Send metrics
        if self._metrics:
            metrics_to_push = self._metrics
            metrics_to_keep = []

            # Filter by step names if specified
            if step_names is not None:
                metrics_to_push = []
                for rec in self._metrics:
                    if rec.step_name in step_names:
                        metrics_to_push.append(rec)
                    else:
                        metrics_to_keep.append(rec)
                # Update the stored metrics (keep the ones not being pushed)
                self._metrics = metrics_to_keep

            if metrics_to_push:
                for sink in self.sinks:
                    sink_name = type(sink).__name__
                    filtered = self._filter_records(metrics_to_push, sink_name)
                    if filtered:
                        sink.emit_metrics(filtered)

            # If no step_names filter, clear all metrics after pushing
            if step_names is None:
                self._metrics.clear()

        # Send configs (always push all if no step_names filter, or if step_names is specified)
        if self._configs and (step_names is None or not step_names):
            for sink in self.sinks:
                sink_name = type(sink).__name__
                filtered = self._filter_records(self._configs, sink_name)
                for rec in filtered:
                    sink.emit_config(rec)
            if step_names is None:
                self._configs.clear()

        # Send tags (always push all if no step_names filter, or if step_names is specified)
        if self._tags and (step_names is None or not step_names):
            for sink in self.sinks:
                sink_name = type(sink).__name__
                filtered = self._filter_records(self._tags, sink_name)
                for rec in filtered:
                    sink.emit_tags(rec)
            if step_names is None:
                self._tags.clear()

        # Flush sinks that support it
        for sink in self.sinks:
            if isinstance(sink, SupportsFlush):
                sink.flush()

    def _filter_records(self, records, sink_name: str):
        """Filter records based on include/exclude lists."""
        filtered = []
        for rec in records:
            exclude = getattr(rec, "_exclude", [])
            include = getattr(rec, "_include", [])

            # If include is specified, only send to those sinks
            if include:
                if sink_name in include:
                    filtered.append(rec)
            # If exclude is specified, don't send to those sinks
            elif sink_name not in exclude:
                filtered.append(rec)
            # If neither include nor exclude is specified, send to all sinks
            elif not include and not exclude:
                filtered.append(rec)

        return filtered
