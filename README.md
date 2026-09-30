# VarMT - Genetic Variant Database Tool

A Python tool for parsing VCF (Variant Call Format) files and storing genetic variants in a PostgreSQL database with aggregated frequency data across different sample collections.

## Overview

VarMTdb processes VCF files and stores genetic variants in a relational database schema designed for efficient querying of variant frequencies across populations and gene-based analysis. The tool automatically creates the database structure and handles the data insertion process.

## Features

- **Automated Database Setup**: Creates PostgreSQL database and tables automatically
- **VCF Processing**: Parses VCF files using pysam
- **Aggregated Storage**: Stores variant frequencies across different sample collections
- **Conflict Handling**: Uses PostgreSQL UPSERT operations to handle duplicate variants
- **Performance Optimization**: Creates essential database indexes for fast querying
- **Web Interface**: Streamlit app for querying variants by chromosome, gene, and allele frequency
- **Single-Container Deployment**: Docker image bundling PostgreSQL and the Streamlit UI

## Quick Start (Docker)

The recommended way to run VarMT. Everything (PostgreSQL, the Streamlit UI, and the CLI) lives in one container.

### 1. Build the image

```bash
docker build -t varmt .
```

### 2. Start the container

```bash
docker run -d \
    --name varmt-app \
    -v varmt-pgdata:/data/postgresql \
    -p 8502:8501 \
    varmt
```

- `-v varmt-pgdata:/data/postgresql` — named volume so the database survives container restarts
- `-p 8502:8501` — exposes the Streamlit UI on host port 8502 (change if needed)
- On first start, the container initializes PostgreSQL and creates the `varmt` database and tables

### 3. Ingest a VCF file

```bash
./docker/ingest.sh /path/to/your.vcf
```

The script copies the VCF into the container and runs the ingestion. Each call adds a new collection — run it once per VCF file.

### 4. Create indexes (one-time, after first ingestion)

```bash
./docker/indexing.sh
```

Creates the indexes that make queries fast on large datasets. Only needs to be run once; PostgreSQL maintains the indexes automatically for subsequent ingestions.

### 5. Open the web UI

Browse to [http://localhost:8502](http://localhost:8502) to query the variants. If running on a remote server, set up an SSH tunnel:

```bash
ssh -L 1455:localhost:8502 user@server
```

Then open [http://localhost:1455](http://localhost:1455) on your local machine.

Every variant search requires a chromosome and an inclusive start/end interval
of at most 5,000 bases (`end - start + 1`). Gene symbols and CSV rsIDs only narrow
that interval. CSV rows must all fit within one 5 kb window on the same chromosome;
unbounded gene searches and searches spanning multiple windows are rejected.

The shared limit is configured in `config/browser_policy.yml`:

```yaml
query:
  max_interval_bases: 5000
```

Restart Streamlit after changing it. For Docker, rebuild the image and
replace the container, retaining the database volume.

### Adding more collections

Just run `./docker/ingest.sh /path/to/another.vcf` again — collections accumulate over time. No need to restart the container or recreate indexes.

## Manual Installation

Use this only if you don't want to run Docker. Requires a PostgreSQL server you manage yourself.

### Environment Setup

```bash
conda env create -f environment.yml
conda activate varMTenv
```

### Database Authentication

The use of [.pgpass](https://www.postgresql.org/docs/current/libpq-pgpass.html) file is recommended for security reasons. You can also pass the password directly via `-p`.

### Running

With `.pgpass` (recommended):
```bash
python3 src/vcf2db.py -d database_name -u username -l host -c -t -i -x -v path/to/vcf
```

With password on command line:
```bash
python3 src/vcf2db.py -d database_name -u username -p password -l host -c -t -i -x -v path/to/vcf
```

### Web Interface

Requires `config/db_connection.yml` with database connection parameters. Supports `.pgpass` authentication (omit password in config) or direct password specification.

```bash
streamlit run src/streamlit_app.py
```

## CLI Reference

These arguments apply to both the Docker workflow (when calling `vcf2db.py` via `docker exec`) and manual installation.

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

### Step-by-Step Workflow (Manual)

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
varMT/
├── Dockerfile                   # Container definition
├── supervisord.conf             # Manages PostgreSQL + Streamlit inside the container
├── environment.txt              # Pip dependencies (used by Docker build)
├── environment.yml              # Conda environment spec (manual install)
├── docker/
│   ├── init-db.sh               # First-run: initdb + create varmt DB and tables
│   ├── db_connection.yml        # In-container Streamlit DB config (localhost)
│   ├── ingest.sh                # Wrapper: docker cp VCF + run vcf2db.py
│   └── indexing.sh              # Wrapper: run vcf2db.py -x for indexing
├── src/
│   ├── vcf2db.py                # Main CLI application
│   ├── vcf2db_cli.py            # Command line interface
│   ├── streamlit_app.py         # Streamlit web interface entry point
│   ├── pages/
│   │   └── 1_Advanced_Search.py # Advanced gene search page
│   ├── queries/
│   │   └── variant_queries.py   # Centralized SQL queries
│   └── utils/
│       ├── db_utils.py          # Database utility functions
│       ├── streamlit_db.py      # DatabaseClient for Streamlit queries
│       ├── vep_utils.py         # VEP annotation parsing utilities
│       ├── csv_parser.py        # CSV/gene mapping file parser
│       └── setup_logging.py     # Logging configuration
├── config/
│   ├── browser_policy.yml       # Shared browser query limit (tracked)
│   └── db_connection.yml        # Local Streamlit DB config (not tracked)
├── tests/                       # Pytest suite
├── res/
│   └── data/
│       └── subset_hg19.vcf      # Sample VCF file
└── docs/
    ├── database_documentation.md
    └── ERschema.png
```

## Troubleshooting

- **Port already in use** when starting the container: another service is bound to the host port. Use a different port (e.g. `-p 8503:8501`).
- **`initdb: directory exists but is not empty`**: a previous container left partial data in the volume. Remove it with `docker volume rm varmt-pgdata` and start fresh.
- **Streamlit shows "connection failed"**: ensure the container is running (`docker ps`) and that you're hitting the host port mapped to 8501.

## Sample Data

The sample dataset provided (`res/data/subset_hg19.vcf`) is publicly available (source [1000 Genomes Project](http://www.internationalgenome.org/)).
