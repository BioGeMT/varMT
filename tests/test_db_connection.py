"""
Database connection tests.
Tests basic connectivity to PostgreSQL test database.

Set environment variables for test database connection:
    TEST_DB_NAME (default: varmt_test)
    TEST_DB_USER (default: postgres)
    TEST_DB_PASSWORD (default: empty)
    TEST_DB_HOST (default: localhost)
"""

import pytest
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.db_utils import create_database, create_tables


# Test database configuration
TEST_DB_CONFIG = {
    'dbname': os.getenv('TEST_DB_NAME', 'varmt_test'),
    'user': os.getenv('TEST_DB_USER', 'postgres'),
    'password': os.getenv('TEST_DB_PASSWORD', ''),
    'host': os.getenv('TEST_DB_HOST', 'localhost')
}


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
    password = test_db_config['password']
    host = test_db_config['host']

    # Create test database
    create_database(dbname=dbname, user=user, password=password, host=host)

    # Create tables
    create_tables(dbname=dbname, user=user, password=password, host=host)

    yield test_db_config

    # Cleanup: Drop test database after all tests
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {dbname}")
    cur.close()
    conn.close()


def test_can_connect_to_postgres(test_db_config):
    """Test that we can connect to PostgreSQL server."""
    user = test_db_config['user']
    password = test_db_config['password']
    host = test_db_config['host']

    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    assert conn is not None
    conn.close()


def test_can_create_test_database(test_db_config):
    """Test that we can create the test database."""
    dbname = test_db_config['dbname']
    user = test_db_config['user']
    password = test_db_config['password']
    host = test_db_config['host']

    # Create database
    create_database(dbname=dbname, user=user, password=password, host=host)

    # Verify it exists
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    result = cur.fetchone()
    cur.close()
    conn.close()

    assert result is not None

    # Cleanup
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {dbname}")
    cur.close()
    conn.close()


def test_can_connect_to_test_database(setup_test_database):
    """Test that we can connect to the test database."""
    conn = psycopg2.connect(**setup_test_database)
    assert conn is not None

    # Verify connection is active
    cur = conn.cursor()
    cur.execute("SELECT 1")
    result = cur.fetchone()
    assert result[0] == 1

    cur.close()
    conn.close()


def test_test_database_has_tables(setup_test_database):
    """Test that the test database has the required tables."""
    conn = psycopg2.connect(**setup_test_database)
    cur = conn.cursor()

    expected_tables = [
        'variant_locations',
        'variants',
        'collections',
        'variant_frequencies',
        'genes',
        'gene_locations'
    ]

    for table in expected_tables:
        cur.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s
        """, (table,))
        result = cur.fetchone()
        assert result is not None, f"Table {table} does not exist"

    cur.close()
    conn.close()
