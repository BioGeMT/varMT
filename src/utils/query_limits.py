VALID_CHROMOSOMES = {str(i) for i in range(1, 23)} | {'X', 'Y', 'MT'}


def validate_query_window(chromosome, start, end, limit: int) -> tuple[str, int, int]:
    """Require one chromosome and an inclusive interval within the supplied limit."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Query limit must be a positive integer.")
    if chromosome is None or not str(chromosome).strip() or start is None or end is None:
        raise ValueError("Chromosome, start position, and end position are required for every search.")

    chromosome = str(chromosome).strip()
    if chromosome.removeprefix('chr') not in VALID_CHROMOSOMES:
        raise ValueError("Chromosome must be 1-22, X, Y, or MT (optionally prefixed with chr).")

    positions = []
    for value in (start, end):
        try:
            position = int(value)
            if isinstance(value, bool) or float(value) != position or position < 1:
                raise ValueError
        except (ValueError, TypeError, OverflowError):
            raise ValueError("Start and end positions must be positive integers.") from None
        positions.append(position)

    start, end = positions
    if start > end:
        raise ValueError("Start position must be less than or equal to end position.")
    if end - start + 1 > limit:
        raise ValueError(f"Search intervals must be at most {limit:,} bases (end - start + 1).")
    return chromosome, start, end
