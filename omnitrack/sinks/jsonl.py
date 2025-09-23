from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ..core.interfaces import Sink, SupportsFlush
from ..core.types import ConfigRecord, MetricRecord, TagRecord


class JSONLSink(Sink, SupportsFlush):
    def __init__(self, path: str):
        self.path = Path(path)
        self._fh = None

    def on_open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", buffering=1, encoding="utf-8")

    def on_close(self):
        if self._fh:
            self._fh.flush()
            self._fh.close()
            self._fh = None

    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None:
        for r in batch:
            self._write(
                {
                    "kind": "metrics",
                    "run": r.run_id.value,
                    "step_name": r.step_name,
                    "step": r.step_value,
                    "ts": r.ts,
                    "metrics": r.metrics,
                }
            )

    def emit_config(self, cfg: ConfigRecord) -> None:
        self._write({"kind": "config", "run": cfg.run_id.value, "ts": cfg.ts, "config": cfg.config})

    def emit_tags(self, tags: TagRecord) -> None:
        self._write({"kind": "tags", "run": tags.run_id.value, "ts": tags.ts, "tags": tags.tags})

    def _write(self, obj):
        assert self._fh is not None, "JSONLSink file not opened"
        self._fh.write(json.dumps(obj) + "\n")

    def flush(self) -> None:
        if self._fh:
            self._fh.flush()
