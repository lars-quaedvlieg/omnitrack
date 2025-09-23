import time
from typing import Dict, Iterable

import psutil
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text
from rich.tree import Tree

from ..core.interfaces import Sink, SupportsFlush
from ..core.types import ConfigRecord, MetricRecord, TagRecord
from ..utils.helpers import flatten_dict

try:
    import torch

    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


class ItersPerSecColumn(ProgressColumn):
    """Renders iterations per second."""

    def render(self, task) -> Text:
        if task.start_time is None or task.completed is None:
            return Text("- it/s", style="blue")
        elapsed = max(time.monotonic() - task.start_time, 1e-8)
        rate = task.completed / elapsed
        return Text(f"{rate:.2f} it/s", style="blue")


class SystemStats:
    """Collects and renders system stats into a rich Panel."""

    def render(self) -> Panel:
        cpu_percent = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        total_mem = mem.total / (1024**3)
        used_mem = mem.used / (1024**3)

        tree = Tree("[yellow]System Stats[/yellow]", guide_style="bold yellow")
        tree.add(f"[yellow]CPU[/yellow]: {cpu_percent:.1f}%")
        tree.add(f"[yellow]RAM[/yellow]: {used_mem:.1f}/{total_mem:.1f} GB")

        if _HAS_TORCH and torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                mem_alloc = torch.cuda.memory_allocated(i) / (1024**3)
                mem_total = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                tree.add(
                    f"[yellow]GPU {i} ({gpu_name})[/yellow]: {mem_alloc:.1f}/{mem_total:.1f} GB"
                )

        return Panel.fit(tree, border_style="yellow", title="System Stats")


class ConsoleSink(Sink, SupportsFlush):
    def __init__(self, title: str = "Omnitrack Console", show_system: bool = True):
        self.console = Console()
        self.title = title
        self.show_system = show_system
        self.system_stats = SystemStats()

        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("{task.fields[metrics]}"),
            ItersPerSecColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

        self.tasks: Dict[str, TaskID] = {}
        self._live: Live | None = None
        self._layout: Layout | None = None
        self._logs: list[str] = []
        self.started = False

    def _make_layout(self) -> Layout:
        """System stats panel above progress, logs panel below."""
        layout = Layout()

        main = Layout(name="main")
        if self.show_system:
            main.split_column(
                Layout(self.system_stats.render(), name="system"),
                Layout(self.progress, name="progress"),
            )
        else:
            main.update(self.progress)

        layout.split_column(
            main,
            Layout(self._render_logs(), name="logs", size=10),
        )
        return layout

    def _render_logs(self) -> Panel:
        if not self._logs:
            return Panel(Text("No logs yet", style="dim"), title="Logs", border_style="blue")
        text = Text("\n".join(self._logs[-20:]))  # keep last 20 lines visible
        return Panel(text, title="Logs", border_style="blue")

    def log(self, message: str):
        """Public API for adding log messages to the logs panel."""
        self._logs.append(message)
        if self._layout:
            self._layout["logs"].update(self._render_logs())
        if self._live:
            self._live.refresh()

    def on_open(self):
        if not self.started:
            banner = Panel.fit(
                f"[bold cyan]{self.title}[/bold cyan]",
                border_style="cyan",
                title="🚀 Run Started",
                subtitle="Logging active",
            )
            self.console.print(banner)

            self._layout = self._make_layout()
            # ✅ No auto refresh, we refresh manually
            self._live = Live(self._layout, console=self.console, refresh_per_second=1e-9)
            self._live.start()
            self.progress.start()
            self.started = True

    def on_close(self):
        if self.started:
            self.progress.stop()
            if self._live:
                self._live.stop()
            self.console.print(Panel.fit("✅ [green]Run finished[/green]", border_style="green"))
            self.started = False

    def emit_metrics(self, batch: Iterable[MetricRecord]) -> None:
        for r in batch:
            payload = flatten_dict(r.metrics)

            if r.step_name not in self.tasks:
                task_id = self.progress.add_task(f"{r.step_name}", total=None, metrics="")
                self.tasks[r.step_name] = task_id
                self.progress.start_task(task_id)

            task_id = self.tasks[r.step_name]
            if r.step_value is not None:
                self.progress.update(task_id, completed=r.step_value + 1)

            metrics_str = " ".join(self._style_metric(k, v) for k, v in payload.items())
            self.progress.update(task_id, metrics=metrics_str)

        if self.show_system and self._layout:
            self._layout["system"].update(self.system_stats.render())

        if self._live:
            self._live.refresh()

    def emit_config(self, cfg: ConfigRecord) -> None:
        def _print_dict(d: dict, tree: Tree):
            for k, v in d.items():
                if isinstance(v, dict):
                    branch = tree.add(f"[green]{k}[/green]")
                    _print_dict(v, branch)
                else:
                    tree.add(f"[green]{k}[/green]: {v}")

        root = Tree("[green]Config[/green]", guide_style="bold green")
        _print_dict(cfg.config, root)
        self.console.print(Panel(root, title="Config", border_style="green"))

    def emit_tags(self, tags: TagRecord) -> None:
        def _print_dict(d: dict, tree: Tree):
            for k, v in d.items():
                tree.add(f"[magenta]{k}[/magenta]: {v}")

        root = Tree("[magenta]Tags[/magenta]", guide_style="bold magenta")
        _print_dict(tags.tags, root)
        self.console.print(Panel(root, title="Tags", border_style="magenta"))

    def flush(self) -> None:
        self.progress.refresh()
        if self.show_system and self._layout:
            self._layout["system"].update(self.system_stats.render())
        if self._live:
            self._live.refresh()

    def _style_metric(self, key, value) -> str:
        if isinstance(value, (int, float)):
            if "loss" in key:
                return f"[red]{key}={value:.4f}[/red]"
            if "acc" in key:
                return f"[green]{key}={value:.4f}[/green]"
            if "lr" in key:
                return f"[yellow]{key}={value:.4e}[/yellow]"
            return f"{key}={value:.4f}"
        return f"{key}={value}"
