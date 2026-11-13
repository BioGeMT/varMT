"""Load shared browser settings independently of the working directory."""

from dataclasses import dataclass
from pathlib import Path

import yaml


POLICY_PATH = Path(__file__).resolve().parents[2] / 'config' / 'browser_policy.yml'
RATE_LIMIT_KEYS = ('per_minute', 'per_day', 'per_month')


@dataclass(frozen=True)
class BrowserPolicy:
    max_interval_bases: int
    min_maf: float
    frequency_bins: tuple[float, ...]
    rate_limits: dict[str, int]


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

    edges = query.get('frequency_bins')
    bins_error = f"{path}: query.frequency_bins must be increasing numbers from min_maf to 1 - min_maf."
    if not isinstance(edges, list) or len(edges) < 2:
        raise ValueError(bins_error)
    if any(isinstance(edge, bool) or not isinstance(edge, (int, float)) for edge in edges):
        raise ValueError(bins_error)
    if any(lower >= upper for lower, upper in zip(edges, edges[1:])):
        raise ValueError(bins_error)
    if round(edges[0], 6) != round(min_maf, 6) or round(edges[-1], 6) != round(1 - min_maf, 6):
        raise ValueError(bins_error)

    rate_limits = settings.get('rate_limits')
    if not isinstance(rate_limits, dict):
        raise ValueError(f"{path}: rate_limits must define {', '.join(RATE_LIMIT_KEYS)}.")
    for key in RATE_LIMIT_KEYS:
        value = rate_limits.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{path}: rate_limits.{key} must be a positive integer.")
    return BrowserPolicy(
        max_interval_bases=limit,
        min_maf=float(min_maf),
        frequency_bins=tuple(float(edge) for edge in edges),
        rate_limits={key: rate_limits[key] for key in RATE_LIMIT_KEYS},
    )


_policy = load_browser_policy()
MAX_QUERY_BASES = _policy.max_interval_bases
MIN_MAF = _policy.min_maf
FREQUENCY_BINS = _policy.frequency_bins
RATE_LIMITS = _policy.rate_limits
