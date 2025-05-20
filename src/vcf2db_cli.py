from argparse import ArgumentParser

def setup_args():
    parser = ArgumentParser(
        prog="varMTdb",
        description="Tool for parsing VCF files and store data in PostreSQL"
    )

    # Database connection arguments
    parser.add_argument("-d", "--database", help="PostgreSQL DB name.", required=True)
    parser.add_argument("-u", "--username", help="PostgreSQL user." , required=True)
    parser.add_argument("-p", "--password", help="PostgreSQL user password.", required=True)
    parser.add_argument("-l", "--host", help="PostgreSQL host name", required=True)

    # Database creation and manipulation arguments
    parser.add_argument("-c", "--create", action="store_true", help="Delete and recreate DB if existing.", required=False)
    parser.add_argument("-t", "--tables", action="store_true", help="Create the tables in the database.", required=False)
    parser.add_argument("-i", "--insert", action="store_true", help="Insert the data inside the tables", required=False)

    parser.add_argument("-v", "--vcf", help="Path to the VCF file.", required=True)

    return parser.parse_args()