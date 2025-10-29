import os.path
import glob

from vcf2db_cli import setup_args
from utils.db_utils import *
from utils.setup_logging import setup_logging
from utils.gene_mapping import load_gene_mapping, map_gene_symbols

import pysam
import psycopg2

logger = setup_logging()

def process_data(vcf_path: str, db_name: str, db_user: str, db_password: str, db_host: str, ref_genome: str) -> None:
    """
    Process VCF files and insert data into the database.
    """
    logging.info("Trying to process data")
    conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host)
    logging.info("Connected to the database")
    gene_mapping = load_gene_mapping()

    try:
        if os.path.isdir(vcf_path):
            vcf_files = sorted(glob.glob(os.path.join(vcf_path, "*.vcf")))
        else:
            vcf_files = [vcf_path]

        logging.info(f"Found {len(vcf_files)} VCF files to process: {vcf_files}")

        for vcf_file in vcf_files:
            cur = conn.cursor()

            try:
                logging.info(f"Processing {vcf_file}")
                vcf = pysam.VariantFile(vcf_file, 'r')

                sample_count = len(vcf.header.samples)
                cur.execute(insert_collection(), (sample_count,))
                collection_id = cur.fetchone()[0]
                
                processed = 0
                for record in vcf:
                    chromosome = record.chrom
                    position = record.pos
                    reference = record.ref

                    cur.execute(insert_variant_location(), (chromosome, position, reference, ref_genome))
                    var_location_id = cur.fetchone()[0]

                    ensembl_gene_id = record.info.get("SNPEFF_GENE_NAME", None)

                    if ensembl_gene_id:
                        gene_symbols = map_gene_symbols(ensembl_gene_id, gene_mapping)

                        for symbol in gene_symbols: # a single variant can be associated with multiple genes
                            cur.execute(insert_gene(), (symbol,))
                            gene_id = cur.fetchone()[0]
                            cur.execute(insert_gene_location(), (gene_id, var_location_id))

                    an_info = record.info.get('AN', None)
                    for i, alt_allele in enumerate(record.alts):
                        rs_id = record.id if record.id else None

                        cur.execute(insert_variant(), (var_location_id, rs_id, alt_allele))
                        variant_id = cur.fetchone()[0]

                        ac_info = record.info['AC']
                        if isinstance(ac_info, list):
                            allele_count = ac_info[i]
                        else:
                            allele_count = ac_info

                        cur.execute(insert_variant_frequency(), (variant_id, collection_id, allele_count, an_info))
                    
                    processed += 1
                    if processed % 10000 == 0: # log and commit every 10,000 records
                        logging.info(f"Processed {processed} records from {vcf_file}")
                        conn.commit()

                vcf.close()
                conn.commit()
                logging.info(f"Successfully processed {vcf_file} with {processed} records.")

            except Exception as e:
                conn.rollback()
                logging.error(f"Error processing {vcf_file}: {e}")
                raise
            finally:
                cur.close()
    finally:
        conn.close()

def main() -> None:
    args = setup_args()

    if args.create:
        create_database(dbname=args.database, user=args.username, password=args.password, host=args.host)

    if args.tables:
        create_tables(dbname=args.database, user=args.username, password=args.password, host=args.host)

    if args.insert:
        process_data(
            vcf_path=args.vcf,
            db_name=args.database,
            db_user=args.username,
            db_password=args.password,
            db_host=args.host,
            ref_genome=args.reference_genome
        )

    if args.indexes:
        create_indexes(dbname=args.database, user=args.username, password=args.password, host=args.host)

if __name__ == '__main__':
    main()