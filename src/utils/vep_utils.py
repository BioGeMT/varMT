from .setup_logging import setup_logging

logger = setup_logging()

def parse_csq_header(vcf_header) -> dict:
    """
    Parse CSQ field format from VCF header to create field name to index mapping.

    Args:
        vcf_header: pysam VCF header object

    Returns:
        dict: Mapping of field names to their index positions
    """
    csq_description = vcf_header.info['CSQ'].description
    # Extract field names from "Format: Field1|Field2|Field3..."
    csq_fields = csq_description.split("Format: ")[1].split("|")
    return {field: i for i, field in enumerate(csq_fields)}

def extract_gene_symbols_from_csq(csq_annotations: tuple, csq_index: dict) -> set:
    """
    Extract unique gene symbols from VEP CSQ annotation field.

    Args:
        csq_annotations (tuple): The CSQ annotations from record.info['CSQ']
        csq_index (dict): Mapping of CSQ field names to indices

    Returns:
        set: A set of unique gene symbols
    """
    if not csq_annotations:
        return set()

    gene_symbols = set()
    symbol_idx = csq_index.get('SYMBOL')

    if symbol_idx is None:
        logger.warning("SYMBOL field not found in CSQ header")
        return set()

    for annotation in csq_annotations:
        fields = annotation.split('|')
        if len(fields) > symbol_idx and fields[symbol_idx]:
            gene_symbols.add(fields[symbol_idx])

    return gene_symbols

def extract_rsid_from_csq(csq_annotations: tuple, csq_index: dict) -> str:
    """
    Extract the first/canonical rs_id from VEP CSQ Existing_variation field.

    Args:
        csq_annotations (tuple): The CSQ annotations from record.info['CSQ']
        csq_index (dict): Mapping of CSQ field names to indices

    Returns:
        str: The first rs_id found, or None if no rs_id exists
    """
    if not csq_annotations:
        return None

    existing_var_idx = csq_index.get('Existing_variation')

    if existing_var_idx is None:
        return None

    for annotation in csq_annotations:
        fields = annotation.split('|')
        if len(fields) > existing_var_idx and fields[existing_var_idx]:
            # Existing_variation can have multiple IDs separated by &
            var_field = fields[existing_var_idx]
            # Split by & and find the first rs_id
            for var_id in var_field.split('&'):
                if var_id.startswith('rs'):
                    return var_id

    return None

def extract_annotations_from_csq(csq_annotations: tuple, csq_index: dict) -> list:
    """
    Extract variant annotations from VEP CSQ field.

    Args:
        csq_annotations (tuple): The CSQ annotations from record.info['CSQ']
        csq_index (dict): Mapping of CSQ field names to indices

    Returns:
        list: List of annotation dictionaries with keys: transcript_id, hgvs_c, hgvs_p, consequence, impact
    """
    if not csq_annotations:
        return []

    # Get field indices
    transcript_idx = csq_index.get('Feature')
    hgvsc_idx = csq_index.get('HGVSc')
    hgvsp_idx = csq_index.get('HGVSp')
    consequence_idx = csq_index.get('Consequence')
    impact_idx = csq_index.get('IMPACT')

    annotations = []

    for annotation in csq_annotations:
        fields = annotation.split('|')

        # Extract fields (use None if field is empty or doesn't exist)
        transcript_id = fields[transcript_idx] if transcript_idx is not None and len(fields) > transcript_idx and fields[transcript_idx] else None
        hgvs_c = fields[hgvsc_idx] if hgvsc_idx is not None and len(fields) > hgvsc_idx and fields[hgvsc_idx] else None
        hgvs_p = fields[hgvsp_idx] if hgvsp_idx is not None and len(fields) > hgvsp_idx and fields[hgvsp_idx] else None
        consequence = fields[consequence_idx] if consequence_idx is not None and len(fields) > consequence_idx and fields[consequence_idx] else None
        impact = fields[impact_idx] if impact_idx is not None and len(fields) > impact_idx and fields[impact_idx] else None

        annotations.append({
            'transcript_id': transcript_id,
            'hgvs_c': hgvs_c,
            'hgvs_p': hgvs_p,
            'consequence': consequence,
            'impact': impact
        })

    return annotations