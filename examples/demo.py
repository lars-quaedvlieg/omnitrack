import argparse
import os
import time

from omnitrack import LogSession, push_config, record, set_tags, step
from omnitrack.sinks.console import ConsoleSink
from omnitrack.sinks.jsonl import JSONLSink
from omnitrack.sinks.wandb import WandbSink


def run_demo(jsonl_path: str, wandb_project: str | None):
    sinks = [ConsoleSink(), JSONLSink(jsonl_path)]
    if wandb_project and WandbSink is not None:
        # silence wandb logs
        os.environ["WANDB_SILENT"] = "true"
        sinks.append(WandbSink(project=wandb_project))

    with LogSession(sinks=sinks, batch_size=8, flush_interval_s=1.0):
        cfg = {
            "lr": 1e-3,
            "batch_size": 64,
            "model": {"name": "toy-net", "hidden_size": 128, "num_layers": 2},
        }
        push_config(config=cfg)
        set_tags(env="local", demo="true")

        # demo logs panel
        if isinstance(sinks[0], ConsoleSink):
            sinks[0].log("🚀 Starting training loop…")

        num_epochs = 3
        num_batches = 50

        for e in range(num_epochs):
            step(name="epoch")
            mean_loss = mean_acc = 0.0

            for b in range(num_batches):
                step(name="batch")

                # global step ensures smooth curve across epochs
                global_step = e * num_batches + b
                loss = 1.0 / (1 + global_step + 1)
                acc = 1 - loss

                record(step_name="batch", loss=loss, acc=acc, exclude=[])
                mean_loss += loss
                mean_acc += acc
                time.sleep(0.05)

                # debug log every 25 batches
                if b % 25 == 0 and isinstance(sinks[0], ConsoleSink):
                    sinks[0].log(f"Processed {b} batches in epoch {e}")

            record(
                step_name="epoch",
                loss=mean_loss / num_batches,
                acc=mean_acc / num_batches,
                exclude=[],
            )

        if isinstance(sinks[0], ConsoleSink):
            sinks[0].log("✅ Training complete.")


def main():
    p = argparse.ArgumentParser("omnitrack")
    sub = p.add_subparsers(dest="cmd")

    demo = sub.add_parser("demo", help="Run demo training loop")
    demo.add_argument("--jsonl", default="logs/demo.jsonl")
    demo.add_argument("--project", default=None)

    args = p.parse_args()
    if args.cmd == "demo":
        run_demo(jsonl_path=args.jsonl, wandb_project=args.project)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
