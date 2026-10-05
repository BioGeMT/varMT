"""Load shared browser settings independently of the working directory."""

from dataclasses import dataclass
from pathlib import Path

import yaml


POLICY_PATH = Path(__file__).resolve().parents[2] / 'config' / 'browser_policy.yml'


@dataclass(frozen=True)
class BrowserPolicy:
    max_interval_bases: int
    min_maf: float


def load_browser_policy(path: Path = POLICY_PATH) -> BrowserPolicy:
    """Require a valid policy file; never silently fall back to weaker limits."""
    try:
        with path.open() as file:
            settings = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Cannot load browser policy from {path}: {error}") from error

    query = settings.get('query') if isinstance(settings, dict) else None
    limit = query.get('max_interval_bases') if isinstance(query, dict) else None
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError(f"{path}: query.max_interval_bases must be a positive integer.")

    min_maf = query.get('min_maf')
    if isinstance(min_maf, bool) or not isinstance(min_maf, (int, float)) or not 0 < min_maf <= 0.5:
        raise ValueError(f"{path}: query.min_maf must be a number greater than 0 and at most 0.5.")
    return BrowserPolicy(max_interval_bases=limit, min_maf=float(min_maf))


_policy = load_browser_policy()
MAX_QUERY_BASES = _policy.max_interval_bases
MIN_MAF = _policy.min_maf
