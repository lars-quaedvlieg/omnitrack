from __future__ import annotations

from numbers import Number
from typing import Iterable, Optional

import wandb

from ..core.interfaces import Sink, SupportsFlush
from ..core.types import ConfigRecord, MetricRecord, MetricValue, TagRecord


class WandbSink(Sink, SupportsFlush):
    def __init__(self, **wandb_init_kwargs):
        self._run: Optional[wandb.sdk.wandb_run.Run] = None
        self._init_kwargs = wandb_init_kwargs
        self._defined_steps: set[str] = set()
        self._defined_metric_pairs: set[tuple[str, str]] = set()
        self._run_id: Optional[str] = None

    def on_open(self):
        self._run = wandb.init(**self._init_kwargs)

    def on_close(self):
        if self._run is not None:
            self._run.finish()
            self._run = None

    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None:
        for r in batch:
            # Set run_id if not already set
            self._set_run_id(r.run_id.value)

            # Namespace metrics by step name to avoid conflicts
            payload = {}
            for metric_key, metric_value in r.metrics.items():
                # Validate metric type for wandb compatibility
                self._validate_metric_type(metric_key, metric_value)

                namespaced_key = f"{r.step_name}/{metric_key}"
                payload[namespaced_key] = metric_value

            # Add step counter
            if r.step_value is not None:
                step_key = f"step_levels/{r.step_name}"
                payload[step_key] = r.step_value

                # Define the step counter itself if not already defined
                if r.step_name not in self._defined_steps:
                    wandb.define_metric(step_key)
                    self._defined_steps.add(r.step_name)

                # Define step relationship for each namespaced metric
                for metric_key in r.metrics.keys():
                    namespaced_key = f"{r.step_name}/{metric_key}"
                    pair = (namespaced_key, r.step_name)
                    if pair not in self._defined_metric_pairs:
                        wandb.define_metric(namespaced_key, step_metric=step_key)
                        self._defined_metric_pairs.add(pair)

            wandb.log(payload)

    def emit_config(self, cfg: ConfigRecord) -> None:
        if self._run is not None:
            # Set run_id if not already set
            self._set_run_id(cfg.run_id.value)

            # Add user config
            for k, v in cfg.config.items():
                self._run.config[k] = v

    def emit_tags(self, tags: TagRecord) -> None:
        if self._run is not None:
            # Set run_id if not already set
            self._set_run_id(tags.run_id.value)

            existing = set(self._run.tags or [])
            for k, v in tags.tags.items():
                existing.add(f"{k}:{v}")
            self._run.tags = list(sorted(existing))

    def _set_run_id(self, run_id: str) -> None:
        """Set the omnitrack run_id in wandb config if not already set."""
        if self._run_id is None and self._run is not None:
            self._run_id = run_id
            self._run.config["omnitrack_run_id"] = run_id

    def _validate_metric_type(self, metric_key: str, metric_value) -> None:
        """Validate that a metric value is supported by WandbSink."""
        if isinstance(metric_value, MetricValue):
            raise TypeError(
                f"WandbSink does not support custom MetricValue types. "
                f"Metric '{metric_key}' has type {type(metric_value).__name__}. "
                f"Use numeric types (int, float, Number) instead."
            )
        if not isinstance(metric_value, (int, float, Number)):
            raise TypeError(
                f"WandbSink only supports numeric metric values. "
                f"Metric '{metric_key}' has unsupported type {type(metric_value).__name__}. "
                f"Use int, float, or Number types instead."
            )

    def flush(self) -> None:
        pass  # wandb handles internal flushing
