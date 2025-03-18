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
                CREATE TABLE variant_locations(
                    id SERIAL PRIMARY KEY,
                    chromosome TEXT NOT NULL,
                    start_position INTEGER NOT NULL,
                    end_position INTEGER NOT NULL,
                    reference_allele TEXT NOT NULL,
                    genome_version TEXT NOT NULL,
                    UNIQUE (chromosome, start_position, end_position, reference_allele, genome_version)
                );
                """)

    cur.execute("""
            CREATE TABLE variants(
                id SERIAL PRIMARY KEY,
                variant_location_id INTEGER NOT NULL,
                rs_id TEXT,
                alternate_allele TEXT NOT NULL,
                FOREIGN KEY (variant_location_id) REFERENCES variant_locations (id),
                UNIQUE (variant_location_id, alternate_allele)
            );
            """)
    
    cur.execute("""
            CREATE TABLE collections(
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                UNIQUE (name)
            );
            """)
    
    cur.execute("""
            CREATE TABLE variants_frequencies(
                id SERIAL PRIMARY KEY,
                variant_id INTEGER NOT NULL,
                collection_id INTEGER NOT NULL,
                alternate_allele_count INTEGER NOT NULL,
                FOREIGN KEY (variant_id) REFERENCES variants (id),
                FOREIGN KEY (collection_id) REFERENCES collections (id)
            );
            """)
    
    cur.execute("""
            CREATE TABLE genes(
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                description TEXT,
                UNIQUE (symbol)
            );
            """)
    
    cur.execute("""
            CREATE TABLE genes_locations(
                id SERIAL PRIMARY KEY,
                gene_id INTEGER NOT NULL,
                variant_location_id INTEGER NOT NULL,
                FOREIGN KEY (gene_id) REFERENCES genes (id),
                FOREIGN KEY (variant_location_id) REFERENCES variant_locations (id),
                UNIQUE (gene_id, variant_location_id)
            );
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