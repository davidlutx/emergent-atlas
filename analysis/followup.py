"""Follow-up experiments requested after review of the initial project."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analyze import aggregate_rules, fit_behavior_map
from .ca import simulate
from .config import CONFIG
from .features import FEATURE_NAMES, extract_features


REPRESENTATIVES = {
    "sparse": "B568/S01238",
    "active": "B123/S02457",
    "dense": "B3/S245678",
}
NOISE_LEVELS = np.arange(100, dtype=float) / 100.0
NOISE_RUNS = 10


def load_projection(root: Path):
    trajectories = pd.read_csv(root / "data" / "simulation_features.csv")
    rules = aggregate_rules(trajectories)
    scaler, pca, coordinates, labels, _, _ = fit_behavior_map(rules, CONFIG.random_seed)
    lookup = {
        str(row["rule"]): (coordinates[index], int(labels[index]))
        for index, row in rules.iterrows()
    }
    return scaler, pca, lookup


def run_noise_sweep(root: Path) -> pd.DataFrame:
    scaler, pca, lookup = load_projection(root)
    rows: list[dict] = []
    for rule_number, (regime, rule) in enumerate(REPRESENTATIVES.items()):
        for noise in NOISE_LEVELS:
            for run in range(NOISE_RUNS):
                density = CONFIG.initial_densities[run % len(CONFIG.initial_densities)]
                seed = CONFIG.random_seed + 4_000_000 + rule_number * 10_000 + run
                trajectory = simulate(
                    rule,
                    CONFIG.grid_size,
                    density,
                    CONFIG.steps,
                    seed,
                    noise,
                )
                rows.append({
                    "regime": regime,
                    "rule": rule,
                    "noise_probability": noise,
                    "run": run,
                    "initial_density": density,
                    **extract_features(trajectory),
                })

    raw = pd.DataFrame(rows)
    raw.to_csv(root / "data" / "noise_sweep_raw.csv", index=False)

    summaries = []
    for (regime, rule, noise), group in raw.groupby(
        ["regime", "rule", "noise_probability"], sort=True
    ):
        record = {
            "regime": regime,
            "rule": rule,
            "noise_probability": float(noise),
            "cluster": lookup[rule][1],
        }
        for feature in FEATURE_NAMES:
            values = group[feature].to_numpy(dtype=float)
            record[f"{feature}_mean"] = float(values.mean())
            record[f"{feature}_q10"] = float(np.quantile(values, 0.10))
            record[f"{feature}_q90"] = float(np.quantile(values, 0.90))
        vector = pd.DataFrame(
            [[record[f"{feature}_mean"] for feature in FEATURE_NAMES]],
            columns=[f"{feature}_mean" for feature in FEATURE_NAMES],
        )
        point = pca.transform(scaler.transform(vector))[0]
        record["pca_x"] = float(point[0])
        record["pca_y"] = float(point[1])
        summaries.append(record)

    summary = pd.DataFrame(summaries)
    for rule in summary["rule"].unique():
        mask = summary["rule"] == rule
        baseline = summary.loc[mask & (summary["noise_probability"] == 0), ["pca_x", "pca_y"]].iloc[0].to_numpy()
        points = summary.loc[mask, ["pca_x", "pca_y"]].to_numpy()
        summary.loc[mask, "pca_displacement"] = np.linalg.norm(points - baseline, axis=1)
    summary.to_csv(root / "data" / "noise_sweep_summary.csv", index=False)
    plot_noise_sweeps(summary, root / "analysis" / "figures")
    return summary


def plot_noise_sweeps(summary: pd.DataFrame, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    panels = [
        ("mean_density", "Mean live-cell density"),
        ("activity", "Activity"),
        ("recurrence", "Recurrence"),
    ]
    for regime, rule in REPRESENTATIVES.items():
        subset = summary[summary["rule"] == rule].sort_values("noise_probability")
        x = subset["noise_probability"].to_numpy() * 100
        fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
        for axis, (feature, label) in zip(axes.flat[:3], panels):
            mean = subset[f"{feature}_mean"].to_numpy()
            low = subset[f"{feature}_q10"].to_numpy()
            high = subset[f"{feature}_q90"].to_numpy()
            axis.plot(x, mean, color="#16796f", linewidth=2)
            axis.fill_between(x, low, high, color="#57d9c4", alpha=0.22)
            axis.set_ylabel(label)
            axis.grid(alpha=0.18)
        axes.flat[3].plot(x, subset["pca_displacement"], color="#8a63d2", linewidth=2)
        axes.flat[3].set_ylabel("PCA displacement")
        axes.flat[3].grid(alpha=0.18)
        for axis in axes[-1]:
            axis.set_xlabel("Cell-flip probability (%)")
        fig.suptitle(f"{regime.title()} representative {rule}: response to noise")
        fig.tight_layout()
        fig.savefig(output / f"noise_sweep_{regime}.png", dpi=190)
        plt.close(fig)


def run_b6_ablation(root: Path) -> pd.DataFrame:
    rules = ("B126/S35678", "B12/S35678")
    densities = CONFIG.initial_densities
    repeats = 10
    rows = []
    trajectories: dict[tuple[str, float], list[np.ndarray]] = {}
    for density_number, density in enumerate(densities):
        for rule in rules:
            trajectories[(rule, density)] = []
            for run in range(repeats):
                seed = CONFIG.random_seed + 5_000_000 + density_number * 100 + run
                trajectory = simulate(rule, CONFIG.grid_size, density, CONFIG.steps, seed)
                trajectories[(rule, density)].append(trajectory)
                rows.append({
                    "rule": rule,
                    "initial_density": density,
                    "run": run,
                    "seed": seed,
                    **extract_features(trajectory),
                })
    result = pd.DataFrame(rows)
    result.to_csv(root / "data" / "b6_ablation.csv", index=False)
    plot_b6_ablation(trajectories, root / "analysis" / "figures")
    return result


def plot_b6_ablation(trajectories: dict, output: Path) -> None:
    rules = ("B126/S35678", "B12/S35678")
    colors = {"B126/S35678": "#8a63d2", "B12/S35678": "#16796f"}
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True, sharey=True)
    for axis, density in zip(axes.flat[:5], CONFIG.initial_densities):
        for rule in rules:
            series = np.array([item.mean(axis=(1, 2)) for item in trajectories[(rule, density)]])
            mean = series.mean(axis=0)
            low, high = np.quantile(series, [0.10, 0.90], axis=0)
            axis.plot(mean, color=colors[rule], label=rule, linewidth=2)
            axis.fill_between(np.arange(len(mean)), low, high, color=colors[rule], alpha=0.13)
        axis.set_title(f"Initial density {density:.0%}")
        axis.grid(alpha=0.18)
    axes.flat[0].legend(frameon=False, fontsize=8)
    axes.flat[5].axis("off")
    for axis in axes[-1, :2]:
        axis.set_xlabel("Generation")
    for axis in axes[:, 0]:
        axis.set_ylabel("Live-cell density")
    fig.suptitle("Removing B6 from the outlier rule")
    fig.tight_layout()
    fig.savefig(output / "outlier_b6_ablation.png", dpi=190)
    plt.close(fig)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    noise = run_noise_sweep(root)
    ablation = run_b6_ablation(root)
    report = {
        "noise_max_adjacent_change": {},
        "ablation": [],
    }
    for regime in REPRESENTATIVES:
        subset = noise[noise["regime"] == regime].sort_values("noise_probability")
        report["noise_max_adjacent_change"][regime] = {
            feature: float(np.abs(np.diff(subset[f"{feature}_mean"])).max())
            for feature in ("mean_density", "activity", "recurrence")
        }
    grouped = ablation.groupby(["rule", "initial_density"], as_index=False).agg(
        final_density=("final_density", "mean"),
        activity=("activity", "mean"),
        growth=("growth", "mean"),
    )
    report["ablation"] = grouped.to_dict(orient="records")
    (root / "data" / "followup_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
