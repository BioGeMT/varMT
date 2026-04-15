"""
Database connection tests.
Tests basic connectivity to PostgreSQL test database.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from utils.db_utils import create_database


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

    create_database(dbname=dbname, user=user, password=password, host=host)

    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    result = cur.fetchone()
    cur.close()
    conn.close()

    assert result is not None

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
