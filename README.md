# Omnitrack 🚀

Unified logging and experiment tracking for ML research.  
Log once → sync everywhere (console, JSONL, W&B, …).

## Features
- 📊 Multi-sink logging (`ConsoleSink`, `JSONLSink`, `WandbSink`)
- 🌲 Hierarchical config & tags
- 🚀 Beautiful Rich-based console
- 🔌 Extensible sink interface
- ⚡ Efficient: batch logging, manual refresh

## Quickstart

```bash
pip install omnitrack
```

```python
from omnitrack import LogSession, record, step, push_config, set_tags
from omnitrack.sinks.console import ConsoleSink

with LogSession(sinks=[ConsoleSink()]):
    push_config({"lr": 1e-3, "batch_size": 64})
    set_tags(env="demo")

    for e in range(3):
        step("epoch")
        for b in range(10):
            step("batch")
            record(step_name="batch", loss=0.1, acc=0.9)
```

## Demo

Run the built-in demo:

```bash
omnitrack demo --jsonl logs/demo.jsonl
```