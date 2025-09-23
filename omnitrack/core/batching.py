from __future__ import annotations

from collections import deque
from typing import Deque, Generic, List, TypeVar

T = TypeVar("T")


class Batcher(Generic[T]):
    """Simple size/time-based batching; caller drives 'should_flush'."""

    def __init__(self, max_items: int = 256):
        self.max_items = max_items
        self._buf: Deque[T] = deque()

    def add(self, item: T) -> bool:
        self._buf.append(item)
        return len(self._buf) >= self.max_items

    def drain(self) -> List[T]:
        out = list(self._buf)
        self._buf.clear()
        return out

    def __len__(self) -> int:
        return len(self._buf)
