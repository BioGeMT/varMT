"""
SQL queries for variant analysis.
Centralized location for all database queries.
"""

def get_variants_in_range():
    """
    Get all variants within a chromosomal range with genotype frequencies.
    
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
        c.sample_count,
        vf.alternate_allele_count,
        -- Calculate allele frequencies
        ROUND(
            (c.sample_count * 2 - vf.alternate_allele_count)::numeric / (c.sample_count * 2), 4
        ) as ref_allele_freq,
        ROUND(
            vf.alternate_allele_count::numeric / (c.sample_count * 2), 4
        ) as alt_allele_freq,
        -- Calculate genotype frequencies (Hardy-Weinberg equilibrium)
        ROUND(
            POWER((c.sample_count * 2 - vf.alternate_allele_count)::numeric / (c.sample_count * 2), 2), 4
        ) as homozygous_ref_freq,
        ROUND(
            2 * (vf.alternate_allele_count::numeric / (c.sample_count * 2)) * 
            ((c.sample_count * 2 - vf.alternate_allele_count)::numeric / (c.sample_count * 2)), 4
        ) as heterozygous_freq,
        ROUND(
            POWER(vf.alternate_allele_count::numeric / (c.sample_count * 2), 2), 4
        ) as homozygous_alt_freq
    FROM variant_locations vl
    JOIN variants v ON vl.id = v.variant_location_id
    JOIN variant_frequencies vf ON v.id = vf.variant_id
    JOIN collections c ON vf.collection_id = c.id
    WHERE vl.chromosome = %s
    ORDER BY vl.position, v.alternate_allele;
    """

def get_variants_by_gene():
    """
    Get all variants associated with a specific gene.
    
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
        vf.alternate_allele_count,
        c.sample_count,
        ROUND(vf.alternate_allele_count::numeric / (c.sample_count * 2), 4) as allele_frequency
    FROM genes g
    JOIN gene_locations gl ON g.id = gl.gene_id
    JOIN variant_locations vl ON gl.variant_location_id = vl.id
    JOIN variants v ON vl.id = v.variant_location_id
    JOIN variant_frequencies vf ON v.id = vf.variant_id
    JOIN collections c ON vf.collection_id = c.id
    WHERE g.symbol = %s
    ORDER BY vl.position;
    """

def get_variants_advanced_search():
    """
    Advanced search for variants by gene symbol and/or chromosomal position range.
    Supports flexible filtering with optional parameters.

    Returns: Base SQL query template for dynamic WHERE clause building
    """
    return """
    SELECT DISTINCT
        g.symbol as gene,
        vl.chromosome,
        vl.position,
        vl.reference_allele,
        v.alternate_allele,
        v.rs_id,
        c.sample_count,
        vf.alternate_allele_count,
        -- Calculate allele frequencies
        ROUND(
            (c.sample_count * 2 - vf.alternate_allele_count)::numeric / (c.sample_count * 2), 4
        ) as ref_allele_freq,
        ROUND(
            vf.alternate_allele_count::numeric / (c.sample_count * 2), 4
        ) as alt_allele_freq,
        -- Calculate genotype frequencies (Hardy-Weinberg equilibrium)
        ROUND(
            POWER((c.sample_count * 2 - vf.alternate_allele_count)::numeric / (c.sample_count * 2), 2), 4
        ) as homozygous_ref_freq,
        ROUND(
            2 * (vf.alternate_allele_count::numeric / (c.sample_count * 2)) *
            ((c.sample_count * 2 - vf.alternate_allele_count)::numeric / (c.sample_count * 2)), 4
        ) as heterozygous_freq,
        ROUND(
            POWER(vf.alternate_allele_count::numeric / (c.sample_count * 2), 2), 4
        ) as homozygous_alt_freq
    FROM variant_locations vl
    JOIN variants v ON vl.id = v.variant_location_id
    JOIN variant_frequencies vf ON v.id = vf.variant_id
    JOIN collections c ON vf.collection_id = c.id
    LEFT JOIN gene_locations gl ON vl.id = gl.variant_location_id
    LEFT JOIN genes g ON gl.gene_id = g.id
    {where_clause}
    ORDER BY vl.chromosome, vl.position, v.alternate_allele;
    """