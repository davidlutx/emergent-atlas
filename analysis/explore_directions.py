"""Follow-up experiments on grid size, boundaries, and rule-bit interventions."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .ca import simulate
from .rules import format_rule, parse_rule


RULES = {
    "Conway Life": "B3/S23",
    "HighLife": "B36/S23",
    "Sparse exemplar": "B568/S01238",
    "Active exemplar": "B123/S02457",
    "Dense exemplar": "B3/S245678",
    "Study outlier": "B126/S35678",
    "Outlier without B6": "B12/S35678",
}
SIZES = (25, 50, 100)
DENSITIES = (0.10, 0.30, 0.50)
BOUNDARIES = ("toroidal", "dead")
REPEATS = 10
STEPS = 150
SEED = 20260930


def summarize(trajectory: np.ndarray) -> dict[str, float | bool]:
    densities = trajectory.mean(axis=(1, 2))
    activity = np.not_equal(trajectory[1:], trajectory[:-1]).mean(axis=(1, 2))
    extinct = bool(np.any(densities == 0))
    return {
        "mean_density": float(densities.mean()),
        "final_density": float(densities[-1]),
        "activity": float(activity.mean()),
        "late_activity": float(activity[-min(30, len(activity)):].mean()),
        "growth": float(np.polyfit(np.linspace(0, 1, len(densities)), densities, 1)[0]),
        "extinct": extinct,
    }


def run_boundary_size_experiment(root: Path) -> pd.DataFrame:
    rows = []
    for rule_index, (name, rule) in enumerate(RULES.items()):
        for size in SIZES:
            for density in DENSITIES:
                for repeat in range(REPEATS):
                    seed = SEED + rule_index * 100_000 + size * 100 + int(density * 10) * 10 + repeat
                    for boundary in BOUNDARIES:
                        trajectory = simulate(
                            rule,
                            grid_size=size,
                            initial_density=density,
                            steps=STEPS,
                            seed=seed,
                            boundary=boundary,
                        )
                        rows.append({
                            "name": name,
                            "rule": rule,
                            "grid_size": size,
                            "boundary": boundary,
                            "initial_density": density,
                            "repeat": repeat,
                            "seed": seed,
                            **summarize(trajectory),
                        })
    data = pd.DataFrame(rows)
    data.to_csv(root / "data" / "boundary_size_experiment.csv", index=False)
    plot_boundary_size_effects(data, root / "analysis" / "figures" / "boundary_size_effects.png")
    plot_conway_size(data, root / "analysis" / "figures" / "conway_size_boundary.png")
    return data


def paired_boundary_effects(data: pd.DataFrame) -> pd.DataFrame:
    key = ["name", "rule", "grid_size", "initial_density", "repeat", "seed"]
    wide = data.pivot(index=key, columns="boundary", values=["final_density", "activity"]).reset_index()
    wide.columns = ["_".join(item).rstrip("_") if isinstance(item, tuple) else item for item in wide.columns]
    wide["final_density_difference"] = (wide["final_density_dead"] - wide["final_density_toroidal"]).abs()
    wide["activity_difference"] = (wide["activity_dead"] - wide["activity_toroidal"]).abs()
    return wide


def plot_boundary_size_effects(data: pd.DataFrame, output: Path) -> None:
    paired = paired_boundary_effects(data)
    labels = list(RULES)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    for axis, feature, title in (
        (axes[0], "final_density_difference", "Final-density difference"),
        (axes[1], "activity_difference", "Activity difference"),
    ):
        table = paired.groupby(["name", "grid_size"])[feature].mean().unstack().reindex(labels)
        image = axis.imshow(table.to_numpy(), cmap="Blues", aspect="auto", vmin=0)
        axis.set_xticks(range(len(SIZES)), [str(size) for size in SIZES])
        axis.set_yticks(range(len(labels)), labels)
        axis.set_xlabel("Grid width")
        axis.set_title(title)
        for row in range(len(labels)):
            for col in range(len(SIZES)):
                value = table.iloc[row, col]
                axis.text(col, row, f"{value:.3f}", ha="center", va="center", fontsize=8,
                          color="white" if value > table.to_numpy().max() * 0.55 else "#1f2933")
        fig.colorbar(image, ax=axis, shrink=0.75)
    fig.suptitle("How much does changing the boundary alter matched runs?")
    fig.savefig(output, dpi=190)
    plt.close(fig)


def plot_conway_size(data: pd.DataFrame, output: Path) -> None:
    subset = data[data["name"] == "Conway Life"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    colors = {"toroidal": "#2d5f8b", "dead": "#b26832"}
    for boundary in BOUNDARIES:
        group = subset[subset["boundary"] == boundary]
        summary = group.groupby("grid_size").agg(
            final=("final_density", "mean"),
            final_sd=("final_density", "std"),
            extinction=("extinct", "mean"),
        )
        axes[0].errorbar(summary.index, summary["final"], yerr=summary["final_sd"], marker="o",
                         capsize=3, label=boundary.title(), color=colors[boundary])
        axes[1].plot(summary.index, summary["extinction"] * 100, marker="o",
                     label=boundary.title(), color=colors[boundary])
    axes[0].set(title="Average final density", xlabel="Grid width", ylabel="Live-cell fraction")
    axes[1].set(title="Runs ending in extinction", xlabel="Grid width", ylabel="Percent")
    axes[1].set_ylim(-3, 103)
    for axis in axes:
        axis.grid(alpha=0.2)
        axis.legend(frameon=False)
    fig.suptitle("Conway Life becomes less variable on larger grids")
    fig.savefig(output, dpi=190)
    plt.close(fig)


def mutation_name(index: int, old_value: int) -> str:
    prefix = "B" if index < 9 else "S"
    count = index if index < 9 else index - 9
    action = "remove" if old_value else "add"
    return f"{action} {prefix}{count}"


def run_bit_mutations(root: Path) -> pd.DataFrame:
    original = "B126/S35678"
    base_bits = parse_rule(original)
    variants = [("original", original)]
    for index in range(18):
        changed = base_bits.copy()
        changed[index] ^= 1
        variants.append((mutation_name(index, int(base_bits[index])), format_rule(changed)))

    rows = []
    for density in DENSITIES:
        for repeat in range(12):
            seed = SEED + 2_000_000 + int(density * 10) * 100 + repeat
            for mutation, rule in variants:
                trajectory = simulate(rule, 40, density, STEPS, seed)
                rows.append({
                    "mutation": mutation,
                    "rule": rule,
                    "initial_density": density,
                    "repeat": repeat,
                    "seed": seed,
                    **summarize(trajectory),
                })
    data = pd.DataFrame(rows)
    data.to_csv(root / "data" / "outlier_bit_mutations.csv", index=False)
    plot_bit_mutations(data, root / "analysis" / "figures" / "outlier_bit_mutations.png")
    return data


def mutation_effects(data: pd.DataFrame) -> pd.DataFrame:
    keys = ["initial_density", "repeat", "seed"]
    baseline = data[data["mutation"] == "original"][keys + ["final_density", "activity", "late_activity"]]
    changed = data[data["mutation"] != "original"].merge(baseline, on=keys, suffixes=("", "_original"))
    changed["final_density_change"] = changed["final_density"] - changed["final_density_original"]
    changed["activity_change"] = changed["activity"] - changed["activity_original"]
    changed["late_activity_change"] = changed["late_activity"] - changed["late_activity_original"]
    return changed


def plot_bit_mutations(data: pd.DataFrame, output: Path) -> None:
    effects = mutation_effects(data)
    order = effects.groupby("mutation")["final_density_change"].mean().sort_values().index
    fig, axes = plt.subplots(1, 2, figsize=(11, 7), sharey=True, constrained_layout=True)
    for axis, feature, title in (
        (axes[0], "final_density_change", "Change in final density"),
        (axes[1], "activity_change", "Change in activity"),
    ):
        grouped = effects.groupby("mutation")[feature]
        means = grouped.mean().reindex(order)
        low = grouped.quantile(0.10).reindex(order)
        high = grouped.quantile(0.90).reindex(order)
        y = np.arange(len(order))
        axis.axvline(0, color="#6b7280", linewidth=1)
        colors = ["#b44b4b" if value < 0 else "#2d7890" for value in means]
        axis.barh(y, means, color=colors, alpha=0.88)
        axis.errorbar(means, y, xerr=[means - low, high - means], fmt="none", ecolor="#252a30", capsize=2)
        axis.set_yticks(y, order)
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.18)
    fig.suptitle("Changing one condition in B126/S35678")
    fig.savefig(output, dpi=190)
    plt.close(fig)


def centered_pattern(size: int, cells: list[tuple[int, int]]) -> np.ndarray:
    grid = np.zeros((size, size), dtype=np.uint8)
    height = max(row for row, _ in cells) + 1
    width = max(col for _, col in cells) + 1
    top = (size - height) // 2
    left = (size - width) // 2
    for row, col in cells:
        grid[top + row, left + col] = 1
    return grid


def run_localized_patterns(root: Path) -> pd.DataFrame:
    rows = []
    glider = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
    glider_grid = np.zeros((25, 25), dtype=np.uint8)
    for row, col in glider:
        glider_grid[18 + row, 18 + col] = 1
    glider_trajectories = {}
    for boundary in BOUNDARIES:
        trajectory = simulate("B3/S23", steps=40, initial_grid=glider_grid, boundary=boundary)
        glider_trajectories[boundary] = trajectory
        for generation, state in enumerate(trajectory):
            rows.append({"pattern": "glider", "grid_size": 25, "boundary": boundary,
                         "generation": generation, "population": int(state.sum())})
    plot_glider_boundaries(glider_trajectories, root / "analysis" / "figures" / "glider_boundary.png")

    r_pentomino = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
    trajectories = {}
    for size in (25, 50, 100, 200):
        trajectory = simulate("B3/S23", steps=300, initial_grid=centered_pattern(size, r_pentomino), boundary="dead")
        trajectories[size] = trajectory
        for generation, state in enumerate(trajectory):
            rows.append({"pattern": "r_pentomino", "grid_size": size, "boundary": "dead",
                         "generation": generation, "population": int(state.sum())})
    plot_finite_growth(trajectories, root / "analysis" / "figures" / "finite_grid_growth.png")
    data = pd.DataFrame(rows)
    data.to_csv(root / "data" / "localized_pattern_experiment.csv", index=False)
    return data


def plot_glider_boundaries(trajectories: dict[str, np.ndarray], output: Path) -> None:
    generations = (0, 16, 28, 40)
    fig, axes = plt.subplots(2, 4, figsize=(10, 5), constrained_layout=True)
    for row, boundary in enumerate(BOUNDARIES):
        for col, generation in enumerate(generations):
            axes[row, col].imshow(trajectories[boundary][generation], cmap="Blues", vmin=0, vmax=1)
            axes[row, col].set_title(f"{boundary.title()}, t={generation}", fontsize=9)
            axes[row, col].set_xticks([])
            axes[row, col].set_yticks([])
    fig.suptitle("The same glider reaches two different worlds at the edge")
    fig.savefig(output, dpi=190)
    plt.close(fig)


def plot_finite_growth(trajectories: dict[int, np.ndarray], output: Path) -> None:
    fig, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for size, trajectory in trajectories.items():
        axis.plot(trajectory.sum(axis=(1, 2)), label=f"{size} × {size}")
    axis.set(xlabel="Generation", ylabel="Live cells",
             title="A larger dead-edge grid better approximates open space")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    fig.savefig(output, dpi=190)
    plt.close(fig)


def first_population_divergence(reference: np.ndarray, candidate: np.ndarray) -> int | None:
    differences = np.flatnonzero(reference != candidate)
    return int(differences[0]) if len(differences) else None


def write_summary(root: Path, boundary: pd.DataFrame, mutations: pd.DataFrame,
                  localized: pd.DataFrame) -> dict:
    paired = paired_boundary_effects(boundary)
    boundary_summary = paired.groupby("grid_size").agg(
        final_density_difference=("final_density_difference", "mean"),
        activity_difference=("activity_difference", "mean"),
    )
    within_condition_sd = (
        boundary.groupby(["name", "grid_size", "boundary", "initial_density"])["final_density"]
        .std()
        .groupby(["name", "grid_size"])
        .mean()
        .unstack()
    )
    effects = mutation_effects(mutations)
    mutation_summary = effects.groupby("mutation").agg(
        final_density_change=("final_density_change", "mean"),
        activity_change=("activity_change", "mean"),
        late_activity_change=("late_activity_change", "mean"),
    ).sort_values("final_density_change")
    r_data = localized[localized["pattern"] == "r_pentomino"]
    populations = {size: group.sort_values("generation")["population"].to_numpy()
                   for size, group in r_data.groupby("grid_size")}
    reference = populations[200]
    report = {
        "boundary_by_size": boundary_summary.reset_index().to_dict(orient="records"),
        "most_boundary_sensitive": paired.groupby("name")["final_density_difference"].mean().sort_values(ascending=False).to_dict(),
        "average_within_condition_final_density_sd": {
            name: {str(size): float(value) for size, value in row.items()}
            for name, row in within_condition_sd.iterrows()
        },
        "mutation_effects": mutation_summary.reset_index().to_dict(orient="records"),
        "r_pentomino_first_population_divergence_from_200": {
            str(size): first_population_divergence(reference, values)
            for size, values in populations.items() if size != 200
        },
    }
    (root / "data" / "exploration_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    boundary = run_boundary_size_experiment(root)
    mutations = run_bit_mutations(root)
    localized = run_localized_patterns(root)
    summary = write_summary(root, boundary, mutations, localized)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
