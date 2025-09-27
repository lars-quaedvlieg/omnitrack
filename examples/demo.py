import argparse
import os
import time

from omnitrack import LogSession, push, push_config, record, set_tags, step
from omnitrack.sinks.console import ConsoleSink
from omnitrack.sinks.jsonl import JSONLSink
from omnitrack.sinks.wandb import WandbSink


def run_demo(jsonl_path: str, wandb_project: str | None, mode: str = "standard"):
    sinks = [ConsoleSink(), JSONLSink(jsonl_path)]
    if wandb_project and WandbSink is not None:
        # silence wandb logs
        os.environ["WANDB_SILENT"] = "true"
        sinks.append(WandbSink(project=wandb_project))

    with LogSession(sinks=sinks):
        cfg = {
            "lr": 1e-3,
            "batch_size": 64,
            "model": {"name": "toy-net", "hidden_size": 128, "num_layers": 2},
            "demo_mode": mode,
        }
        push_config(config=cfg)
        set_tags(env="local", demo="true")
        push()  # Push initial config and tags

        # demo logs panel
        if isinstance(sinks[0], ConsoleSink):
            sinks[0].log(f"🚀 Starting training loop in {mode} mode…")

        if mode == "standard":
            run_standard_training(sinks)
        elif mode == "alternating":
            run_alternating_training(sinks)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        print("Done")


def run_standard_training(sinks):
    """Standard training loop: epochs with batches inside"""
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

            # Demo: exclude console sink for batch metrics (too noisy)
            record(step_name="batch", loss=loss, acc=acc, exclude=["JSONLSink"])
            mean_loss += loss
            mean_acc += acc
            time.sleep(0.05)

        # Demo: include only specific sinks for epoch summaries
        record(
            step_name="epoch",
            loss=mean_loss / num_batches,
            acc=mean_acc / num_batches,
            include=["JSONLSink", "WandbSink"],  # Show epoch summaries in console and JSONL
        )
        push(step_names=["epoch"])


def run_alternating_training(sinks):
    """Alternating training loop: two different step types that alternate"""
    num_outer = 3
    num_inner = 10  # Each inner loop will have 10 iterations

    for outer in range(num_outer):
        step(name="outer")
        outer_loss_a = outer_acc_a = 0.0
        outer_loss_b = outer_acc_b = 0.0

        # First inner loop - step_a
        for inner in range(num_inner):
            step(name="step_a")

            # global step ensures smooth curve across outer loops
            global_step = outer * (num_inner * 2) + inner
            loss = 1.0 / (1 + global_step + 1)
            acc = 1 - loss

            # Log step_a metrics
            record(step_name="step_a", loss=loss, acc=acc, exclude=["JSONLSink"])
            outer_loss_a += loss
            outer_acc_a += acc
            time.sleep(0.05)

        # Second inner loop - step_b
        for inner in range(num_inner):
            step(name="step_b")

            # global step continues from step_a
            global_step = outer * (num_inner * 2) + num_inner + inner
            loss = 1.0 / (1 + global_step + 1)
            acc = 1 - loss

            # Log step_b metrics
            record(step_name="step_b", loss=loss, acc=acc, exclude=["JSONLSink"])
            outer_loss_b += loss
            outer_acc_b += acc
            time.sleep(0.05)

        # Log outer summaries for both step types
        record(
            step_name="outer",
            loss_a=outer_loss_a / num_inner,
            acc_a=outer_acc_a / num_inner,
            loss_b=outer_loss_b / num_inner,
            acc_b=outer_acc_b / num_inner,
            include=["JSONLSink", "WandbSink"],
        )
        push(step_names=["outer"])


def main():
    p = argparse.ArgumentParser("omnitrack")
    sub = p.add_subparsers(dest="cmd")

    demo = sub.add_parser("demo", help="Run demo training loop")
    demo.add_argument("--jsonl", default="logs/demo.jsonl")
    demo.add_argument("--project", default=None)
    demo.add_argument(
        "--mode",
        choices=["standard", "alternating"],
        default="standard",
        help="Training mode: standard (epochs/batches) or alternating (outer/inner)",
    )

    args = p.parse_args()
    if args.cmd == "demo":
        run_demo(jsonl_path=args.jsonl, wandb_project=args.project, mode=args.mode)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
