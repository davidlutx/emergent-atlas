"""Parsing and encoding for binary outer-totalistic cellular automata."""

from __future__ import annotations

import re

import numpy as np

RULE_PATTERN = re.compile(r"^B([0-8]*)/S([0-8]*)$", re.IGNORECASE)


def parse_rule(rule: str) -> np.ndarray:
    """Convert a B/S rule string into [B0..B8, S0..S8]."""
    compact = re.sub(r"\s+", "", rule).upper()
    match = RULE_PATTERN.fullmatch(compact)
    if not match:
        raise ValueError(f"Invalid outer-totalistic rule: {rule!r}")
    birth_text, survival_text = match.groups()
    if len(set(birth_text)) != len(birth_text) or len(set(survival_text)) != len(survival_text):
        raise ValueError(f"Repeated neighbor count in rule: {rule!r}")
    bits = np.zeros(18, dtype=np.uint8)
    for digit in birth_text:
        bits[int(digit)] = 1
    for digit in survival_text:
        bits[9 + int(digit)] = 1
    return bits


def format_rule(bits: np.ndarray | list[int]) -> str:
    """Convert [B0..B8, S0..S8] into canonical B/S notation."""
    values = np.asarray(bits, dtype=np.uint8)
    if values.shape != (18,) or not np.isin(values, (0, 1)).all():
        raise ValueError("Rule must contain exactly 18 binary values")
    births = "".join(str(i) for i in range(9) if values[i])
    survivals = "".join(str(i) for i in range(9) if values[9 + i])
    return f"B{births}/S{survivals}"


def sample_rules(count: int, seed: int, include: tuple[str, ...] = ("B3/S23", "B36/S23")) -> list[np.ndarray]:
    """Sample unique rules reproducibly, always including named reference rules."""
    if count < len(include):
        raise ValueError("count must be at least the number of included rules")
    rng = np.random.default_rng(seed)
    chosen: dict[str, np.ndarray] = {}
    for rule in include:
        bits = parse_rule(rule)
        chosen[format_rule(bits)] = bits
    while len(chosen) < count:
        bits = rng.integers(0, 2, size=18, dtype=np.uint8)
        chosen.setdefault(format_rule(bits), bits)
    return list(chosen.values())

