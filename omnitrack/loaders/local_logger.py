from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd


class LocalLoggerLoader:
    """
    Loader for omnitrack LocalLogger data with structured analysis capabilities.

    This class provides seamless conversion from omnitrack's structured JSON format
    to pandas DataFrames and various data structures for immediate analysis,
    visualization, and table generation.
    """

    def __init__(self, json_path: Union[str, Path]):
        """
        Initialize loader with path to LocalLogger JSON file.

        Args:
            json_path: Path to the LocalLogger JSON file
        """
        self.json_path = Path(json_path)
        self._data: Optional[Dict[str, Any]] = None
        self._load_data()

    def _load_data(self) -> None:
        """Load the JSON data from file."""
        if not self.json_path.exists():
            raise FileNotFoundError(f"LocalLogger file not found: {self.json_path}")

        with self.json_path.open("r", encoding="utf-8") as f:
            self._data = json.load(f)

    @property
    def run_id(self) -> str:
        """Get the run ID."""
        return self._data["run_id"]

    @property
    def config(self) -> Dict[str, Any]:
        """Get the configuration."""
        return self._data["config"]

    @property
    def tags(self) -> Dict[str, str]:
        """Get the tags."""
        return self._data["tags"]

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the metadata (timing, step counts, etc.)."""
        return self._data["metadata"]

    def get_metrics_df(self, step_name: str) -> pd.DataFrame:
        """
        Get metrics for a specific step as a pandas DataFrame.

        Args:
            step_name: Name of the step (e.g., 'epoch', 'batch', 'validation')

        Returns:
            DataFrame with columns: step, metric_name_1, metric_name_2, ...
        """
        if step_name not in self._data["metrics"]:
            raise KeyError(f"Step '{step_name}' not found in data")

        step_data = self._data["metrics"][step_name]
        steps = step_data["steps"]
        metrics = step_data["metrics"]

        # Create DataFrame with steps as index
        df_data = {"step": steps}
        df_data.update(metrics)

        return pd.DataFrame(df_data)

    def get_all_metrics_df(self) -> pd.DataFrame:
        """
        Get all metrics as a single DataFrame with step_name as a column.

        Returns:
            DataFrame with columns: step_name, step, metric_name_1, metric_name_2, ...
        """
        all_data = []

        for step_name, step_data in self._data["metrics"].items():
            steps = step_data["steps"]
            metrics = step_data["metrics"]

            # Create DataFrame for this step
            df_data = {"step_name": [step_name] * len(steps), "step": steps}
            df_data.update(metrics)

            all_data.append(pd.DataFrame(df_data))

        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    def get_plot_data(self, step_name: str, x_metric: str, y_metrics: List[str]) -> Dict[str, Any]:
        """
        Convert metrics to structured plot data format.

        Args:
            step_name: Name of the step to plot
            x_metric: Metric to use as x-axis (usually 'step')
            y_metrics: List of metrics to plot on y-axis

        Returns:
            Dictionary with structured plot data
        """
        df = self.get_metrics_df(step_name)

        if x_metric not in df.columns:
            raise KeyError(f"X metric '{x_metric}' not found in step '{step_name}'")

        # Create structured plot data
        plot_data = {}

        for y_metric in y_metrics:
            if y_metric not in df.columns:
                raise KeyError(f"Y metric '{y_metric}' not found in step '{step_name}'")

            plot_data[y_metric] = {"x": df[x_metric].tolist(), "y": df[y_metric].tolist()}

        return plot_data

    def get_table_data(
        self, step_name: str, metrics: List[str], groupby: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Convert metrics to structured table data format.

        Args:
            step_name: Name of the step to use for table
            metrics: List of metrics to include in table
            groupby: Optional column to group by (e.g., 'step' for step-wise aggregation)

        Returns:
            DataFrame ready for table generation
        """
        df = self.get_metrics_df(step_name)

        # Filter to requested metrics
        available_metrics = [m for m in metrics if m in df.columns]
        if not available_metrics:
            raise KeyError(f"None of the requested metrics found in step '{step_name}'")

        # Select columns
        table_df = df[["step"] + available_metrics].copy()

        # Group by if requested
        if groupby and groupby in table_df.columns:
            # Aggregate by the groupby column
            agg_dict = {col: "mean" for col in available_metrics}
            table_df = table_df.groupby(groupby).agg(agg_dict).reset_index()

        return table_df

    def get_comparison_data(
        self, step_name: str, x_metric: str, y_metric: str, groupby: str = "step"
    ) -> Dict[str, Any]:
        """
        Get data formatted for comparison plots (multiple lines, etc.).

        Args:
            step_name: Name of the step to plot
            x_metric: Metric to use as x-axis
            y_metric: Metric to use as y-axis
            groupby: Column to group by for comparison

        Returns:
            Dictionary with 'x', 'y', and 'group' keys for comparison plots
        """
        df = self.get_metrics_df(step_name)

        if x_metric not in df.columns or y_metric not in df.columns:
            raise KeyError(f"Metrics not found in step '{step_name}'")

        return {
            "x": df[x_metric].tolist(),
            "y": df[y_metric].tolist(),
            "group": df[groupby].tolist() if groupby in df.columns else None,
        }

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for all metrics across all steps.

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "run_id": self.run_id,
            "config": self.config,
            "tags": self.tags,
            "metadata": self.metadata,
            "metrics_summary": {},
        }

        for step_name, step_data in self._data["metrics"].items():
            metrics = step_data["metrics"]
            step_summary = {}

            for metric_name, values in metrics.items():
                if values:  # Check if values exist
                    step_summary[metric_name] = {
                        "count": len(values),
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "final": values[-1] if values else None,
                    }

            summary["metrics_summary"][step_name] = step_summary

        return summary

    def get_analysis_data(self, step_name: str, plot_type: str = "line") -> Dict[str, Any]:
        """
        Get data ready for immediate analysis and visualization.

        Args:
            step_name: Name of the step to prepare
            plot_type: Type of plot ('line', 'bar', 'scatter', etc.)

        Returns:
            Dictionary ready for analysis and plotting
        """
        df = self.get_metrics_df(step_name)

        # Common analysis data format
        analysis_data = {
            "data": df,
            "x_key": "step",
            "y_key": [col for col in df.columns if col != "step"],
            "run_info": {"run_id": self.run_id, "config": self.config, "tags": self.tags},
        }

        return analysis_data
