"""Shared policy loading and validation without a database."""

import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from utils.browser_policy import load_browser_policy, POLICY_PATH


class TestBrowserPolicy(unittest.TestCase):
    def test_load_custom_values(self):
        with patch.object(Path, 'open', mock_open(read_data='query:\n  max_interval_bases: 10000\n  min_maf: 0.1\n')):
            policy = load_browser_policy()
        self.assertEqual(policy.max_interval_bases, 10000)
        self.assertEqual(policy.min_maf, 0.1)

    def test_reject_invalid_or_missing_min_maf(self):
        for value in ['', 'min_maf: 0', 'min_maf: -0.05', 'min_maf: 0.6', 'min_maf: true', 'min_maf: "0.05"']:
            document = f'query: {{max_interval_bases: 5000, {value}}}' if value else 'query: {max_interval_bases: 5000}'
            with self.subTest(document=document), patch.object(Path, 'open', mock_open(read_data=document)):
                with self.assertRaisesRegex(ValueError, 'min_maf'):
                    load_browser_policy()

    def test_reject_invalid_or_missing_limit(self):
        for document in [
            '', '[]', 'query: []', 'query: {}',
            'query: {max_interval_bases: 0}',
            'query: {max_interval_bases: -1}',
            'query: {max_interval_bases: true}',
            'query: {max_interval_bases: 1.5}',
            'query: {max_interval_bases: "5000"}',
        ]:
            with self.subTest(document=document), patch.object(Path, 'open', mock_open(read_data=document)):
                with self.assertRaisesRegex(ValueError, 'positive integer'):
                    load_browser_policy()

    def test_reject_malformed_yaml(self):
        with patch.object(Path, 'open', mock_open(read_data='query: [')):
            with self.assertRaisesRegex(ValueError, 'Cannot load browser policy'):
                load_browser_policy()

    def test_missing_file_does_not_fall_back(self):
        with patch.object(Path, 'open', side_effect=FileNotFoundError('missing policy')):
            with self.assertRaisesRegex(ValueError, 'Cannot load browser policy'):
                load_browser_policy()

    def test_path_is_relative_to_repository(self):
        expected = Path(__file__).resolve().parents[1] / 'config' / 'browser_policy.yml'
        self.assertEqual(POLICY_PATH, expected)
        policy = load_browser_policy()
        self.assertGreater(policy.max_interval_bases, 0)
        self.assertTrue(0 < policy.min_maf <= 0.5)
