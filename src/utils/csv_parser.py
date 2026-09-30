import re
import pandas as pd
from typing import List, Tuple
from .browser_policy import MAX_QUERY_BASES
from .query_limits import validate_query_window

REQUIRED_COLUMNS = ['gene_symbol', 'rs_id', 'chromosome', 'start_position', 'end_position']

def get_required_columns():
    return REQUIRED_COLUMNS

def validate_csv_columns(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """
    Check that all required columns are in the given CSV, and that the provided columns are in the expected column names

    Args:
        df: DataFrame loaded from CSV

    Returns:
        Tuple of lists
    """
    errors_required_not_in = []
    errors_provided_not_in = []
    columns_provided = set(df.columns)

    for required_column in REQUIRED_COLUMNS:
        if required_column not in columns_provided:
            errors_required_not_in.append(required_column)

    for column_provided in columns_provided:
        if column_provided.lower() not in REQUIRED_COLUMNS:
            errors_provided_not_in.append(column_provided)

    return errors_required_not_in, errors_provided_not_in


def validate_csv_data(df: pd.DataFrame) -> List[str]:
    """
    Validate CSV data for correctness and valid query combinations.

    Args:
        df: DataFrame loaded from CSV

    Returns:
        List of error messages (empty if validation passes)

    Validation rules:
        - Each row requires chromosome, start_position, and end_position
        - Gene symbols and rsIDs optionally narrow the interval
        - All rows must fit within the configured query limit on one chromosome
        - Chromosome values must be valid (1-22, X, Y, MT)
        - Position values must be positive integers
        - start_position <= end_position (can be equal for single position)
        - rs_id must be in format rs<digits> (e.g. rs80357906)
    """
    errors = []
    windows = []
    if df.empty:
        return ["CSV must contain at least one search interval."]

    for idx, row in df.iterrows():
        row_num = idx + 2  # skip header

        # Check what columns are present in this row (non-null)
        has_rs_id = pd.notna(row.get('rs_id')) and str(row.get('rs_id', '')).strip()
        has_chr = pd.notna(row.get('chromosome')) and str(row.get('chromosome', '')).strip()
        has_start = pd.notna(row.get('start_position'))
        has_end = pd.notna(row.get('end_position'))

        if not (has_chr and has_start and has_end):
            errors.append(f"Row {row_num}: Chromosome, start_position, and end_position are required, including for gene and rsID searches.")
            continue
        try:
            windows.append(validate_query_window(row['chromosome'], row['start_position'], row['end_position'], limit=MAX_QUERY_BASES))
        except ValueError as error:
            errors.append(f"Row {row_num}: {error}")
            continue

        # Validate rs_id format
        if has_rs_id:
            rs_value = str(row['rs_id']).strip()
            if not re.match(r'^rs\d+$', rs_value):
                errors.append(f"Row {row_num}: rs_id '{rs_value}' is not valid. Must be in format rs<digits> (e.g. rs80357906)")

    if windows and not errors:
        chromosomes = {window[0] for window in windows}
        if len(chromosomes) != 1:
            errors.append(f"All CSV rows must use the same chromosome and fit within one {MAX_QUERY_BASES / 1000:g} kb window.")
        else:
            try:
                validate_query_window(windows[0][0], min(w[1] for w in windows), max(w[2] for w in windows), limit=MAX_QUERY_BASES)
            except ValueError as error:
                errors.append(f"Combined CSV search: {error}")

    return errors


def build_query_conditions(df: pd.DataFrame) -> Tuple[List[str], List]:
    """
    Build SQL WHERE conditions from CSV rows.
    Each row becomes a set of conditions combined with OR.

    Args:
        df: DataFrame loaded from CSV (must be validated first)

    Returns:
        Tuple of (where_conditions, params):
            - where_conditions: List of SQL condition strings
            - params: List of parameter values for parameterized query

    Example output:
        where_conditions = ["(vl.chromosome = %s AND vl.position BETWEEN %s AND %s)"]
        params = ['17', 43044295, 43044295]
    """
    errors = validate_csv_data(df)
    if errors:
        raise ValueError("; ".join(errors))
    conditions = []
    params = []

    for _, row in df.iterrows():
        row_conditions = []

        # Check what columns are present in this row (non-null)
        has_gene = pd.notna(row.get('gene_symbol')) and str(row.get('gene_symbol', '')).strip()
        has_rs_id = pd.notna(row.get('rs_id')) and str(row.get('rs_id', '')).strip()
        has_chr = pd.notna(row.get('chromosome')) and str(row.get('chromosome', '')).strip()
        has_start = pd.notna(row.get('start_position'))
        has_end = pd.notna(row.get('end_position'))

        # Build gene condition
        if has_gene:
            row_conditions.append("UPPER(g.symbol) = UPPER(%s)")
            params.append(str(row['gene_symbol']).strip())

        # Build rs_id condition
        if has_rs_id:
            row_conditions.append("v.rs_id = %s")
            params.append(str(row['rs_id']).strip())

        # Build position condition
        if has_chr and has_start and has_end:
            row_conditions.append("vl.chromosome = %s AND vl.position BETWEEN %s AND %s")
            params.extend([
                str(row['chromosome']).strip(),
                int(row['start_position']),
                int(row['end_position'])
            ])

        # Combine conditions for this row with AND
        if row_conditions:
            combined = " AND ".join(row_conditions)
            conditions.append(f"({combined})")

    return conditions, params
