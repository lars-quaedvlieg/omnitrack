from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RunId:
    value: str

    @staticmethod
    def new() -> "RunId":
        return RunId(str(uuid.uuid4()))


@dataclass
class MetricRecord:
    run_id: RunId
    step_name: str  # e.g. "batch", "epoch", "global"
    step_value: Optional[int]  # may be None for unstepped logs
    metrics: Dict[str, Any]
    ts: float = field(default_factory=time.time)


@dataclass
class ConfigRecord:
    run_id: RunId
    config: Dict[str, Any]
    ts: float = field(default_factory=time.time)


@dataclass
class TagRecord:
    run_id: RunId
    tags: Dict[str, str]
    ts: float = field(default_factory=time.time)


@dataclass
class StepRecord:
    run_id: RunId
    step_name: str
    step_value: int
    ts: float = field(default_factory=time.time)
