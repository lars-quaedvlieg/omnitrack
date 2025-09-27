from __future__ import annotations

import json
from numbers import Number
from pathlib import Path
from typing import Any, Dict, Iterable

from ..core.interfaces import Sink, SupportsFlush
from ..core.types import ConfigRecord, MetricRecord, MetricValue, TagRecord


class LocalLogger(Sink, SupportsFlush):
    """
    Structured local logging that maintains hierarchical data for easy analysis.

    Stores data in a structured format that's easy to load back into pandas:
    - Metrics are grouped by step_name and stored as lists
    - Configs are accumulated into a single tree
    - Tags are accumulated into a single structure
    - Final output is a single JSON file with all run data
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self._data: Dict[str, Any] = {
            "run_id": None,
            "config": {},
            "tags": {},
            "metrics": {},
            "metadata": {"start_time": None, "end_time": None, "total_steps": {}},
        }
        self._step_counts: Dict[str, int] = {}

    def on_open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        import time

        self._data["metadata"]["start_time"] = time.time()

    def on_close(self):
        import time

        self._data["metadata"]["end_time"] = time.time()
        self._data["metadata"]["total_steps"] = self._step_counts.copy()

        # Write the complete structured data
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None:
        for r in batch:
            # Set run_id if not set
            if self._data["run_id"] is None:
                self._data["run_id"] = r.run_id.value

            # Initialize step_name structure if not exists
            if r.step_name not in self._data["metrics"]:
                self._data["metrics"][r.step_name] = {"steps": [], "metrics": {}}

            # Add step value to steps list
            if r.step_value is not None:
                self._data["metrics"][r.step_name]["steps"].append(r.step_value)
                self._step_counts[r.step_name] = max(
                    self._step_counts.get(r.step_name, -1), r.step_value
                )

            # Add metrics to the step_name structure
            for metric_name, metric_value in r.metrics.items():
                # Validate metric type for JSON serialization
                self._validate_metric_type(metric_name, metric_value)

                if metric_name not in self._data["metrics"][r.step_name]["metrics"]:
                    self._data["metrics"][r.step_name]["metrics"][metric_name] = []

                # Add the metric value
                self._data["metrics"][r.step_name]["metrics"][metric_name].append(metric_value)

    def emit_config(self, cfg: ConfigRecord) -> None:
        # Set run_id if not set
        if self._data["run_id"] is None:
            self._data["run_id"] = cfg.run_id.value

        # Deep merge configs into the accumulated config
        self._deep_merge(self._data["config"], cfg.config)

    def emit_tags(self, tags: TagRecord) -> None:
        # Set run_id if not set
        if self._data["run_id"] is None:
            self._data["run_id"] = tags.run_id.value

        # Merge tags into the accumulated tags
        self._data["tags"].update(tags.tags)

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _validate_metric_type(self, metric_key: str, metric_value) -> None:
        """Validate that a metric value is supported by LocalLogger."""
        if isinstance(metric_value, MetricValue):
            raise TypeError(
                f"LocalLogger does not support custom MetricValue types. "
                f"Metric '{metric_key}' has type {type(metric_value).__name__}. "
                f"Use numeric types (int, float, Number) instead."
            )
        if not isinstance(metric_value, (int, float, Number)):
            raise TypeError(
                f"LocalLogger only supports numeric metric values. "
                f"Metric '{metric_key}' has unsupported type {type(metric_value).__name__}. "
                f"Use int, float, or Number types instead."
            )

    def flush(self) -> None:
        # LocalLogger doesn't need explicit flushing since it writes on close
        pass
