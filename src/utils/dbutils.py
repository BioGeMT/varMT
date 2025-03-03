import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_database(dbname, user, password, host):
    logger.info("Creating database...")
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS " + dbname)
    cur.execute("CREATE DATABASE " + dbname)
    cur.close()
    conn.close()

    logger.info("Database created correctly")

def create_tables(dbname, user, password, host):
    logger.info("Creating tables...")
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host)

    cur = conn.cursor()

    cur.execute("""
                CREATE TABLE positions(
                    id SERIAL PRIMARY KEY,
                    chromosome TEXT NOT NULL,
                    start_position INTEGER NOT NULL,
                    end_position INTEGER NOT NULL,
                    reference TEXT NOT NULL,
                    UNIQUE (chromosome, start_position, end_position, reference)
                )
                """)

    cur.execute("""
            CREATE TABLE variants(
                id SERIAL PRIMARY KEY,
                position_id INTEGER NOT NULL,
                rs_id TEXT,
                alternate TEXT NOT NULL,
                count INTEGER NOT NULL,
                FOREIGN KEY (position_id) REFERENCES positions (id),
                UNIQUE (position_id, alternate)
            )
            """)

    conn.commit()
    cur.close()
    conn.close()

    logger.info("Tables created correctly")


def insert_variant():
    variant_insert_query = """
                            INSERT INTO variants(position_id, rs_id, alternate, count)
                            VALUES (%s, %s, %s, %s)
            """
    return variant_insert_query

def insert_position():
    position_insert_query = """
                            INSERT INTO positions (chromosome, start_position, end_position, reference)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (chromosome, start_position, end_position, reference) 
                            DO UPDATE SET chromosome = EXCLUDED.chromosome
                            RETURNING id
    """
    return position_insert_query