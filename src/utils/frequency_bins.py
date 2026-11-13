"""Frequency bins shown instead of exact allele frequencies."""

from utils.browser_policy import FREQUENCY_BINS


def frequency_bins(edges: tuple[float, ...] = FREQUENCY_BINS) -> list[tuple[float, float, str]]:
    """Return (lower, upper, label) for each bin; only the last bin includes its upper edge."""
    bins = []
    for i, (lower, upper) in enumerate(zip(edges, edges[1:])):
        last = i == len(edges) - 2
        bins.append((lower, upper, f"{lower:.0%} to {'' if last else '<'}{upper:.0%}"))
    return bins


def frequency_bin(frequency: float, edges: tuple[float, ...] = FREQUENCY_BINS) -> str:
    """Return the label of the bin containing the frequency."""
    bins = frequency_bins(edges)
    for lower, upper, label in bins:
        if lower <= frequency < upper:
            return label
    if frequency == bins[-1][1]:
        return bins[-1][2]
    raise ValueError(f"Frequency {frequency} is outside the displayed bins.")


def bin_range(first_label: str, last_label: str, edges: tuple[float, ...] = FREQUENCY_BINS) -> tuple[float, float, bool]:
    """Return (lower edge, upper edge, upper edge included) for a range of bins chosen by label."""
    bins = frequency_bins(edges)
    labels = [label for _, _, label in bins]
    first, last = labels.index(first_label), labels.index(last_label)
    return bins[first][0], bins[last][1], last == len(bins) - 1
