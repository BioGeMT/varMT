from .setup_logging import setup_logging

import pandas

logger = setup_logging()

def load_gene_mapping() -> dict:
    """
    Load gene mapping from TSV file.
    The file should contain (at least) two columns: "Ensembl gene ID" and "Gene name".

    Returns:
        gene_mapping (dict): A dictionary mapping Ensembl gene IDs to gene names.
    """

    df = pandas.read_csv("res/ensembl_gene_mapping.tsv", sep="\t")
    
    df = df.dropna(subset=["Gene name"]) # Drop not mapping genes rows

    gene_mapping = df.set_index("Gene stable ID")["Gene name"].to_dict()

    logger.info(f"Loaded {len(gene_mapping)} gene mappings from res/ensembl_gene_mapping.tsv")

    return gene_mapping

def map_gene_symbols(ensembl_gene_id: str, gene_mapping: dict) -> list:
    """
    Map Ensembl gene ID to gene symbols using the provided mapping.

    Args:
        ensembl_gene_id (str): The Ensembl gene ID to map.
        gene_mapping (dict): The dictionary containing the mapping.

    Returns:
        list: A list of gene symbols corresponding to the Ensembl gene ID.
    """

    symbol = gene_mapping.get(ensembl_gene_id, None)
    if symbol is None:
        return []
    return [symbol]