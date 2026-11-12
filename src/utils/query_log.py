"""Per-user search log and rate limits."""

from queries.query_log_queries import count_recent_queries, insert_query_log
from utils.browser_policy import RATE_LIMITS

LIMIT_WINDOWS = {'per_minute': 'per minute', 'per_day': 'in 24 hours', 'per_month': 'in 30 days'}


def rate_limit_message(conn, user_id: str, limits: dict[str, int] = RATE_LIMITS) -> str | None:
    """Return why the user may not search now, or None if every limit allows it."""
    with conn.cursor() as cur:
        cur.execute(count_recent_queries(), (user_id,))
        counts = dict(zip(('per_minute', 'per_day', 'per_month'), cur.fetchone()))

    for key, window in LIMIT_WINDOWS.items():
        if counts[key] >= limits[key]:
            return f"You have reached the limit of {limits[key]:,} searches {window}. Please try again later."
    return None


def log_query(conn, user_id: str, search_type: str, chromosome: str, start: int, end: int,
              gene_symbol: str | None, allowed: bool, result_count: int | None = None) -> None:
    """Record one search attempt and commit it immediately."""
    with conn.cursor() as cur:
        cur.execute(insert_query_log(), (user_id, search_type, chromosome, start, end, gene_symbol, allowed, result_count))
    conn.commit()
