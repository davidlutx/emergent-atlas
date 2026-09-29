"""Small, explainable measurements of macroscopic CA behavior."""

from __future__ import annotations

from collections import deque

import numpy as np

FEATURE_NAMES = [
    "mean_density",
    "final_density",
    "activity",
    "growth",
    "entropy",
    "normalized_lifespan",
    "recurrence",
    "component_count",
]


def binary_entropy(probabilities: np.ndarray) -> np.ndarray:
    p = np.asarray(probabilities, dtype=float)
    result = np.zeros_like(p)
    mask = (p > 0.0) & (p < 1.0)
    result[mask] = -(p[mask] * np.log2(p[mask]) + (1 - p[mask]) * np.log2(1 - p[mask]))
    return result


def connected_components_toroidal(grid: np.ndarray) -> int:
    """Count 8-connected live components on a torus."""
    live = np.asarray(grid, dtype=bool)
    rows, cols = live.shape
    seen = np.zeros_like(live)
    components = 0
    for row, col in np.argwhere(live):
        if seen[row, col]:
            continue
        components += 1
        seen[row, col] = True
        queue = deque([(int(row), int(col))])
        while queue:
            r, c = queue.popleft()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if not (dr or dc):
                        continue
                    nr, nc = (r + dr) % rows, (c + dc) % cols
                    if live[nr, nc] and not seen[nr, nc]:
                        seen[nr, nc] = True
                        queue.append((nr, nc))
    return components


def extract_features(trajectory: np.ndarray) -> dict[str, float]:
    states = np.asarray(trajectory, dtype=np.uint8)
    if states.ndim != 3 or len(states) < 2:
        raise ValueError("trajectory must have shape (at least 2, rows, columns)")
    densities = states.mean(axis=(1, 2))
    changes = np.not_equal(states[1:], states[:-1]).mean(axis=(1, 2))
    time = np.linspace(0.0, 1.0, len(densities))
    growth = float(np.polyfit(time, densities, 1)[0])

    zero_generations = np.flatnonzero(densities == 0.0)
    extinction_generation = int(zero_generations[0]) if len(zero_generations) else len(states) - 1
    normalized_lifespan = extinction_generation / (len(states) - 1)

    best_distance = 1.0
    for lag in range(1, min(10, len(states) - 1) + 1):
        distance = np.not_equal(states[lag:], states[:-lag]).mean(axis=(1, 2)).min()
        best_distance = min(best_distance, float(distance))

    sample_indices = np.unique(np.linspace(0, len(states) - 1, 5, dtype=int))
    component_count = float(np.mean([connected_components_toroidal(states[i]) for i in sample_indices]))

    return {
        "mean_density": float(densities.mean()),
        "final_density": float(densities[-1]),
        "activity": float(changes.mean()),
        "growth": growth,
        "entropy": float(binary_entropy(densities).mean()),
        "normalized_lifespan": float(normalized_lifespan),
        "recurrence": float(1.0 - best_distance),
        "component_count": component_count,
        "extinct": bool(len(zero_generations)),
        "extinction_generation": int(zero_generations[0]) if len(zero_generations) else None,
    }

