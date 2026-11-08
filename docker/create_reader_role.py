"""Create or update the read-only varmt_reader role used by the Streamlit app."""
import os

import psycopg2

conn = psycopg2.connect(dbname="varmt", user="postgres", host="db")
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'varmt_reader') THEN
                CREATE ROLE varmt_reader LOGIN;
            END IF;
        END $$;
    """)
    cur.execute("ALTER ROLE varmt_reader WITH LOGIN PASSWORD %s", (os.environ["VARMT_READER_PASSWORD"],))
    cur.execute("GRANT CONNECT ON DATABASE varmt TO varmt_reader")
    cur.execute("GRANT USAGE ON SCHEMA public TO varmt_reader")
    cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO varmt_reader")
    # Tables created later by postgres are readable too
    cur.execute("ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT ON TABLES TO varmt_reader")
conn.close()
