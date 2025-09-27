# Omnitrack

[![PyPI version](https://badge.fury.io/py/omnitrack.svg)](https://badge.fury.io/py/omnitrack)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Unified logging and experiment tracking for research workflows**

Omnitrack is a lightweight, flexible experiment tracking library that provides a unified interface for logging metrics, configurations, and tags across multiple backends. Whether you're training machine learning models, running scientific experiments, or building research prototypes, Omnitrack helps you track everything in one place.

## ✨ Features

- **🎯 Unified API**: Single interface for all your logging needs
- **🔄 Multiple Backends**: Console, JSONL, Weights & Biases support
- **📊 Rich Console**: Beautiful real-time progress tracking with system stats
- **🏷️ Flexible Step Management**: Support for multiple step types (epochs, batches, etc.)
- **🔧 Easy Integration**: Drop-in replacement for existing logging
- **⚡ Lightweight**: Minimal dependencies, fast execution
- **🎨 Smart Namespacing**: Automatic metric separation by step type

## 🚀 Quick Start

### Installation

```bash
pip install omnitrack
```

### Basic Usage

```python
from omnitrack import LogSession, record, step, push_config, set_tags
from omnitrack.sinks.console import ConsoleSink
from omnitrack.sinks.wandb import WandbSink

# Set up your experiment
with LogSession(sinks=[ConsoleSink(), WandbSink(project="my-project")]):
    # Log configuration
    push_config(lr=1e-3, batch_size=64, model="transformer")
    set_tags(env="production", version="v1.0")
    
    # Training loop
    for epoch in range(10):
        step(name="epoch")
        
        for batch in range(100):
            step(name="batch")
            
            # Log metrics
            loss = compute_loss()
            accuracy = compute_accuracy()
            record(step_name="batch", loss=loss, acc=accuracy)
        
        # Log epoch summary
        record(step_name="epoch", loss=epoch_loss, acc=epoch_acc)
```

## 📖 Core Concepts

### Sessions and Sinks

Omnitrack uses a **session-based** approach where you define sinks (backends) that receive your logged data:

```python
from omnitrack import LogSession
from omnitrack.sinks.console import ConsoleSink
from omnitrack.sinks.jsonl import LocalLogger
from omnitrack.sinks.wandb import WandbSink

# Multiple sinks for different purposes
with LogSession(sinks=[
    ConsoleSink(),                    # Real-time console output
    LocalLogger("logs/experiment.jsonl"), # Structured logging
    WandbSink(project="my-project")   # Weights & Biases tracking
]):
    # Your experiment code here
    pass
```

### Step Management

Omnitrack supports **multiple step types** with automatic namespacing:

```python
# Different step types for different granularities
step(name="epoch")     # High-level training progress
step(name="batch")     # Fine-grained training steps
step(name="validation") # Validation steps

# Log metrics for specific step types
record(step_name="batch", loss=0.5, accuracy=0.8)
record(step_name="epoch", loss=0.4, accuracy=0.85)
```

This creates separate metrics in your backends:
- `batch/loss`, `batch/accuracy` 
- `epoch/loss`, `epoch/accuracy`

### Metric Filtering

Control which sinks receive which metrics:

```python
# Only send to specific sinks
record(
    step_name="batch", 
    loss=loss, 
    include=["WandbSink"]  # Only send to Weights & Biases
)

# Exclude noisy metrics from console
record(
    step_name="batch", 
    loss=loss, 
    exclude=["ConsoleSink"]  # Don't spam console
)
```

## 🎨 Available Sinks

### ConsoleSink
Beautiful real-time console output with progress bars and system stats.

```python
from omnitrack.sinks.console import ConsoleSink

# Basic usage
ConsoleSink()

# Customized
ConsoleSink(title="My Experiment", show_system=True)
```

**Features:**
- Real-time progress tracking
- System resource monitoring (CPU, RAM, GPU)
- Color-coded metrics
- Log panel for messages

### LocalLogger
Structured local logging that maintains hierarchical data for easy analysis.

```python
from omnitrack.sinks.jsonl import LocalLogger

LocalLogger("logs/experiment.json")
```

**Features:**
- **Structured data format**: Metrics grouped by step type with lists of values
- **Config accumulation**: All configs merged into a single tree structure  
- **Tag accumulation**: All tags merged into a single structure
- **Pandas-friendly**: Easy to load back into pandas for analysis
- **Single JSON file**: Complete run data in one structured file
- **Metadata tracking**: Run duration, step counts, and timing info
- **Analysis integration**: Direct conversion to pandas DataFrames and structured data formats

**Example LocalLogger Output:**
```json
{
  "run_id": "abc123",
  "config": {
    "lr": 0.001,
    "batch_size": 64,
    "model": {"name": "transformer", "layers": 6}
  },
  "tags": {"env": "demo", "version": "v1.0"},
  "metrics": {
    "batch": {
      "steps": [0, 1, 2, 0, 1, 2],
      "metrics": {
        "loss": [0.5, 0.25, 0.167, 0.25, 0.2, 0.167],
        "acc": [0.5, 0.75, 0.833, 0.75, 0.8, 0.833]
      }
    },
    "epoch": {
      "steps": [0, 1],
      "metrics": {
        "loss": [0.5, 0.4],
        "acc": [0.5, 0.6]
      }
    }
  },
  "metadata": {
    "start_time": 1234567890.123,
    "end_time": 1234567890.456,
    "total_steps": {"batch": 2, "epoch": 1}
  }
}
```

### WandbSink
Integration with Weights & Biases for experiment tracking.

```python
from omnitrack.sinks.wandb import WandbSink

WandbSink(project="my-project", entity="my-team")
```

**Features:**
- Automatic metric namespacing by step type
- Proper step relationships
- Config and tag tracking
- Rich visualizations

## 📊 Data Analysis Integration

Omnitrack provides seamless data loading and analysis capabilities:

```python
from omnitrack.loaders import LocalLoggerLoader
import pandas as pd

# Load your experiment data
loader = LocalLoggerLoader("logs/experiment.json")

# Get structured data
plot_data = loader.get_plot_data("epoch", "step", ["loss", "acc"])
table_data = loader.get_table_data("epoch", ["loss", "acc"])

# Direct pandas analysis
df = loader.get_metrics_df("epoch")
print(df.describe())

# Custom analysis
summary = loader.get_summary_stats()
print(f"Final loss: {summary['metrics_summary']['epoch']['loss']['final']}")
```

**Key Benefits:**
- **Zero boilerplate**: Direct conversion to pandas DataFrames
- **Structured analysis**: Clean data formats for any visualization library
- **Flexible output**: Works with matplotlib, seaborn, plotly, or any plotting library
- **Complete workflow**: From experiment tracking to analysis

## 🔧 Advanced Usage

### Custom Step Patterns

Omnitrack excels at complex step patterns:

```python
# Alternating step types
for outer in range(3):
    step(name="outer")
    
    # First phase
    for inner in range(10):
        step(name="phase_a")
        record(step_name="phase_a", loss=compute_loss_a())
    
    # Second phase  
    for inner in range(10):
        step(name="phase_b")
        record(step_name="phase_b", loss=compute_loss_b())
    
    # Summary
    record(step_name="outer", loss_a=avg_loss_a, loss_b=avg_loss_b)
```

### Selective Pushing

Control when metrics are sent to sinks:

```python
# Push only epoch metrics immediately
push(step_names=["epoch"])

# Push everything at the end
push()  # No filter = push all
```

### Decorator Support

Use the `@autolog` decorator for automatic metric logging:

```python
from omnitrack.utils.decorators import autolog

@autolog
def train_step():
    loss = compute_loss()
    return loss, {"loss": loss, "accuracy": 0.8}  # Auto-logged

@autolog  
def validation():
    return {"val_loss": 0.3, "val_acc": 0.9}  # Just metrics
```

## 📊 Example: Complete Training Loop

```python
from omnitrack import LogSession, record, step, push_config, set_tags
from omnitrack.sinks.console import ConsoleSink
from omnitrack.sinks.wandb import WandbSink

def train_model():
    with LogSession(sinks=[
        ConsoleSink(title="Model Training"),
        WandbSink(project="my-ml-project")
    ]):
        # Configuration
        config = {
            "lr": 1e-3,
            "batch_size": 64,
            "model": {"name": "transformer", "layers": 6}
        }
        push_config(**config)
        set_tags(env="production", dataset="imagenet")
        
        # Training
        for epoch in range(10):
            step(name="epoch")
            epoch_loss = 0
            
            for batch in range(100):
                step(name="batch")
                
                # Compute metrics
                loss = 1.0 / (1 + epoch * 100 + batch + 1)
                accuracy = 1 - loss
                
                # Log batch metrics (exclude console to reduce noise)
                record(
                    step_name="batch", 
                    loss=loss, 
                    accuracy=accuracy,
                    exclude=["ConsoleSink"]
                )
                epoch_loss += loss
            
            # Log epoch summary
            record(
                step_name="epoch",
                loss=epoch_loss / 100,
                accuracy=1 - epoch_loss / 100
            )
            
            # Push epoch metrics immediately
            push(step_names=["epoch"])

if __name__ == "__main__":
    train_model()
```

## 🛠️ Development

### Installation from Source

```bash
git clone https://github.com/lars-quaedvlieg/omnitrack.git
cd omnitrack
pip install -e .
```

### Running Examples

```bash
# Standard training demo
python examples/demo.py demo --project my-wandb-project

# Alternating step pattern demo  
python examples/demo.py demo --project my-wandb-project --mode alternating
```

### Code Quality

```bash
# Format and lint
make fix-style
make lint
```

## 🤝 Contributing

We welcome contributions! Please see our [GitHub repository](https://github.com/lars-quaedvlieg/omnitrack) for:

- Issue tracking
- Pull request guidelines  
- Development setup
- Code of conduct

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful console output
- Integrates with [Weights & Biases](https://wandb.ai) for experiment tracking
- Inspired by the need for flexible, lightweight experiment tracking in research workflows

---

**Made with ❤️ for the research community**