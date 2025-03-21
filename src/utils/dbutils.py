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
                FOREIGN KEY (collection_id) REFERENCES collections (id)
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
    variant_insert_query = """
                            INSERT INTO variants (variant_location_id, rs_id, alternate_allele)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (variant_location_id, alternate_allele)
                            DO UPDATE SET id = variants.id
                            RETURNING id
            """
    return variant_insert_query

def insert_variant_location():
    variant_location_insert_query = """
                            INSERT INTO variant_locations (chromosome, position, reference_allele, genome_version)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (chromosome, position, reference_allele, genome_version)
                            RETURNING id
    """
    return variant_location_insert_query

def insert_collection():
    collection_insert_query = """
                            INSERT INTO collections (sample_count)
                            VALUES (%s)
                            RETURNING id
                            """
    return collection_insert_query

def insert_variant_frequency():
    variant_frequency_insert_query = """
                            INSERT INTO variant_frequencies (variant_id, collection_id, alternate_allele_count)
                            VALUES (%s, %s, %s)
                            """
    return variant_frequency_insert_query

def insert_gene():
    gene_insert_query = """
                            INSERT INTO genes (symbol)
                            VALUES (%s)
                            ON CONFLICT (symbol)
                            DO UPDATE SET id = genes.id
                            RETURNING id
                        """
    return gene_insert_query

def insert_gene_location():
    gene_location_insert_query = """
                            INSERT INTO gene_locations (gene_id, variant_location_id)
                            VALUES (%s, %s)
                            ON CONFLICT (gene_id, variant_location_id)
                            DO UPDATE SET id = gene_locations.id
                            RETURNING id
                            """
    return gene_location_insert_query