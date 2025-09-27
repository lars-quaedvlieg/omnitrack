from __future__ import annotations

from typing import Iterable, Optional

import wandb

from ..core.interfaces import Sink, SupportsFlush
from ..core.types import ConfigRecord, MetricRecord, TagRecord


class WandbSink(Sink, SupportsFlush):
    def __init__(self, **wandb_init_kwargs):
        self._run: Optional[wandb.sdk.wandb_run.Run] = None
        self._init_kwargs = wandb_init_kwargs
        self._defined_steps: set[str] = set()
        self._defined_metric_pairs: set[tuple[str, str]] = set()

    def on_open(self):
        self._run = wandb.init(**self._init_kwargs)

    def on_close(self):
        if self._run is not None:
            self._run.finish()
            self._run = None

    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None:
        for r in batch:
            # Namespace metrics by step name to avoid conflicts
            payload = {}
            for metric_key, metric_value in r.metrics.items():
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
            for k, v in cfg.config.items():
                self._run.config[k] = v

    def emit_tags(self, tags: TagRecord) -> None:
        if self._run is not None:
            existing = set(self._run.tags or [])
            for k, v in tags.tags.items():
                existing.add(f"{k}:{v}")
            self._run.tags = list(sorted(existing))

    def flush(self) -> None:
        pass  # wandb handles internal flushing
