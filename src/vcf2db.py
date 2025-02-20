import os.path
import psycopg2
import glob
from arg_parser import setup_args
from utils.dbutils import create_database, create_tables, insert_position, insert_variant
import pysam


def process_data(vcf_path, db_name, db_user, db_password, db_host):
    print("Trying to process data")
    conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host)

    try:
        if os.path.isdir(vcf_path):
            vcf_files = glob.glob(os.path.join(vcf_path, "*.vcf"))
            print(f"Found these VCF files: {vcf_files}")
        else:
            vcf_files = [vcf_path]

        print(f"Found {len(vcf_files)} VCF files to process")

        for vcf_file in vcf_files:
            cur = conn.cursor()  # Create cursor per file

            try:
                print(f"Processing {vcf_file}...")
                vcf = pysam.VariantFile(vcf_file, 'r')

                for record in vcf:
                    chromosome = record.chrom
                    start_position = record.pos
                    end_position = start_position + len(record.ref) - 1
                    reference = record.ref

                    cur.execute(insert_position(), (chromosome, start_position, end_position, reference))
                    position_id = cur.fetchone()[0]

                    for alt_allele in record.alts:
                        rs_id = record.id if record.id else None
                        allele_count = record.info.get('AC', [1])[0]
                        cur.execute(insert_variant(), (position_id, rs_id, alt_allele, allele_count))

                vcf.close()
                conn.commit()

            except Exception as e:
                conn.rollback()  # Rollback on error
                print(f"Error processing {vcf_file}: {e}")
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
        process_data('../data/',
                    args.database, args.username, args.password, args.host)

if __name__ == '__main__':
    main()