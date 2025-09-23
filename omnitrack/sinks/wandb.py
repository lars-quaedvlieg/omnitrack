from __future__ import annotations

from typing import Iterable, Optional

import wandb

from ..core.interfaces import Sink, SupportsFlush
from ..core.types import ConfigRecord, MetricRecord, TagRecord


class WandbSink(Sink, SupportsFlush):
    def __init__(self, **wandb_init_kwargs):
        self._run: Optional[wandb.sdk.wandb_run.Run] = None
        self._init_kwargs = wandb_init_kwargs
        self._defined: set[str] = set()

    def on_open(self):
        self._run = wandb.init(**self._init_kwargs)

    def on_close(self):
        if self._run is not None:
            self._run.finish()
            self._run = None

    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None:
        for r in batch:
            payload = dict(r.metrics)

            # Namespace the step into "step_levels/{name}"
            if r.step_value is not None:
                step_key = f"step_levels/{r.step_name}"
                payload[step_key] = r.step_value

                # Only define metrics once per step_name
                if r.step_name not in self._defined:
                    wandb.define_metric(step_key)  # the counter itself
                    # link all current metric keys to this step axis
                    for key in r.metrics.keys():
                        wandb.define_metric(key, step_metric=step_key)
                    self._defined.add(r.step_name)

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
