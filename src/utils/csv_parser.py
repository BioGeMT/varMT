import pandas as pd
from typing import Dict, List, Optional, Tuple


# Standard column names (case-insensitive)
REQUIRED_COLUMNS = {
    'gene_symbol': 'gene_symbol',
    'chromosome': 'chromosome',
    'start_position': 'start_position',
    'end_position': 'end_position'
}


def detect_csv_format(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Detect which standard columns are present in the CSV.
    Column names must match exactly (case-insensitive).

    Args:
        df: DataFrame loaded from CSV

    Returns:
        Dictionary mapping standard column names to actual column names in CSV,
        or None if column is not present

    Raises:
        ValueError: If CSV has unrecognized columns or invalid format

    Example:
        {
            'gene_symbol': 'gene_symbol',
            'chromosome': 'Chromosome',
            'start_position': 'start_position',
            'end_position': 'end_position'
        }
    """
    columns_lower = {col.lower(): col for col in df.columns}

    detected = {}
    for standard_name in REQUIRED_COLUMNS.keys():
        # Check if this column exists (case-insensitive)
        actual_name = columns_lower.get(standard_name.lower())
        detected[standard_name] = actual_name

    return detected


def validate_csv_data(df: pd.DataFrame, detected_format: Dict[str, Optional[str]]) -> List[str]:
    """
    Validate CSV data for correctness and valid query combinations.

    Args:
        df: DataFrame loaded from CSV
        detected_format: Output from detect_csv_format()

    Returns:
        List of error messages (empty if validation passes)

    Validation rules:
        - Each row must have at least one valid query type
        - Chromosome + position queries require both start_position and end_position
        - Chromosome values must be valid (1-22, X, Y, MT)
        - Position values must be positive integers
        - start_position <= end_position (can be equal for single position)
        - Gene symbols must be non-empty strings
    """
    errors = []

    # Valid chromosome values
    valid_chromosomes = set([str(i) for i in range(1, 23)] + ['X', 'Y', 'MT', 'chrX', 'chrY', 'chrMT'])
    valid_chromosomes.update([f'chr{i}' for i in range(1, 23)])

    # Get actual column names from detected format
    gene_col = detected_format.get('gene_symbol')
    chr_col = detected_format.get('chromosome')
    start_col = detected_format.get('start_position')
    end_col = detected_format.get('end_position')

    for idx, row in df.iterrows():
        row_num = idx + 2  # +2 because: +1 for header, +1 for 0-indexed

        # Check what columns are present in this row (non-null)
        has_gene = gene_col and pd.notna(row.get(gene_col))
        has_chr = chr_col and pd.notna(row.get(chr_col))
        has_start = start_col and pd.notna(row.get(start_col))
        has_end = end_col and pd.notna(row.get(end_col))

        # Rule 1: Each row must have at least one valid query type
        if not (has_gene or (has_chr and has_start and has_end)):
            errors.append(f"Row {row_num}: Must have gene_symbol OR (chromosome + start_position + end_position)")
            continue

        # Rule 2: If using position queries, must have chromosome AND both start and end
        if has_chr and not (has_start and has_end):
            errors.append(f"Row {row_num}: Chromosome queries require both start_position and end_position")
            continue

        if (has_start or has_end) and not has_chr:
            errors.append(f"Row {row_num}: start_position and end_position require chromosome")
            continue

        # Validate chromosome value
        if has_chr:
            chr_value = str(row[chr_col]).strip()
            if chr_value not in valid_chromosomes:
                errors.append(f"Row {row_num}: Invalid chromosome '{chr_value}'. Must be 1-22, X, Y, or MT")

        # Validate start and end positions
        if has_start and has_end:
            try:
                start_value = int(row[start_col])
                end_value = int(row[end_col])

                if start_value <= 0 or end_value <= 0:
                    errors.append(f"Row {row_num}: start_position and end_position must be positive integers")
                elif start_value > end_value:
                    errors.append(f"Row {row_num}: start_position ({start_value}) must be <= end_position ({end_value})")
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: start_position and end_position must be valid integers")

        # Validate gene symbol is non-empty
        if has_gene:
            gene_value = str(row[gene_col]).strip()
            if not gene_value:
                errors.append(f"Row {row_num}: gene_symbol cannot be empty")

    return errors


def build_query_conditions(df: pd.DataFrame, detected_format: Dict[str, Optional[str]]) -> Tuple[List[str], List]:
    """
    Build SQL WHERE conditions from CSV rows.
    Each row becomes a set of conditions combined with OR.

    Args:
        df: DataFrame loaded from CSV (must be validated first)
        detected_format: Output from detect_csv_format()

    Returns:
        Tuple of (where_conditions, params):
            - where_conditions: List of SQL condition strings
            - params: List of parameter values for parameterized query

    Example output:
        where_conditions = [
            "(UPPER(g.symbol) = UPPER(%s))",
            "(vl.chromosome = %s AND vl.position BETWEEN %s AND %s)",
            "(UPPER(g.symbol) = UPPER(%s) AND vl.chromosome = %s AND vl.position BETWEEN %s AND %s)"
        ]
        params = ['BRCA1', '17', 43000000, 44000000, 'TP53', '17', 7675088, 7675088]
    """
    conditions = []
    params = []

    # Get actual column names from detected format
    gene_col = detected_format.get('gene_symbol')
    chr_col = detected_format.get('chromosome')
    start_col = detected_format.get('start_position')
    end_col = detected_format.get('end_position')

    for idx, row in df.iterrows():
        row_conditions = []

        # Check what columns are present in this row (non-null)
        has_gene = gene_col and pd.notna(row.get(gene_col))
        has_chr = chr_col and pd.notna(row.get(chr_col))
        has_start = start_col and pd.notna(row.get(start_col))
        has_end = end_col and pd.notna(row.get(end_col))

        # Build gene condition
        if has_gene:
            row_conditions.append("UPPER(g.symbol) = UPPER(%s)")
            params.append(str(row[gene_col]).strip())

        # Build position condition
        if has_chr and has_start and has_end:
            row_conditions.append("vl.chromosome = %s AND vl.position BETWEEN %s AND %s")
            params.extend([
                str(row[chr_col]).strip(),
                int(row[start_col]),
                int(row[end_col])
            ])

        # Combine conditions for this row with AND
        if row_conditions:
            combined = " AND ".join(row_conditions)
            conditions.append(f"({combined})")

    return conditions, params
