#!/bin/bash

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-vcf-file>"
    exit 1
fi

VCF_NAME=$(basename "$1")
trap 'docker exec varmt-app rm -f /tmp/'"$VCF_NAME"' 2>/dev/null' EXIT

docker cp "$1" varmt-app:/tmp/"$VCF_NAME"
docker exec varmt-app python3 /app/src/vcf2db.py \
    -d varmt -u postgres -l localhost -i -v /tmp/"$VCF_NAME"
