"""
Variant frequency aggregation tests.
Tests that allele frequencies update correctly when the same variant
appears across multiple collections/populations.
"""

import psycopg2
import pytest
from decimal import Decimal

from utils.db_utils import (
    insert_variant_location,
    insert_variant,
    insert_collection,
    insert_variant_frequency,
)

from queries.variant_queries import get_variants_in_range


@pytest.fixture()
def db_conn(setup_test_database):
    """Provide a database connection that rolls back after each test."""
    conn = psycopg2.connect(**setup_test_database)
    yield conn
    conn.rollback()
    conn.close()


def _insert_variant_with_frequency(cur, chrom, pos, ref, alt, genome, sample_count, ac, an,
                                    hom_ref=0, hom_alt=0, het=0, missing=0):
    """Helper to insert a variant location, variant, collection, and frequency row."""
    cur.execute(insert_variant_location(), (chrom, pos, ref, genome))
    var_location_id = cur.fetchone()[0]

    cur.execute(insert_variant(), (var_location_id, None, alt))
    variant_id = cur.fetchone()[0]

    cur.execute(insert_collection(), (sample_count,))
    collection_id = cur.fetchone()[0]

    cur.execute(insert_variant_frequency(), (
        variant_id, collection_id, ac, an, hom_ref, hom_alt, het, missing
    ))

    return variant_id, collection_id


def _query_variant_frequency(cur, chrom):
    """Run the aggregation query and return results as list of dicts."""
    query = get_variants_in_range()
    cur.execute(query, (chrom,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


class TestVariantFrequencyAggregation:
    """Tests for allele frequency changes across multiple collections."""

    def test_single_collection_frequency(self, db_conn):
        """Frequency with one collection equals AC/AN for that collection."""
        cur = db_conn.cursor()

        _insert_variant_with_frequency(
            cur, chrom='chrTest', pos=100, ref='A', alt='T',
            genome='GRCh38', sample_count=50,
            ac=10, an=100, hom_ref=40, hom_alt=5, het=0, missing=5
        )

        results = _query_variant_frequency(cur, 'chrTest')
        assert len(results) == 1
        assert results[0]['alt_allele_freq'] == Decimal('0.1000')
        assert results[0]['ref_allele_freq'] == Decimal('0.9000')

        cur.close()

    def test_frequency_changes_with_second_collection(self, db_conn):
        """
        After adding a second collection with the same variant,
        the aggregated frequency reflects both populations.
        """
        cur = db_conn.cursor()

        # Collection 1: AC=10, AN=100 -> freq = 0.10
        _insert_variant_with_frequency(
            cur, chrom='chrTest', pos=200, ref='A', alt='G',
            genome='GRCh38', sample_count=50,
            ac=10, an=100, hom_ref=40, hom_alt=5, het=0, missing=5
        )

        results = _query_variant_frequency(cur, 'chrTest')
        freq_after_first = results[0]['alt_allele_freq']
        assert freq_after_first == Decimal('0.1000')

        # Collection 2: same variant, AC=30, AN=200 -> freq = 0.15
        # Aggregated should be (10+30)/(100+200) = 40/300 = 0.1333
        _insert_variant_with_frequency(
            cur, chrom='chrTest', pos=200, ref='A', alt='G',
            genome='GRCh38', sample_count=100,
            ac=30, an=200, hom_ref=80, hom_alt=10, het=10, missing=0
        )

        results = _query_variant_frequency(cur, 'chrTest')
        freq_after_second = results[0]['alt_allele_freq']

        assert freq_after_second != freq_after_first, (
            "Frequency should change after adding a second collection"
        )
        assert freq_after_second == Decimal('0.1333')

        cur.close()

    def test_frequency_aggregation_three_collections(self, db_conn):
        """Frequency aggregates correctly across three collections."""
        cur = db_conn.cursor()

        # Collection 1: AC=5, AN=50
        _insert_variant_with_frequency(
            cur, chrom='chrTest', pos=300, ref='C', alt='T',
            genome='GRCh38', sample_count=25,
            ac=5, an=50, hom_ref=20, hom_alt=2, het=1, missing=2
        )

        # Collection 2: AC=15, AN=100
        _insert_variant_with_frequency(
            cur, chrom='chrTest', pos=300, ref='C', alt='T',
            genome='GRCh38', sample_count=50,
            ac=15, an=100, hom_ref=40, hom_alt=5, het=5, missing=0
        )

        # Collection 3: AC=20, AN=150
        _insert_variant_with_frequency(
            cur, chrom='chrTest', pos=300, ref='C', alt='T',
            genome='GRCh38', sample_count=75,
            ac=20, an=150, hom_ref=60, hom_alt=5, het=10, missing=0
        )

        results = _query_variant_frequency(cur, 'chrTest')
        # (5+15+20) / (50+100+150) = 40/300 = 0.1333
        assert results[0]['alt_allele_freq'] == Decimal('0.1333')

        cur.close()
