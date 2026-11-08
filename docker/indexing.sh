#!/bin/bash

set -e

echo "Creating indexes on varmt database..."

docker compose -f "$(dirname "$0")/../docker-compose.yml" run --rm admin \
    python3 /app/src/vcf2db.py -d varmt -u postgres -l db -x

echo "Indexes created."
