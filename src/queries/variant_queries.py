"""
SQL queries for variant analysis.
Centralized location for all database queries.
"""

def get_variants_advanced_search():
    """
    Advanced search for variants by gene symbol and/or chromosomal position range.
    Supports flexible filtering with optional parameters.
    Includes VEP annotations (multiple rows per variant if multiple transcripts).

    Frequencies are aggregated once per variant across collections, separately from annotations.
    Collections without a row for a variant are ambiguous (all reference or no data), so the
    true AF is bounded:
        af_max = AC / AN                                  (absent collections had no data)
        af_min = AC / (AN + 2 * samples in absent ones)   (absent collections were all reference)
    Only variants with af_min >= min_maf and af_max <= 1 - min_maf are returned.

    Returns: SQL template with {where_clause} and {freq_filter} placeholders.
    Parameter order: where_clause params, min_maf, min_maf, freq_filter params.
    """
    return """
    WITH selected AS (
        SELECT DISTINCT v.id AS variant_id, g.symbol AS gene
        FROM variant_locations vl
        JOIN variants v ON vl.id = v.variant_location_id
        LEFT JOIN gene_locations gl ON vl.id = gl.variant_location_id
        LEFT JOIN genes g ON gl.gene_id = g.id
        {where_clause}
    ),
    stats AS (
        SELECT
            vf.variant_id,
            SUM(vf.alternate_allele_count) AS ac,
            SUM(vf.allele_number) AS an,
            SUM(c.sample_count) AS present_samples
        FROM variant_frequencies vf
        JOIN collections c ON c.id = vf.collection_id
        WHERE vf.variant_id IN (SELECT variant_id FROM selected)
        GROUP BY vf.variant_id
    ),
    bounds AS (
        SELECT
            variant_id,
            ac::numeric / NULLIF(an, 0) AS af_max,
            ac::numeric / NULLIF(an + 2 * ((SELECT SUM(sample_count) FROM collections) - present_samples), 0) AS af_min
        FROM stats
    )
    SELECT
        s.gene,
        vl.chromosome,
        vl.position,
        vl.reference_allele,
        v.alternate_allele,
        v.rs_id,
        ROUND(1 - b.af_max, 4) AS ref_allele_freq,
        ROUND(b.af_max, 4) AS alt_allele_freq,
        vva.transcript_id,
        vva.hgvs_c,
        vva.hgvs_p,
        vva.consequence,
        vva.impact
    FROM selected s
    JOIN bounds b ON b.variant_id = s.variant_id
    JOIN variants v ON v.id = s.variant_id
    JOIN variant_locations vl ON vl.id = v.variant_location_id
    LEFT JOIN (
        SELECT DISTINCT variant_id, transcript_id, hgvs_c, hgvs_p, consequence, impact
        FROM variant_vep_annotations
        WHERE variant_id IN (SELECT variant_id FROM selected)
    ) vva ON vva.variant_id = s.variant_id
    WHERE b.af_min >= %s AND b.af_max <= 1 - %s
    {freq_filter}
    ORDER BY vl.chromosome, vl.position, v.alternate_allele, vva.impact DESC NULLS LAST;
    """