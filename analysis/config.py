"""Single source of truth for reproducible experiment settings."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExperimentConfig:
    grid_size: int = 40
    steps: int = 150
    n_rules: int = 500
    runs_per_rule: int = 5
    initial_densities: tuple[float, ...] = (0.10, 0.20, 0.30, 0.40, 0.50)
    random_seed: int = 20260925
    noise_levels: tuple[float, ...] = (0.0, 0.001, 0.005, 0.01, 0.02)
    noise_runs: int = 10
    boundary: str = "toroidal"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["initial_densities"] = list(self.initial_densities)
        data["noise_levels"] = list(self.noise_levels)
        return data


CONFIG = ExperimentConfig()
