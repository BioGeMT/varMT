"""
Release-rule tests for the advanced search query.
Variants are shown only if af_min >= min_maf and af_max <= 1 - min_maf, where collections
without a row for the variant may be all reference (af_min) or have no data (af_max).
"""

from decimal import Decimal

from utils.db_utils import (
    insert_variant_location,
    insert_variant,
    insert_collection,
    insert_variant_frequency,
    insert_variant_vep_annotation,
)

from queries.variant_queries import get_variants_advanced_search

MIN_MAF = 0.05  # Fixed test policy, independent of deployment configuration.


def _collection(cur, sample_count):
    cur.execute(insert_collection(), (sample_count,))
    return cur.fetchone()[0]


def _variant(cur, pos):
    cur.execute(insert_variant_location(), ('chrTest', pos, 'A', 'GRCh38'))
    cur.execute(insert_variant(), (cur.fetchone()[0], None, 'T'))
    return cur.fetchone()[0]


def _frequency(cur, variant_id, collection_id, ac, an):
    cur.execute(insert_variant_frequency(), (variant_id, collection_id, ac, an, 0, 0, 0, 0))


def _search(cur, min_maf=MIN_MAF, freq_filter="", freq_params=()):
    query = get_variants_advanced_search().format(where_clause="WHERE vl.chromosome = %s", freq_filter=freq_filter)
    cur.execute(query, ('chrTest', min_maf, min_maf, *freq_params))
    columns = [desc[0] for desc in cur.description]
    return {row['position']: row for row in (dict(zip(columns, r)) for r in cur.fetchall())}


def test_threshold_boundaries_single_collection(db_conn):
    cur = db_conn.cursor()
    collection = _collection(cur, 100)
    for pos, ac in [(100, 9), (101, 10), (102, 190), (103, 191), (104, 196)]:
        _frequency(cur, _variant(cur, pos), collection, ac, 200)
    _frequency(cur, _variant(cur, 105), collection, 0, 0)

    # 4.5% and 95.5% are rare; 98% means a rare reference allele; AN = 0 has no frequency
    assert sorted(_search(cur)) == [101, 102]


def test_variant_in_all_collections_uses_pooled_frequency(db_conn):
    cur = db_conn.cursor()
    a, b = _collection(cur, 100), _collection(cur, 300)
    variant = _variant(cur, 200)
    _frequency(cur, variant, a, 20, 200)
    _frequency(cur, variant, b, 30, 600)

    assert _search(cur)[200]['alt_allele_freq'] == Decimal('0.0625')


def test_variant_missing_from_collection_uses_lower_bound(db_conn):
    cur = db_conn.cursor()
    a = _collection(cur, 100)
    _collection(cur, 300)
    _frequency(cur, _variant(cur, 300), a, 20, 200)   # local 10%, af_min 20/800 = 2.5%
    _frequency(cur, _variant(cur, 301), a, 100, 200)  # local 50%, af_min 100/800 = 12.5%

    results = _search(cur)
    assert sorted(results) == [301]
    assert results[301]['alt_allele_freq'] == Decimal('0.5000')


def test_adding_collection_without_variant_hides_it(db_conn):
    cur = db_conn.cursor()
    a = _collection(cur, 100)
    _frequency(cur, _variant(cur, 400), a, 10, 200)  # 5%
    assert 400 in _search(cur)

    _collection(cur, 300)
    assert 400 not in _search(cur)


def test_duplicated_annotations_do_not_change_frequency(db_conn):
    cur = db_conn.cursor()
    a, b = _collection(cur, 100), _collection(cur, 300)
    variant = _variant(cur, 500)
    _frequency(cur, variant, a, 20, 200)
    _frequency(cur, variant, b, 30, 600)
    for _ in range(2):  # ingestion inserts annotations once per collection
        for transcript in ['T1', 'T2', 'T3']:
            cur.execute(insert_variant_vep_annotation(), (variant, transcript, None, None, 'missense_variant', 'MODERATE'))

    query = get_variants_advanced_search().format(where_clause="WHERE vl.chromosome = %s", freq_filter="")
    cur.execute(query, ('chrTest', MIN_MAF, MIN_MAF))
    rows = cur.fetchall()
    freq_index = [desc[0] for desc in cur.description].index('alt_allele_freq')
    assert len(rows) == 3
    assert {row[freq_index] for row in rows} == {Decimal('0.0625')}


def test_user_frequency_filter_narrows_released_variants(db_conn):
    cur = db_conn.cursor()
    collection = _collection(cur, 100)
    for pos, ac in [(600, 20), (601, 100)]:  # 10%, 50%
        _frequency(cur, _variant(cur, pos), collection, ac, 200)

    results = _search(cur, freq_filter="AND b.af_max BETWEEN %s AND %s", freq_params=(0.4, 0.6))
    assert sorted(results) == [601]


def test_min_maf_parameter_is_respected(db_conn):
    cur = db_conn.cursor()
    collection = _collection(cur, 100)
    _frequency(cur, _variant(cur, 700), collection, 16, 200)  # 8%

    assert 700 in _search(cur, min_maf=0.05)
    assert 700 not in _search(cur, min_maf=0.10)
