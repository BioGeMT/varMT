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

def create_database(dbname: str, user: str, password: str, host: str):
    """
    Creates a PostgreSQL database with the specified name.
    If the database already exists, it will be dropped and recreated.

    Args:
        dbname (str): Name of the database to create.
        user (str): PostgreSQL user name.
        password (str): PostgreSQL user password.
        host (str): PostgreSQL host name.
        
    Returns:
        None
    """
    logger.info("Creating database...")
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {dbname}")
    cur.execute(f"CREATE DATABASE {dbname}")
    cur.close()
    conn.close()

    logger.info("Database created correctly")

def create_tables(dbname: str, user: str, password: str, host: str):
    """
    Create the necessary tables in the PostgreSQL database.

    Args:
        dbname (str): Name of the database.
        user (str): PostgreSQL user name.
        password (str): PostgreSQL user password.
        host (str): PostgreSQL host name.

    Returns:
        None
    """
    logger.info("Creating tables...")
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host)

    cur = conn.cursor()

    cur.execute("""
                CREATE TABLE variant_locations(
                    id SERIAL PRIMARY KEY,
                    chromosome TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    reference_allele TEXT NOT NULL,
                    genome_version TEXT NOT NULL,
                    UNIQUE (chromosome, position, reference_allele, genome_version)
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
                sample_count INTEGER NOT NULL
            );
            """)
    
    cur.execute("""
            CREATE TABLE variant_frequencies(
                id SERIAL PRIMARY KEY,
                variant_id INTEGER NOT NULL,
                collection_id INTEGER NOT NULL,
                alternate_allele_count INTEGER NOT NULL,
                FOREIGN KEY (variant_id) REFERENCES variants (id),
                FOREIGN KEY (collection_id) REFERENCES collections (id),
                UNIQUE (variant_id, collection_id)
            );
            """)
    
    cur.execute("""
            CREATE TABLE genes(
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                UNIQUE (symbol)
            );
            """)
    
    cur.execute("""
            CREATE TABLE gene_locations(
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
    """
    Returns the SQL query string for inserting or updating a variant in the 'variants' table.
    """
    variant_insert_query = """
                            INSERT INTO variants (variant_location_id, rs_id, alternate_allele)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (variant_location_id, alternate_allele)
                            DO UPDATE SET id = variants.id
                            RETURNING id
                        """
    return variant_insert_query

def insert_variant_location():
    """
    Returns the SQL query string for inserting or updating a variant location in the 'variant_locations' table.
    """
    variant_location_insert_query = """
                            INSERT INTO variant_locations (chromosome, position, reference_allele, genome_version)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (chromosome, position, reference_allele, genome_version)
                            DO UPDATE SET id = variant_locations.id
                            RETURNING id
                        """
    return variant_location_insert_query

def insert_collection():
    """
    Returns the SQL query string for inserting a new collection in the 'collections' table.
    """
    collection_insert_query = """
                            INSERT INTO collections (sample_count)
                            VALUES (%s)
                            RETURNING id
                        """
    return collection_insert_query

def insert_variant_frequency():
    """
    Return the SQL query string for inserting or updating a variant frequency in the 'variant_frequencies' table.
    """
    variant_frequency_insert_query = """
                            INSERT INTO variant_frequencies (variant_id, collection_id, alternate_allele_count)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (variant_id, collection_id)
                            DO UPDATE SET alternate_allele_count = variant_frequencies.alternate_allele_count + EXCLUDED.alternate_allele_count
                        """
    return variant_frequency_insert_query

def insert_gene():
    """
    Returns the SQL query string for inserting or updating a gene in the 'genes' table.
    """
    gene_insert_query = """
                            INSERT INTO genes (symbol)
                            VALUES (%s)
                            ON CONFLICT (symbol)
                            DO UPDATE SET id = genes.id
                            RETURNING id
                        """
    return gene_insert_query

def insert_gene_location():
    """
    Returns the SQL query string for inserting or updating a gene location in the 'gene_locations' table.
    """
    gene_location_insert_query = """
                            INSERT INTO gene_locations (gene_id, variant_location_id)
                            VALUES (%s, %s)
                            ON CONFLICT (gene_id, variant_location_id)
                            DO NOTHING
                        """
    return gene_location_insert_query