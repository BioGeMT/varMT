# Genetic Variant Database Schema Documentation

## Table of Contents
- [Overview](#overview)
- [E/R Diagram](#er-diagram)
- [Table Descriptions](#table-descriptions)
- [Relationship Explanations](#relationship-explanations)
- [Sample Queries](#sample-queries)

## Overview

This database schema is designed to store genetic variants from VCF files, along with their frequencies across different collections (populations), while also enabling queries based on gene symbols.
## E/R Diagram

![Database e/r diagram](ERschema.png "Title")

## Table Descriptions

### 1. variant_locations
Stores the genomic coordinates where variants occur.

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| chromosome | text | Chromosome identifier (e.g., "chr1") |
| position | integer | Coordinate of the variant |
| reference_allele | text | Reference sequence at this position |
| genome_version | text | Reference genome build/version (e.g., "GRCh38") |

### 2. variants
Stores the actual genetic variants.

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| variant_location_id | integer | Foreign key to positions table |
| rs_id | text | dbSNP reference SNP ID (when available) |
| alternate_allele | text | Alternate sequence at this position |

### 3. collections
Stores information about different sample collections/populations.

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| sample_count | integer | Number of individual samples in this collection |

### 4. variant_frequencies
Junction table that stores the frequency data and genotype counts for variants across different collections.

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| variant_id | integer | Foreign key to variants table |
| collection_id | integer | Foreign key to collections table |
| alternate_allele_count | integer | Count of the alternate allele in this collection |
| allele_number | integer | Total number of alleles genotyped (2 × samples with non-missing genotypes) |
| hom_ref_count | integer | Number of homozygous reference genotypes (0/0) |
| hom_alt_count | integer | Number of homozygous alternate genotypes (1/1, 2/2, etc.) |
| het_count | integer | Number of heterozygous genotypes (0/1, 0/2, etc.) |
| missing_count | integer | Number of samples with missing genotypes (./., 0/., etc.) |

### 5. genes
Stores gene information.

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| symbol | text | Gene symbol (e.g., "BRCA1") |

### 6. gene_locations
Junction table that connects genes to genomic positions.

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Primary key |
| gene_id | integer | Foreign key to genes table |
| variant_location_id | integer | Foreign key to positions table |

## Relationship Explanations

### variant_locations ↔ variants (1:N)
A location can have multiple variants. This happens because at a single genomic position, there can be multiple possible alternate alleles. For instance, at position chr1:1000, the reference allele might be "A", but we could observe variants with "G", "T", or "C" alternate alleles.

### variants ↔ variants_frequencies (1:N)
A variant can have frequency data in multiple collections. This relationship allows us to track how common a particular variant is across different populations or sample groups (different collections may have different frequencies).

### collections ↔ variants_frequencies (1:N)
A collection can contain frequency data for many variants. This relationship allows us to keep track of the different allele frequencies per variant and sample.

### genes ↔ gene_positions (1:N)
A gene can span many positions in the genome.

### positions ↔ gene_positions (1:N)
A position can be associated with multiple genes. This accounts for overlapping genes.

## Sample Queries

### Calculate allele frequency for a specific variant in a specific collection:
```sql
SELECT v.rs_id, v.alternate_allele,
       vf.alternate_allele_count::float / vf.allele_number AS allele_frequency,
       vf.hom_ref_count,
       vf.het_count,
       vf.hom_alt_count,
       vf.missing_count
FROM variants v
JOIN variant_frequencies vf ON v.id = vf.variant_id
WHERE v.rs_id = 'rs123456';
```

### Find all variants in a specific gene with their frequencies:
```sql
SELECT g.symbol AS gene, v.rs_id, v.alternate_allele,
       vf.alternate_allele_count::float / vf.allele_number AS allele_frequency,
       vf.hom_ref_count,
       vf.het_count,
       vf.hom_alt_count
FROM genes g
JOIN gene_locations gp ON g.id = gp.gene_id
JOIN variant_locations vl ON gp.variant_location_id = vl.id
JOIN variants v ON vl.id = v.variant_location_id
JOIN variant_frequencies vf ON v.id = vf.variant_id
WHERE g.symbol = 'BRCA1';
```

### Calculate Hardy-Weinberg equilibrium expectations:
```sql
SELECT v.rs_id,
       vf.alternate_allele_count::float / vf.allele_number AS p_alt,
       vf.hom_ref_count AS observed_hom_ref,
       vf.het_count AS observed_het,
       vf.hom_alt_count AS observed_hom_alt,
       -- Expected counts under HWE
       ((vf.allele_number - vf.alternate_allele_count)::float / vf.allele_number)^2 * (vf.hom_ref_count + vf.het_count + vf.hom_alt_count) AS expected_hom_ref,
       2 * (vf.alternate_allele_count::float / vf.allele_number) * ((vf.allele_number - vf.alternate_allele_count)::float / vf.allele_number) * (vf.hom_ref_count + vf.het_count + vf.hom_alt_count) AS expected_het
FROM variants v
JOIN variant_frequencies vf ON v.id = vf.variant_id
WHERE v.rs_id = 'rs123456';
```
