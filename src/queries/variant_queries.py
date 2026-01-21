"""
SQL queries for variant analysis.
Centralized location for all database queries.
"""

def get_variants_in_range():
    """
    Get all variants within a chromosomal range with genotype frequencies.
    Includes VEP annotations (multiple rows per variant if multiple transcripts).

    Parameters: chromosome, start_position, end_position
    Returns: DataFrame with variant details and frequency calculations
    """
    return """
    SELECT
        vl.chromosome,
        vl.position,
        vl.reference_allele,
        v.alternate_allele,
        v.rs_id,
        SUM(vf.alternate_allele_count) as alternate_allele_count,
        SUM(vf.allele_number) as allele_number,
        -- Calculate aggregated allele frequencies across all collections
        ROUND(
            (SUM(vf.allele_number) - SUM(vf.alternate_allele_count))::numeric / SUM(vf.allele_number), 4
        ) as ref_allele_freq,
        ROUND(
            SUM(vf.alternate_allele_count)::numeric / SUM(vf.allele_number), 4
        ) as alt_allele_freq,
        -- VEP annotation fields
        vva.transcript_id,
        vva.hgvs_c,
        vva.hgvs_p,
        vva.consequence,
        vva.impact
    FROM variant_locations vl
    JOIN variants v ON vl.id = v.variant_location_id
    JOIN variant_frequencies vf ON v.id = vf.variant_id
    LEFT JOIN variant_vep_annotations vva ON v.id = vva.variant_id
    WHERE vl.chromosome = %s
    GROUP BY vl.chromosome, vl.position, vl.reference_allele, v.alternate_allele, v.rs_id,
             vva.transcript_id, vva.hgvs_c, vva.hgvs_p, vva.consequence, vva.impact
    ORDER BY vl.position, v.alternate_allele, vva.impact DESC NULLS LAST;
    """

def get_variants_by_gene():
    """
    Get all variants associated with a specific gene.
    Includes VEP annotations (multiple rows per variant if multiple transcripts).

    Parameters: gene_symbol
    Returns: DataFrame with variants in the specified gene
    """
    return """
    SELECT
        g.symbol as gene,
        vl.chromosome,
        vl.position,
        vl.reference_allele,
        v.alternate_allele,
        v.rs_id,
        SUM(vf.alternate_allele_count) as alternate_allele_count,
        SUM(vf.allele_number) as allele_number,
        ROUND(SUM(vf.alternate_allele_count)::numeric / SUM(vf.allele_number), 4) as allele_frequency,
        -- VEP annotation fields
        vva.transcript_id,
        vva.hgvs_c,
        vva.hgvs_p,
        vva.consequence,
        vva.impact
    FROM genes g
    JOIN gene_locations gl ON g.id = gl.gene_id
    JOIN variant_locations vl ON gl.variant_location_id = vl.id
    JOIN variants v ON vl.id = v.variant_location_id
    JOIN variant_frequencies vf ON v.id = vf.variant_id
    LEFT JOIN variant_vep_annotations vva ON v.id = vva.variant_id
    WHERE g.symbol = %s
    GROUP BY g.symbol, vl.chromosome, vl.position, vl.reference_allele, v.alternate_allele, v.rs_id,
             vva.transcript_id, vva.hgvs_c, vva.hgvs_p, vva.consequence, vva.impact
    ORDER BY vl.position, v.alternate_allele, vva.impact DESC NULLS LAST;
    """

def get_variants_advanced_search():
    """
    Advanced search for variants by gene symbol and/or chromosomal position range.
    Supports flexible filtering with optional parameters.
    Includes VEP annotations (multiple rows per variant if multiple transcripts).

    Returns: Base SQL query template for dynamic WHERE and HAVING clause building
    """
    return """
    SELECT
        g.symbol as gene,
        vl.chromosome,
        vl.position,
        vl.reference_allele,
        v.alternate_allele,
        v.rs_id,
        SUM(vf.alternate_allele_count) as alternate_allele_count,
        SUM(vf.allele_number) as allele_number,
        -- Calculate aggregated allele frequencies across all collections
        ROUND(
            (SUM(vf.allele_number) - SUM(vf.alternate_allele_count))::numeric / SUM(vf.allele_number), 4
        ) as ref_allele_freq,
        ROUND(
            SUM(vf.alternate_allele_count)::numeric / SUM(vf.allele_number), 4
        ) as alt_allele_freq,
        -- VEP annotation fields
        vva.transcript_id,
        vva.hgvs_c,
        vva.hgvs_p,
        vva.consequence,
        vva.impact
    FROM variant_locations vl
    JOIN variants v ON vl.id = v.variant_location_id
    JOIN variant_frequencies vf ON v.id = vf.variant_id
    LEFT JOIN gene_locations gl ON vl.id = gl.variant_location_id
    LEFT JOIN genes g ON gl.gene_id = g.id
    LEFT JOIN variant_vep_annotations vva ON v.id = vva.variant_id
    {where_clause}
    GROUP BY g.symbol, vl.chromosome, vl.position, vl.reference_allele, v.alternate_allele, v.rs_id,
             vva.transcript_id, vva.hgvs_c, vva.hgvs_p, vva.consequence, vva.impact
    {having_clause}
    ORDER BY vl.chromosome, vl.position, v.alternate_allele, vva.impact DESC NULLS LAST;
    """