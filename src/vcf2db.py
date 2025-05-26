import os.path
import psycopg2
import glob
from vcf2db_cli import setup_args
from utils.dbutils import *
import pysam
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def process_data(vcf_path, db_name, db_user, db_password, db_host):
    logging.info("Trying to process data")
    conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host)
    logging.info("Connected to the database")

    try:
        if os.path.isdir(vcf_path):
            vcf_files = sorted(glob.glob(os.path.join(vcf_path, "*.vcf")))
            logging.info(f"Found these VCF files: {vcf_files}")
        else:
            vcf_files = [vcf_path]

        logging.info(f"Found {len(vcf_files)} VCF files to process: {vcf_files}")

        for vcf_file in vcf_files:
            cur = conn.cursor()

            try:
                logging.info(f"Processing {vcf_file}...")
                vcf = pysam.VariantFile(vcf_file, 'r')

                cur.execute(insert_collection(), (1,))
                collection_id = cur.fetchone()[0]

                for record in vcf:
                    chromosome = record.chrom
                    position = record.pos
                    reference = record.ref
                    gene_symbols = record.info.get('CSQ', None) #TODO this may vary depending on the annotation process

                    cur.execute(insert_variant_location(), (chromosome, position, reference, "GRCh38"))
                    var_location_id = cur.fetchone()[0]

                    for symbol in gene_symbols: # a single variant can be associated with multiple genes
                        cur.execute(insert_gene(), (symbol,))
                        gene_id = cur.fetchone()[0]
                        cur.execute(insert_gene_location(), (gene_id, var_location_id))

                    for i, alt_allele in enumerate(record.alts):
                        rs_id = record.id if record.id else None

                        cur.execute(insert_variant(), (var_location_id, rs_id, alt_allele))
                        variant_id = cur.fetchone()[0]

                        if isinstance(record.info['AC'], tuple) and len(record.info['AC']) > i:
                            allele_count = record.info['AC'][i]
                        else:
                            allele_count = record.info['AC'][0]

                        cur.execute(insert_variant_frequency(), (variant_id, collection_id, allele_count))

                vcf.close()
                conn.commit()

            except Exception as e:
                conn.rollback()
                logging.error(f"Error processing {vcf_file}: {e}")
                raise
            finally:
                cur.close()
    finally:
        conn.close()

def main():
    args = setup_args()

    if args.create:
        create_database(dbname=args.database, user=args.username, password=args.password, host=args.host)

    if args.tables:
        create_tables(dbname=args.database, user=args.username, password=args.password, host=args.host)

    if args.insert:
        process_data(vcf_path=args.vcf, db_name=args.database, db_user=args.username, db_password=args.password, db_host=args.host)

if __name__ == '__main__':
    main()