import re
import pandas as pd
from typing import List, Tuple

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
        - Each row must have at least one valid query type
        - Valid query types: gene_symbol | rs_id | (chromosome + start_position + end_position)
        - Chromosome + position queries require both start_position and end_position
        - Chromosome values must be valid (1-22, X, Y, MT)
        - Position values must be positive integers
        - start_position <= end_position (can be equal for single position)
        - rs_id must be in format rs<digits> (e.g. rs80357906)
    """
    errors = []

    # Valid chromosome values
    valid_chromosomes = set([str(i) for i in range(1, 23)] + ['X', 'Y', 'MT', 'chrX', 'chrY', 'chrMT'])
    valid_chromosomes.update([f'chr{i}' for i in range(1, 23)])

    for idx, row in df.iterrows():
        row_num = idx + 2  # skip header

        # Check what columns are present in this row (non-null)
        has_gene = pd.notna(row.get('gene_symbol')) and str(row.get('gene_symbol', '')).strip()
        has_rs_id = pd.notna(row.get('rs_id')) and str(row.get('rs_id', '')).strip()
        has_chr = pd.notna(row.get('chromosome')) and str(row.get('chromosome', '')).strip()
        has_start = pd.notna(row.get('start_position'))
        has_end = pd.notna(row.get('end_position'))

        # Rule 1: Each row must have at least one valid query type
        if not (has_gene or has_rs_id or (has_chr and has_start and has_end)):
            errors.append(f"Row {row_num}: Must have gene_symbol OR rs_id OR (chromosome + start_position + end_position)")
            continue

        # Rule 2: If using position queries, must have chromosome AND both start and end
        if has_chr and not (has_start and has_end):
            errors.append(f"Row {row_num}: Chromosome queries require both start_position and end_position")
            continue

        if (has_start or has_end) and not has_chr:
            errors.append(f"Row {row_num}: start_position and end_position require chromosome")
            continue

        # Validate rs_id format
        if has_rs_id:
            rs_value = str(row['rs_id']).strip()
            if not re.match(r'^rs\d+$', rs_value):
                errors.append(f"Row {row_num}: rs_id '{rs_value}' is not valid. Must be in format rs<digits> (e.g. rs80357906)")

        # Validate chromosome value
        if has_chr:
            chr_value = str(row['chromosome']).strip()
            if chr_value not in valid_chromosomes:
                errors.append(f"Row {row_num}: Invalid chromosome '{chr_value}'. Must be 1-22, X, Y, or MT")

        # Validate start and end positions
        if has_start and has_end:
            try:
                start_value = int(row['start_position'])
                end_value = int(row['end_position'])

                if start_value <= 0 or end_value <= 0:
                    errors.append(f"Row {row_num}: start_position and end_position must be positive integers")
                elif start_value > end_value:
                    errors.append(f"Row {row_num}: start_position ({start_value}) must be <= end_position ({end_value})")
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: start_position and end_position must be valid integers")

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
        where_conditions = [
            "(UPPER(g.symbol) = UPPER(%s))",
            "(v.rs_id = %s)",
            "(vl.chromosome = %s AND vl.position BETWEEN %s AND %s)",
        ]
        params = ['BRCA1', 'rs80357906', '17', 43000000, 44000000]
    """
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
