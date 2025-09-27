#!/usr/bin/env python3
"""
Demo showing the new LocalLogger structured output format.
"""

import json

from omnitrack import LogSession, push_config, record, set_tags, step
from omnitrack.sinks.jsonl import LocalLogger


def demo_local_logger():
    """Demonstrate the structured output of LocalLogger."""

    with LogSession(sinks=[LocalLogger("logs/structured_demo.json")]):
        # Configuration
        push_config(
            config={"lr": 1e-3, "batch_size": 64, "model": {"name": "transformer", "layers": 6}}
        )
        set_tags(env="demo", version="v1.0")

        # Training loop
        for epoch in range(2):
            step(name="epoch")

            for batch in range(3):  # Just 3 batches for demo
                step(name="batch")

                # Simulate metrics
                loss = 1.0 / (1 + epoch * 3 + batch + 1)
                acc = 1 - loss

                record(step_name="batch", loss=loss, acc=acc)

            # Epoch summary
            record(step_name="epoch", loss=0.5 - epoch * 0.1, acc=0.5 + epoch * 0.1)

    # Show the structured output
    print("LocalLogger output structure:")
    print("=" * 50)

    with open("logs/structured_demo.json", "r") as f:
        data = json.load(f)
        print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    demo_local_logger()
