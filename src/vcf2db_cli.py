from argparse import ArgumentParser, Namespace

def setup_args() -> Namespace:
    parser = ArgumentParser(
        prog="varMTdb",
        description="Tool for parsing VCF files and store data in PostreSQL"
    )

    # Database connection arguments
    parser.add_argument("-d", "--database", help="PostgreSQL DB name.", required=True)
    parser.add_argument("-u", "--username", help="PostgreSQL user." , required=True)
    parser.add_argument("-p", "--password", help="PostgreSQL user password.", required=False)
    parser.add_argument("-l", "--host", help="PostgreSQL host name", required=True)

    # Database creation and manipulation arguments
    parser.add_argument("-c", "--create", action="store_true", help="Delete and recreate DB if existing.", required=False)
    parser.add_argument("-t", "--tables", action="store_true", help="Create the tables in the database.", required=False)
    parser.add_argument("-i", "--insert", action="store_true", help="Insert the data inside the tables", required=False)

    parser.add_argument("-v", "--vcf", help="Path to the VCF file or directory containing VCF files.", required=False)

    parser.add_argument("-r", "--reference_genome", help="Reference genome version (e.g., GRCh37, GRCh38)", default="GRCh38", required=False)

    args = parser.parse_args()
    if args.insert and not args.vcf:
        parser.error("--vcf is required when using --insert")

    return args