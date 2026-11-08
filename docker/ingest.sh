#!/bin/bash

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-vcf-file>"
    exit 1
fi

VCF_NAME=$(basename "$1")

docker compose -f "$(dirname "$0")/../docker-compose.yml" run --rm \
    -v "$(realpath "$1")":/tmp/"$VCF_NAME":ro admin \
    python3 /app/src/vcf2db.py -d varmt -u postgres -l db -i -v /tmp/"$VCF_NAME"
