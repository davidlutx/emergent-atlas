"""Targeted follow-up experiments and report figures.

This script complements the broad 100-rule survey with repeated Conway/HighLife
comparisons and visual case studies of learned cluster representatives.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .ca import simulate
from .config import CONFIG
from .features import extract_features


TARGET_RULES = {
    "Conway Life": "B3/S23",
    "HighLife": "B36/S23",
}
DENSITIES = (0.01, 0.05, 0.15, 0.30, 0.50, 0.90)
REPLICATES = 10
CASE_RULES = {
    "Sparse exemplar": "B568/S01238",
    "Active exemplar": "B123/S02457",
    "Dense exemplar": "B3/S245678",
    "ML outlier": "B126/S35678",
}


def conway_highlife_experiment() -> tuple[pd.DataFrame, dict[tuple[str, float], list[np.ndarray]]]:
    rows: list[dict] = []
    trajectories: dict[tuple[str, float], list[np.ndarray]] = {}
    for rule_number, (label, rule) in enumerate(TARGET_RULES.items()):
        for density_number, density in enumerate(DENSITIES):
            key = (label, density)
            trajectories[key] = []
            for replicate in range(REPLICATES):
                seed = CONFIG.random_seed + 2_000_000 + density_number * 100 + replicate
                trajectory = simulate(rule, CONFIG.grid_size, density, CONFIG.steps, seed)
                trajectories[key].append(trajectory)
                features = extract_features(trajectory)
                rows.append({
                    "label": label,
                    "rule": rule,
                    "initial_density": density,
                    "replicate": replicate,
                    "seed": seed,
                    **features,
                })
    return pd.DataFrame(rows), trajectories


def plot_density_comparison(trajectories: dict, output: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, sharey=True)
    colors = {"Conway Life": "#57d9c4", "HighLife": "#ff9d66"}
    for axis, density in zip(axes.flat, DENSITIES):
        for label in TARGET_RULES:
            series = np.array([trajectory.mean(axis=(1, 2)) for trajectory in trajectories[(label, density)]])
            mean = series.mean(axis=0)
            low, high = np.percentile(series, [10, 90], axis=0)
            axis.plot(mean, label=label, color=colors[label], linewidth=2)
            axis.fill_between(np.arange(len(mean)), low, high, color=colors[label], alpha=0.15)
        axis.set_title(f"Initial density {density:.0%}")
        axis.grid(alpha=0.15)
    axes[0, 0].legend(frameon=False)
    for axis in axes[-1]:
        axis.set_xlabel("Generation")
    for axis in axes[:, 0]:
        axis.set_ylabel("Live-cell density")
    fig.suptitle("Conway and HighLife: mean of 10 seeded runs (bands show 10th–90th percentiles)")
    fig.tight_layout()
    fig.savefig(output / "conway_highlife_density.png", dpi=190)
    plt.close(fig)


def plot_rule_snapshots(output: Path) -> None:
    rules = {**TARGET_RULES, **CASE_RULES}
    generations = (0, 25, 75, 150)
    fig, axes = plt.subplots(len(rules), len(generations), figsize=(10, 14))
    seed = CONFIG.random_seed + 3_000_000
    for row, (label, rule) in enumerate(rules.items()):
        trajectory = simulate(rule, CONFIG.grid_size, 0.30, CONFIG.steps, seed)
        for col, generation in enumerate(generations):
            axis = axes[row, col]
            axis.imshow(trajectory[generation], cmap="Greens", vmin=0, vmax=1, interpolation="nearest")
            axis.set_xticks([])
            axis.set_yticks([])
            if row == 0:
                axis.set_title(f"Generation {generation}")
            if col == 0:
                axis.set_ylabel(f"{label}\n{rule}", rotation=0, ha="right", va="center", labelpad=12)
    fig.suptitle("Case studies from the same 30% random initial condition")
    fig.tight_layout()
    fig.savefig(output / "rule_snapshots.png", dpi=190)
    plt.close(fig)


def plot_case_timeseries(output: Path) -> pd.DataFrame:
    seed = CONFIG.random_seed + 3_000_000
    records = []
    fig, (density_axis, activity_axis) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    colors = ["#57d9c4", "#ff9d66", "#a58cff", "#b8f35a"]
    for color, (label, rule) in zip(colors, CASE_RULES.items()):
        trajectory = simulate(rule, CONFIG.grid_size, 0.30, CONFIG.steps, seed)
        density = trajectory.mean(axis=(1, 2))
        activity = np.not_equal(trajectory[1:], trajectory[:-1]).mean(axis=(1, 2))
        density_axis.plot(density, label=f"{label}: {rule}", color=color)
        activity_axis.plot(np.arange(1, len(trajectory)), activity, color=color)
        features = extract_features(trajectory)
        records.append({"label": label, "rule": rule, **features})
    density_axis.set_ylabel("Live-cell density")
    activity_axis.set_ylabel("Activity")
    activity_axis.set_xlabel("Generation")
    density_axis.legend(fontsize=8, frameon=False, ncol=2)
    density_axis.grid(alpha=0.15)
    activity_axis.grid(alpha=0.15)
    fig.suptitle("Learned cluster exemplars and the behavioral outlier")
    fig.tight_layout()
    fig.savefig(output / "case_timeseries.png", dpi=190)
    plt.close(fig)
    return pd.DataFrame(records)


def plot_known_patterns(output: Path) -> None:
    size = 18
    block = np.zeros((size, size), dtype=np.uint8)
    block[7:9, 7:9] = 1
    blinker = np.zeros((size, size), dtype=np.uint8)
    blinker[8, 7:10] = 1
    glider = np.zeros((size, size), dtype=np.uint8)
    glider[5:8, 5:8] = np.array([[0, 1, 0], [0, 0, 1], [1, 1, 1]], dtype=np.uint8)
    examples = [
        ("Block, generation 0", simulate("B3/S23", steps=1, initial_grid=block)[0]),
        ("Block, generation 1", simulate("B3/S23", steps=1, initial_grid=block)[1]),
        ("Blinker, generation 0", simulate("B3/S23", steps=2, initial_grid=blinker)[0]),
        ("Blinker, generation 1", simulate("B3/S23", steps=2, initial_grid=blinker)[1]),
        ("Blinker, generation 2", simulate("B3/S23", steps=2, initial_grid=blinker)[2]),
        ("Glider, generation 0", simulate("B3/S23", steps=4, initial_grid=glider)[0]),
        ("Glider, generation 4", simulate("B3/S23", steps=4, initial_grid=glider)[4]),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(10, 5))
    for axis, (title, state) in zip(axes.flat, examples):
        axis.imshow(state, cmap="Greens", vmin=0, vmax=1, interpolation="nearest")
        axis.set_title(title, fontsize=9)
        axis.set_xticks([])
        axis.set_yticks([])
    axes.flat[-1].axis("off")
    fig.suptitle("Conway sanity checks: stability, oscillation, and motion")
    fig.tight_layout()
    fig.savefig(output / "known_patterns.png", dpi=190)
    plt.close(fig)


def run(root: Path) -> None:
    data_output = root / "data"
    figure_output = root / "analysis" / "figures"
    data_output.mkdir(parents=True, exist_ok=True)
    figure_output.mkdir(parents=True, exist_ok=True)
    comparison, trajectories = conway_highlife_experiment()
    comparison.to_csv(data_output / "conway_highlife_investigation.csv", index=False)
    summary = comparison.groupby(["label", "rule", "initial_density"], as_index=False).agg(
        final_density_mean=("final_density", "mean"),
        final_density_std=("final_density", "std"),
        activity_mean=("activity", "mean"),
        recurrence_mean=("recurrence", "mean"),
        component_count_mean=("component_count", "mean"),
        extinction_rate=("extinct", "mean"),
    )
    summary.to_csv(data_output / "conway_highlife_summary.csv", index=False)
    plot_density_comparison(trajectories, figure_output)
    plot_rule_snapshots(figure_output)
    plot_case_timeseries(figure_output).to_csv(data_output / "case_studies.csv", index=False)
    plot_known_patterns(figure_output)
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
