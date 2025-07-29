# VarMT - Genetic Variant Database Tool

A Python tool for parsing VCF (Variant Call Format) files and storing genetic variants in a PostgreSQL database with aggregated frequency data across different sample collections.

## Overview

VarMTdb processes VCF files and stores genetic variants in a relational database schema designed for efficient querying of variant frequencies across populations and gene-based analysis. The tool automatically creates the database structure and handles the data insertion process.

## Features

- **Automated Database Setup**: Creates PostgreSQL database and tables automatically
- **VCF Processing**: Parses VCF files using pysam
- **Aggregated Storage**: Stores variant frequencies across different sample collections
- **Conflict Handling**: Uses PostgreSQL UPSERT operations to handle duplicate variants
- **Secure Authentication**: Supports .pgpass file for password-free authentication
- **Performance Optimization**: Creates essential database indexes for fast querying

## Environment Setup
Create and activate the conda environment:

```bash
conda env create -f environment.yaml
conda activate varMTenv
```

## Database authentication
The use of [.pgpass](https://www.postgresql.org/docs/current/libpq-pgpass.html) file is recommended for security reasons.

You can still provide the password directly from the CLI.

## Usage

### Basic Usage
With .pgpass file (recommended):
```bash
python3 src/vcf2db.py -d database_name -u username -l host -c -t -i -x -v path/to/vcf
```

With password on command line:
```bash
python3 src/vcf2db.py -d database_name -u username -p password -l host -c -t -i -x -v path/to/vcf
```

### Command Line Arguments

**Database Connection:**
- `-d, --database`: PostgreSQL database name (required)
- `-u, --username`: PostgreSQL username (required)  
- `-p, --password`: PostgreSQL password (optional if using .pgpass)
- `-l, --host`: PostgreSQL host name (required)

**Database Operations:**
- `-c, --create`: Delete and recreate database if existing
- `-t, --tables`: Create the database tables
- `-i, --insert`: Insert VCF data into tables
- `-x, --indexes`: Create indexes on tables

**Data Input:**
- `-v, --vcf`: Path to VCF file or directory containing VCF files
- `-r, --reference_genome`: Reference genome version (optional, default=GRCh38)

### Step-by-Step Workflow

1. **Create Database and Tables:**
   ```bash
   python3 src/vcf2db.py -d myvariantdb -u postgres -l localhost -c -t -v data/
   ```

2. **Process VCF Files:**
   ```bash
   python3 src/vcf2db.py -d myvariantdb -u postgres -l localhost -i -v data/
   ```

3. **Create Indexes (after data loading):**
   ```bash
   python3 src/vcf2db.py -d myvariantdb -u postgres -l localhost -x
   ```

## Project Structure

```
varMTdb/
├── src/
│   ├── vcf2db.py              # Main application script
│   ├── vcf2db_cli.py          # Command line interface
│   └── utils/
│       └── db_utils.py        # Database utility functions
├── res/
│   └── data/
│       └── subset_hg19.vcf    # Sample VCF file
├── docs/
│   ├── database_documentation.md  # Detailed schema documentation
│   └── ERschema.png           # Entity-relationship diagram
├── environment.yaml           # Conda environment specification
└── README.md
```