"""Generate deterministic trajectory-level measurements."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .ca import simulate
from .config import CONFIG, ExperimentConfig
from .features import extract_features
from .rules import format_rule, sample_rules


def generate_dataset(config: ExperimentConfig = CONFIG) -> pd.DataFrame:
    rows: list[dict] = []
    rules = sample_rules(config.n_rules, config.random_seed)
    for rule_index, bits in enumerate(rules):
        rule = format_rule(bits)
        for run_index in range(config.runs_per_rule):
            density = config.initial_densities[run_index % len(config.initial_densities)]
            seed = config.random_seed + rule_index * 100 + run_index
            trajectory = simulate(
                bits,
                grid_size=config.grid_size,
                initial_density=density,
                steps=config.steps,
                seed=seed,
            )
            row = {
                "rule_index": rule_index,
                "run": run_index,
                "seed": seed,
                "initial_density": density,
                "rule": rule,
                **{f"B{i}": int(bits[i]) for i in range(9)},
                **{f"S{i}": int(bits[9 + i]) for i in range(9)},
                **extract_features(trajectory),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def write_dataset(path: str | Path, config: ExperimentConfig = CONFIG) -> pd.DataFrame:
    frame = generate_dataset(config)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return frame


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    data = write_dataset(root / "data" / "simulation_features.csv")
    print(f"Wrote {len(data)} trajectories across {data['rule'].nunique()} rules")

