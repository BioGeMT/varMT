"""
Shared test fixtures for VarMT tests.

Set environment variables for test database connection:
    TEST_DB_NAME (default: varmt_test)
    TEST_DB_USER (default: postgres)
    TEST_DB_PASSWORD (default: empty)
    TEST_DB_HOST (default: localhost)
"""

import os
import sys
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.db_utils import create_database, create_tables


TEST_DB_CONFIG = {
    'dbname': os.getenv('TEST_DB_NAME', 'varmt_test'),
    'user': os.getenv('TEST_DB_USER', 'postgres'),
    'host': os.getenv('TEST_DB_HOST', 'localhost')
}

# Only include password if explicitly set; otherwise let psycopg2 use .pgpass
if os.getenv('TEST_DB_PASSWORD'):
    TEST_DB_CONFIG['password'] = os.getenv('TEST_DB_PASSWORD')


@pytest.fixture(scope='module')
def test_db_config():
    """Provide test database configuration."""
    return TEST_DB_CONFIG


@pytest.fixture(scope='module')
def setup_test_database(test_db_config):
    """
    Create test database once for all tests in this module.
    Yields database config, then drops the database after tests complete.
    """
    dbname = test_db_config['dbname']
    user = test_db_config['user']
    password = test_db_config.get('password')
    host = test_db_config['host']

    create_database(dbname=dbname, user=user, password=password, host=host)
    create_tables(dbname=dbname, user=user, password=password, host=host)

    yield test_db_config

    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {dbname}")
    cur.close()
    conn.close()
