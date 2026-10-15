"""Regression tests for bounded manual and CSV searches; no database required."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from utils import csv_parser
from utils.query_limits import validate_query_window
from utils.csv_parser import build_query_conditions, validate_csv_data, REQUIRED_COLUMNS

MAX_QUERY_BASES = 5000  # Fixed test policy, independent of deployment configuration.


class TestQueryLimits(unittest.TestCase):
    def test_inclusive_boundary(self):
        self.assertEqual(validate_query_window('1', 100, 5099, limit=MAX_QUERY_BASES), ('1', 100, 5099))
        with self.assertRaisesRegex(ValueError, '5,000'):
            validate_query_window('1', 100, 5100, limit=MAX_QUERY_BASES)

    def test_single_position(self):
        self.assertEqual(validate_query_window('chrX', 100, 100, limit=MAX_QUERY_BASES), ('chrX', 100, 100))

    def test_missing_interval_parts(self):
        for window in [('', 1, 100), ('1', None, 100), ('1', 100, None)]:
            with self.subTest(window=window), self.assertRaises(ValueError):
                validate_query_window(*window, limit=MAX_QUERY_BASES)

    def test_invalid_coordinates(self):
        for start, end in [(0, 10), (10, 1), (1.5, 10), (1, float('nan')), (True, 10)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                validate_query_window('1', start, end, limit=MAX_QUERY_BASES)

    def test_invalid_chromosome(self):
        with self.assertRaises(ValueError):
            validate_query_window('all', 1, 100, limit=MAX_QUERY_BASES)

    def test_custom_limit(self):
        self.assertEqual(validate_query_window('1', 100, 199, limit=100), ('1', 100, 199))
        with self.assertRaisesRegex(ValueError, '100 bases'):
            validate_query_window('1', 100, 200, limit=100)
        self.assertEqual(validate_query_window('1', 1, 6000, limit=6000), ('1', 1, 6000))

    def test_invalid_limit(self):
        for limit in [0, -1, 1.5, True, None]:
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, 'positive integer'):
                validate_query_window('1', 100, 100, limit=limit)


class TestCsvQueryLimits(unittest.TestCase):
    def setUp(self):
        policy = patch.object(csv_parser, 'MAX_QUERY_BASES', MAX_QUERY_BASES)
        policy.start()
        self.addCleanup(policy.stop)

    def csv(self, *rows):
        return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)

    def test_rows_within_one_window(self):
        df = self.csv(['TEST', None, '1', 100, 200], [None, 'rs123', '1', 5000, 5099])
        self.assertEqual(validate_csv_data(df), [])
        conditions, params = build_query_conditions(df)
        self.assertEqual(len(conditions), 2)
        self.assertEqual(params, ['TEST', '1', 100, 200, 'rs123', '1', 5000, 5099])

    def test_gene_and_rsid_cannot_bypass_interval(self):
        for row in [['TEST', None, None, None, None], [None, 'rs123', None, None, None]]:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, 'required'):
                build_query_conditions(self.csv(row))

    def test_oversized_row(self):
        with self.assertRaisesRegex(ValueError, '5,000'):
            build_query_conditions(self.csv([None, None, '1', 100, 5100]))

    def test_separate_small_windows_cannot_bypass_limit(self):
        df = self.csv([None, None, '1', 100, 200], [None, None, '1', 10000, 10100])
        with self.assertRaisesRegex(ValueError, 'Combined CSV'):
            build_query_conditions(df)

    def test_multiple_chromosomes(self):
        df = self.csv([None, None, '1', 100, 200], [None, None, '2', 100, 200])
        with self.assertRaisesRegex(ValueError, 'same chromosome'):
            build_query_conditions(df)

    def test_empty_csv(self):
        with self.assertRaisesRegex(ValueError, 'at least one'):
            build_query_conditions(self.csv())


if __name__ == '__main__':
    unittest.main()
