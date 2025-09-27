from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from numbers import Number
from typing import Any, Dict, Optional, Union


# Base class for custom metric value types
class MetricValue:
    """
    Base class for custom metric value types.

    Users can inherit from this class to create their own metric value types
    that will be accepted by omnitrack's validation system.

    Example:
        class CustomMetric(MetricValue):
            def __init__(self, value: float, confidence: float):
                self.value = value
                self.confidence = confidence

            def __float__(self):
                return float(self.value)
    """

    pass


# Define valid metric types
ValidMetricTypes = Union[float, int, Number, MetricValue]


def _validate_metric_value(value: Any) -> None:
    """Validate that a metric value is of a supported type."""
    if not isinstance(value, (int, float, Number, MetricValue)):
        raise TypeError(
            f"Invalid metric value type: {type(value).__name__}. "
            f"Expected int, float, Number, or MetricValue subclass, got {type(value).__name__}"
        )


@dataclass
class MetricRecord:
    run_id: RunId
    step_name: str  # e.g. "batch", "epoch", "global"
    step_value: Optional[int]  # may be None for unstepped logs
    metrics: Dict[str, ValidMetricTypes]
    ts: float = field(default_factory=time.time)

    def __post_init__(self):
        """Validate metric values after initialization."""
        for _, value in self.metrics.items():
            _validate_metric_value(value)


@dataclass(frozen=True)
class RunId:
    value: str

    @staticmethod
    def new() -> "RunId":
        return RunId(str(uuid.uuid4()))


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
