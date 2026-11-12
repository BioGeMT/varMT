"""
SQL queries for the per-user search log.
"""

def insert_query_log():
    """
    Record one search attempt.

    Parameter order: user_id, search_type, chromosome, start_position, end_position,
    gene_symbol, allowed, result_count.
    """
    return """
    INSERT INTO query_log
        (user_id, search_type, chromosome, start_position, end_position, gene_symbol, allowed, result_count)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """

def count_recent_queries():
    """
    Count a user's allowed searches in the last minute, 24 hours and 30 days.
    Blocked attempts are not counted, so retrying while blocked does not extend the block.

    Parameter order: user_id.
    """
    return """
    SELECT
        COUNT(*) FILTER (WHERE queried_at > now() - interval '1 minute') AS per_minute,
        COUNT(*) FILTER (WHERE queried_at > now() - interval '24 hours') AS per_day,
        COUNT(*) AS per_month
    FROM query_log
    WHERE user_id = %s AND allowed AND queried_at > now() - interval '30 days';
    """
