"""Vectorized two-dimensional cellular-automaton simulator."""

from __future__ import annotations

import numpy as np

from .rules import parse_rule


def neighbor_counts(grid: np.ndarray, boundary: str = "toroidal") -> np.ndarray:
    """Count eight Moore neighbors using toroidal or dead boundaries."""
    if boundary not in {"toroidal", "dead"}:
        raise ValueError("boundary must be 'toroidal' or 'dead'")
    if boundary == "dead":
        padded = np.pad(grid, 1, mode="constant")
        rows, cols = grid.shape
        counts = np.zeros_like(grid, dtype=np.uint8)
        for row_offset in range(3):
            for col_offset in range(3):
                if row_offset != 1 or col_offset != 1:
                    counts += padded[row_offset:row_offset + rows, col_offset:col_offset + cols]
        return counts
    counts = np.zeros_like(grid, dtype=np.uint8)
    for row_shift in (-1, 0, 1):
        for col_shift in (-1, 0, 1):
            if row_shift or col_shift:
                counts += np.roll(np.roll(grid, row_shift, axis=0), col_shift, axis=1)
    return counts


def step(grid: np.ndarray, rule: str | np.ndarray, rng: np.random.Generator | None = None,
         noise_probability: float = 0.0, boundary: str = "toroidal") -> np.ndarray:
    """Advance one generation, then independently flip cells with probability p."""
    if not 0.0 <= noise_probability <= 1.0:
        raise ValueError("noise_probability must be between 0 and 1")
    bits = parse_rule(rule) if isinstance(rule, str) else np.asarray(rule, dtype=np.uint8)
    if bits.shape != (18,):
        raise ValueError("rule must be a B/S string or an 18-bit vector")
    current = np.asarray(grid, dtype=np.uint8)
    counts = neighbor_counts(current, boundary)
    next_grid = np.where(current == 1, bits[9 + counts], bits[counts]).astype(np.uint8)
    if noise_probability:
        if rng is None:
            rng = np.random.default_rng()
        next_grid ^= (rng.random(current.shape) < noise_probability).astype(np.uint8)
    return next_grid


def simulate(rule: str | np.ndarray, grid_size: int = 40, initial_density: float = 0.3,
             steps: int = 100, seed: int = 0, noise_probability: float = 0.0,
             initial_grid: np.ndarray | None = None, boundary: str = "toroidal") -> np.ndarray:
    """Return a trajectory with shape (steps + 1, rows, columns)."""
    rng = np.random.default_rng(seed)
    if initial_grid is None:
        grid = (rng.random((grid_size, grid_size)) < initial_density).astype(np.uint8)
    else:
        grid = np.asarray(initial_grid, dtype=np.uint8).copy()
        if grid.ndim != 2:
            raise ValueError("initial_grid must be two-dimensional")
    trajectory = np.empty((steps + 1, *grid.shape), dtype=np.uint8)
    trajectory[0] = grid
    for generation in range(1, steps + 1):
        grid = step(grid, rule, rng, noise_probability, boundary)
        trajectory[generation] = grid
    return trajectory
