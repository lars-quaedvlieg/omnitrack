from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from .types import ConfigRecord, MetricRecord, TagRecord


class Sink(ABC):
    """Synchronous sink interface (thread-safe expected)."""

    def on_open(self): ...
    def on_close(self): ...

    @abstractmethod
    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None: ...
    def emit_config(self, cfg: ConfigRecord) -> None: ...
    def emit_tags(self, tags: TagRecord) -> None: ...


class SupportsFlush(ABC):
    def flush(self) -> None: ...
