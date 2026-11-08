#!/bin/bash

set -e

python3 /app/src/vcf2db.py -d varmt -u postgres -l db -t
python3 /app/create_reader_role.py
