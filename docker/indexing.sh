#!/bin/bash

set -e

echo "Creating indexes on varmt database..."

docker exec varmt-app python3 /app/src/vcf2db.py \
    -d varmt -u postgres -l db -x

echo "Indexes created."
