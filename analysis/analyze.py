"""PCA, clustering, supervised prediction, and perturbation experiments."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, silhouette_score
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .ca import simulate
from .config import CONFIG, ExperimentConfig
from .features import FEATURE_NAMES, extract_features
from .generate import write_dataset
from .rules import parse_rule

RULE_BIT_NAMES = [f"B{i}" for i in range(9)] + [f"S{i}" for i in range(9)]


def _python(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if pd.isna(value):
        return None
    return value


def aggregate_rules(trajectories: pd.DataFrame) -> pd.DataFrame:
    aggregations = {name: ["mean", "std"] for name in FEATURE_NAMES}
    grouped = trajectories.groupby(["rule_index", "rule", *RULE_BIT_NAMES], as_index=False).agg(aggregations)
    grouped.columns = [
        column if isinstance(column, str) else column[0]
        if not column[1]
        else f"{column[0]}_{column[1]}"
        for column in grouped.columns
    ]
    return grouped.fillna(0.0)


def fit_behavior_map(rules: pd.DataFrame, seed: int) -> tuple[StandardScaler, PCA, np.ndarray, np.ndarray, list[dict], int]:
    feature_columns = [f"{name}_mean" for name in FEATURE_NAMES]
    scaler = StandardScaler().fit(rules[feature_columns])
    scaled = scaler.transform(rules[feature_columns])
    pca = PCA(n_components=2, random_state=seed).fit(scaled)
    coordinates = pca.transform(scaled)

    candidates = []
    models = {}
    for k in (3, 4, 5):
        model = KMeans(n_clusters=k, n_init=50, random_state=seed).fit(scaled)
        sizes = np.bincount(model.labels_, minlength=k)
        score = silhouette_score(scaled, model.labels_)
        candidates.append({"k": k, "silhouette": float(score), "sizes": sizes.tolist()})
        models[k] = model
    minimum_cluster_size = max(5, int(np.ceil(len(rules) * 0.02)))
    eligible = [item for item in candidates if min(item["sizes"]) >= minimum_cluster_size] or candidates
    chosen_k = max(eligible, key=lambda item: item["silhouette"])["k"]
    labels = models[chosen_k].labels_.copy()

    # Make cluster IDs deterministic and readable: sparse clusters come first.
    density = rules["mean_density_mean"].to_numpy()
    ordering = sorted(range(chosen_k), key=lambda cluster: density[labels == cluster].mean())
    remap = {old: new for new, old in enumerate(ordering)}
    labels = np.array([remap[label] for label in labels], dtype=int)
    return scaler, pca, coordinates, labels, candidates, chosen_k


def train_predictor(rules: pd.DataFrame, labels: np.ndarray, seed: int) -> tuple[dict, np.ndarray]:
    x = rules[RULE_BIT_NAMES].to_numpy()
    folds = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=seed)
    candidates = {
        "Majority baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic regression": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed),
        "Decision tree": DecisionTreeClassifier(max_depth=8, min_samples_leaf=5, class_weight="balanced", random_state=seed),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, random_state=seed, class_weight="balanced", n_jobs=-1
        ),
    }
    comparison = []
    for name, candidate in candidates.items():
        scores = cross_validate(
            candidate,
            x,
            labels,
            cv=folds,
            scoring={"accuracy": "accuracy", "balanced_accuracy": "balanced_accuracy"},
            n_jobs=-1,
        )
        comparison.append({
            "model": name,
            "accuracy_mean": float(scores["test_accuracy"].mean()),
            "accuracy_std": float(scores["test_accuracy"].std()),
            "balanced_accuracy_mean": float(scores["test_balanced_accuracy"].mean()),
            "balanced_accuracy_std": float(scores["test_balanced_accuracy"].std()),
            "evaluations": int(len(scores["test_accuracy"])),
        })

    x_train, x_test, y_train, y_test = train_test_split(
        x, labels, test_size=0.2, random_state=seed, stratify=labels
    )
    model = RandomForestClassifier(
        n_estimators=500, random_state=seed, class_weight="balanced", n_jobs=-1
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)
    balanced_accuracy = balanced_accuracy_score(y_test, predictions)
    majority = np.bincount(y_train).max() / len(y_train)
    matrix = confusion_matrix(y_test, predictions, labels=range(len(np.unique(labels))))
    result = {
        "accuracy": float(accuracy),
        "balanced_accuracy": float(balanced_accuracy),
        "majority_baseline": float(majority),
        "test_size": int(len(y_test)),
        "cross_validation": comparison,
        "confusion_matrix": matrix.tolist(),
        "feature_importance": [
            {"feature": name, "importance": float(value)}
            for name, value in sorted(zip(RULE_BIT_NAMES, model.feature_importances_), key=lambda pair: pair[1], reverse=True)
        ],
    }
    return result, model.feature_importances_


def cluster_summaries(rules: pd.DataFrame, labels: np.ndarray, coordinates: np.ndarray) -> tuple[list[dict], dict[int, int], int]:
    summaries = []
    representatives = {}
    distances = np.zeros(len(rules))
    for cluster in sorted(np.unique(labels)):
        indices = np.flatnonzero(labels == cluster)
        centroid = coordinates[indices].mean(axis=0)
        local_distances = np.linalg.norm(coordinates[indices] - centroid, axis=1)
        representative = int(indices[np.argmin(local_distances)])
        representatives[int(cluster)] = representative
        distances[indices] = local_distances
        means = {name: float(rules.loc[indices, f"{name}_mean"].mean()) for name in FEATURE_NAMES}
        summaries.append({
            "cluster": int(cluster),
            "size": int(len(indices)),
            "representative_rule": str(rules.iloc[representative]["rule"]),
            "features": means,
        })
    outlier = int(np.argmax(distances))
    return summaries, representatives, outlier


def run_noise_experiment(rules: pd.DataFrame, selected_indices: list[int], scaler: StandardScaler,
                         pca: PCA, config: ExperimentConfig) -> list[dict]:
    records = []
    for rule_position in selected_indices:
        rule = str(rules.iloc[rule_position]["rule"])
        bits = parse_rule(rule)
        for noise in config.noise_levels:
            measurements = []
            for run in range(config.noise_runs):
                density = config.initial_densities[run % len(config.initial_densities)]
                seed = config.random_seed + 1_000_000 + rule_position * 1000 + run
                trajectory = simulate(bits, config.grid_size, density, config.steps, seed, noise)
                measurements.append(extract_features(trajectory))
            vector = np.array([[np.mean([row[name] for row in measurements]) for name in FEATURE_NAMES]])
            point = pca.transform(scaler.transform(pd.DataFrame(vector, columns=[f"{name}_mean" for name in FEATURE_NAMES])))[0]
            records.append({
                "rule": rule,
                "noise": float(noise),
                "pca_x": float(point[0]),
                "pca_y": float(point[1]),
                "features": {name: float(np.mean([row[name] for row in measurements])) for name in FEATURE_NAMES},
            })
    baseline = {record["rule"]: np.array([record["pca_x"], record["pca_y"]]) for record in records if record["noise"] == 0}
    for record in records:
        point = np.array([record["pca_x"], record["pca_y"]])
        record["displacement"] = float(np.linalg.norm(point - baseline[record["rule"]]))
    return records


def make_figures(output: Path, rules: pd.DataFrame, labels: np.ndarray, coordinates: np.ndarray,
                 supervised: dict, importances: np.ndarray, noise: list[dict]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 5))
    for cluster in sorted(np.unique(labels)):
        mask = labels == cluster
        plt.scatter(coordinates[mask, 0], coordinates[mask, 1], label=f"Cluster {cluster + 1}", alpha=0.8)
    plt.xlabel("PCA component 1")
    plt.ylabel("PCA component 2")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "behavior_map.png", dpi=180)
    plt.close()

    order = np.argsort(importances)
    plt.figure(figsize=(7, 5))
    plt.barh(np.array(RULE_BIT_NAMES)[order], importances[order])
    plt.xlabel("Random Forest feature importance")
    plt.tight_layout()
    plt.savefig(output / "feature_importance.png", dpi=180)
    plt.close()

    matrix = np.array(supervised["confusion_matrix"])
    plt.figure(figsize=(5, 4))
    plt.imshow(matrix, cmap="Blues")
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            plt.text(col, row, matrix[row, col], ha="center", va="center")
    plt.xlabel("Predicted cluster")
    plt.ylabel("Actual cluster")
    plt.tight_layout()
    plt.savefig(output / "confusion_matrix.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7, 5))
    for rule in sorted({record["rule"] for record in noise}):
        subset = [record for record in noise if record["rule"] == rule]
        plt.plot([r["pca_x"] for r in subset], [r["pca_y"] for r in subset], "o-", label=rule)
    plt.xlabel("PCA component 1")
    plt.ylabel("PCA component 2")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(output / "noise_paths.png", dpi=180)
    plt.close()


def run_pipeline(root: Path, config: ExperimentConfig = CONFIG) -> dict:
    data_dir = root / "data"
    web_data_dir = root / "web" / "data"
    csv_path = data_dir / "simulation_features.csv"
    trajectories = write_dataset(csv_path, config)
    rules = aggregate_rules(trajectories)
    scaler, pca, coordinates, labels, candidates, chosen_k = fit_behavior_map(rules, config.random_seed)
    summaries, representatives, outlier = cluster_summaries(rules, labels, coordinates)
    supervised, importances = train_predictor(rules, labels, config.random_seed)
    selected = list(representatives.values())
    if outlier not in selected:
        selected.append(outlier)
    noise = run_noise_experiment(rules, selected, scaler, pca, config)

    points = []
    for index, row in rules.iterrows():
        points.append({
            "rule": row["rule"],
            "bits": [int(row[name]) for name in RULE_BIT_NAMES],
            "cluster": int(labels[index]),
            "pca_x": float(coordinates[index, 0]),
            "pca_y": float(coordinates[index, 1]),
            "is_outlier": bool(index == outlier),
            "features": {name: float(row[f"{name}_mean"]) for name in FEATURE_NAMES},
            "feature_std": {name: float(row[f"{name}_std"]) for name in FEATURE_NAMES},
        })
    result = {
        "metadata": {
            **config.to_dict(),
            "feature_names": FEATURE_NAMES,
            "pca_explained_variance": pca.explained_variance_ratio_.tolist(),
            "cluster_candidates": candidates,
            "chosen_k": int(chosen_k),
            "outlier_rule": str(rules.iloc[outlier]["rule"]),
        },
        "clusters": summaries,
        "supervised": supervised,
        "rules": points,
        "noise": noise,
    }
    for destination in (data_dir / "rule_analysis.json", web_data_dir / "rule_analysis.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, default=_python) + "\n")
    rules.assign(cluster=labels, pca_x=coordinates[:, 0], pca_y=coordinates[:, 1]).to_csv(
        data_dir / "rule_summary.csv", index=False
    )
    make_figures(root / "analysis" / "figures", rules, labels, coordinates, supervised, importances, noise)
    return result


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    analysis = run_pipeline(project_root)
    print(json.dumps({
        "rules": len(analysis["rules"]),
        "chosen_k": analysis["metadata"]["chosen_k"],
        "silhouettes": analysis["metadata"]["cluster_candidates"],
        "outlier": analysis["metadata"]["outlier_rule"],
        "accuracy": analysis["supervised"]["accuracy"],
        "baseline": analysis["supervised"]["majority_baseline"],
    }, indent=2))
