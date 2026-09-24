---
name: ml-project
description: Guidelines for ML projects. Use when training or evaluating models, building ML pipelines, running experiments, or working with datasets/parquet files and CatBoost/PyTorch/Polars code.
---

# ML Project Guidelines

## Philosophy

- **Validation is king** - always define clear train/val/test splits before training
- **Error analysis is queen** - understand failures, not just metrics
- **No mocks** - test with real data and objects
- **Raw over abstraction** - YAML configs, tensorboard, raw plots. No MLflow/W&B complexity
- **Hyperparam tuning is overrated** - usually low-hanging fruit elsewhere: features, data, target. Highly tuned models are brittle
- **Simple ensembles only** - if needed, blend linear model + CatBoost. No stacking towers
- **Too good = suspicious** - great results warrant paranoid leakage checks before celebration
- **Apples to apples** - always compare full baseline vs full experiment on the same data. No cherrypicked subsamples
- **Hypotheses need origins** - every experiment starts with "why". No random fishing expeditions
- **No hardcoded paths** - paths live in config

## Default Workflow

1. Inspect the project first: data shape, target definition, existing metrics, existing split, and current baseline.
2. Define or verify train/val/test before training anything. For time-series, use chronological splits by default.
3. Write the hypothesis before the experiment: what should improve, why, and which metric should move.
4. Run the simplest baseline that answers the question, then compare the full baseline and full experiment on identical splits.
5. Save the frozen config, metrics, predictions, model artifact, and any feature importance or plots into the run directory.
6. Do error analysis before declaring success: inspect false positives/negatives, high-loss examples, calibration, slices, and date/entity drift.
7. If results look very strong, assume leakage until checked.
8. Write a short memo with hypothesis, setup, results, conclusion, and next step.

Proportionality: throwaway exploration (quick plots, sanity checks) needs no run dir and no memo — do it in `temp/` or `experimental/`. The full hypothesis → frozen config → run dir → memo ceremony is for tracked experiments. The moment you are about to compare results or make a decision on them, it is a tracked experiment — promote it.

### When it goes wrong

- A failed hypothesis still gets a memo with the negative result. Most common outcome, most commonly unwritten.
- Diverging or NaN loss: check data and targets before touching the learning rate.
- Baseline cannot be reproduced: stop. Every comparison is blocked until it can.

## Stack

| Purpose | Tool |
|---------|------|
| Tabular ML | CatBoost |
| Deep Learning | PyTorch |
| DataFrames | Polars, never pandas |
| Logging | coloredlogs + `logging.getLogger(__name__)`, never print |
| CLI | fire, e.g. `fire.Fire({"train": train, "evaluate": evaluate})` |
| Config | dataclass + YAML |
| Plots | matplotlib, raw |
| Tracking | tensorboard + `memos/` |
| Performance | Rust via maturin, when needed |

## Project Structure

```
project/
├── core/               # metrics, validation, shared utils
├── pipeline/           # production baseline code
├── experimental/       # exp_name/ subdirs for throwaway code
│   └── exp_name/       # migrate to pipeline/ if works
├── features/           # feature engineering modules
├── data/
│   ├── raw/            # immutable source data
│   └── processed/      # transformed data
├── memos/              # experiment results, markdown
├── configs/            # YAML job configs
├── experiments/        # timestamped run outputs
├── tests/              # pytest tests
└── temp/               # validation scripts, clean up after
```

## Leakage Checks

Always verify:

- Features are available at prediction time
- Aggregations and normalizers are fit on train only
- No target, future, backtest, or execution columns enter features
- Entity duplicates do not cross splits unless that is intentional
- Time-series tasks use chronological splits, and embargo gaps where labels overlap windows
- A too-good metric is reproduced on a fresh holdout before it is trusted

## References

- `references/config-and-tracking.md` — open when setting up configs, run dirs, memos, logging, or reproducibility.
- `references/data-and-validation.md` — open when writing splits, feature selection, or data loading code.
- `references/modeling.md` — open when writing CatBoost or PyTorch training code.
