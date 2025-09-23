from __future__ import annotations

import queue
import threading
import time
from typing import List, Optional

from .batching import Batcher
from .interfaces import Sink, SupportsFlush
from .types import ConfigRecord, MetricRecord, TagRecord


class Router:
    """
    Background worker that fans out records to all sinks, with batching.
    Thread-safe: front-end puts onto a queue; worker drains in background.
    """

    def __init__(self, sinks: List[Sink], batch_size: int, flush_interval_s: float):
        self.sinks = sinks
        self._q: "queue.Queue[MetricRecord|ConfigRecord|TagRecord|None]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._batch = Batcher[MetricRecord](max_items=batch_size)
        self.flush_interval_s = flush_interval_s
        self._last_flush = time.time()

    def start(self):
        for s in self.sinks:
            s.on_open()
        self._thread = threading.Thread(target=self._loop, name="omnitrack-router", daemon=True)
        self._thread.start()

    def stop(self):
        # signal + sentinel
        self._stop.set()
        self._q.put(None)
        if self._thread:
            self._thread.join()
        # final flush and close
        self._flush_metrics()
        for s in self.sinks:
            if isinstance(s, SupportsFlush):
                try:
                    s.flush()
                except Exception:
                    pass
            s.on_close()

    def submit_metrics(self, rec: MetricRecord):
        self._q.put(rec)

    def submit_config(self, rec: ConfigRecord):
        self._q.put(rec)

    def submit_tags(self, rec: TagRecord):
        self._q.put(rec)

    # Worker
    def _loop(self):
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=self.flush_interval_s)
            except queue.Empty:
                item = None

            now = time.time()
            timed_flush = (now - self._last_flush) >= self.flush_interval_s

            if item is None:
                # Either sentinel or timeout
                if timed_flush and len(self._batch) > 0:
                    self._flush_metrics()
                if self._stop.is_set():
                    break
                continue

            if isinstance(item, MetricRecord):
                should_flush = self._batch.add(item)
                if should_flush or timed_flush:
                    self._flush_metrics()
            elif isinstance(item, ConfigRecord):
                for s in self.sinks:
                    try:
                        s.emit_config(item)
                    except Exception:
                        pass
            else:  # TagRecord
                for s in self.sinks:
                    try:
                        s.emit_tags(item)
                    except Exception:
                        pass

    def _flush_metrics(self):
        batch = self._batch.drain()
        if not batch:
            self._last_flush = time.time()
            return
        for s in self.sinks:
            try:
                s.emit_metrics(batch)
            except Exception:
                pass
        self._last_flush = time.time()

    def _flush_metrics(self):
        batch = self._batch.drain()
        if not batch:
            self._last_flush = time.time()
            return
        for s in self.sinks:
            sink_name = type(s).__name__
            filtered = [r for r in batch if sink_name not in getattr(r, "_exclude", [])]
            if filtered:
                try:
                    s.emit_metrics(filtered)
                except Exception:
                    pass
        self._last_flush = time.time()
