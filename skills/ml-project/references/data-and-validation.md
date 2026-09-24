# Data & Validation Patterns

## Temporal Split

Default for time-series. No lookahead bias.

```python
import polars as pl


def temporal_split(
    df: pl.DataFrame,
    date_col: str,
    val_days: int = 3,
    test_days: int = 5,
    embargo_days: int = 0,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    if date_col not in df.columns:
        raise ValueError(f"Missing date column: {date_col}")
    if val_days <= 0 or test_days <= 0:
        raise ValueError("val_days and test_days must be positive")
    if embargo_days < 0:
        raise ValueError("embargo_days must be non-negative")

    date_expr = pl.col(date_col)
    if df.schema[date_col] != pl.Date:
        date_expr = date_expr.dt.date()

    with_dates = df.with_columns(date_expr.alias("_split_date"))
    unique_dates = (
        with_dates.select("_split_date")
        .unique()
        .sort("_split_date")
        .get_column("_split_date")
        .to_list()
    )

    required_days = val_days + test_days + 2 * embargo_days + 1
    if len(unique_dates) < required_days:
        raise ValueError(
            f"Need at least {required_days} unique dates, got {len(unique_dates)}"
        )

    val_end = -(test_days + embargo_days)
    val_start = val_end - val_days
    train_end = val_start - embargo_days

    train_dates = unique_dates[:train_end]
    val_dates = unique_dates[val_start:val_end]
    test_dates = unique_dates[-test_days:]

    train = with_dates.filter(pl.col("_split_date").is_in(train_dates)).drop("_split_date")
    val = with_dates.filter(pl.col("_split_date").is_in(val_dates)).drop("_split_date")
    test = with_dates.filter(pl.col("_split_date").is_in(test_dates)).drop("_split_date")

    return train, val, test
```

## Feature Column Filtering

Exclude leakage-prone columns by prefix and name. The values below are an
example (from a trading project) — adapt the prefixes and columns to whatever
is leakage-prone in *your* project.

```python
import polars as pl


EXCLUDED_PREFIXES = ("target_", "backtest_", "aux_", "exec_")  # example, adapt
EXCLUDED_COLS = {"timestamp", "date", "id"}


def get_feature_cols(df: pl.DataFrame) -> list[str]:
    return [
        col
        for col in df.columns
        if not any(col.startswith(prefix) for prefix in EXCLUDED_PREFIXES)
        and col not in EXCLUDED_COLS
    ]
```

## JSON + Parquet Pairs

```python
import json
from pathlib import Path

import polars as pl


slug = "train"
data_dir = Path("data")

with (data_dir / f"{slug}.json").open(encoding="utf-8") as f:
    metadata = json.load(f)

df = pl.read_parquet(data_dir / f"{slug}.parquet")
```

## Memory Optimization

```python
import polars as pl


float_cols = [name for name, dtype in df.schema.items() if dtype == pl.Float64]
df = df.with_columns([pl.col(col).cast(pl.Float32) for col in float_cols])
```
