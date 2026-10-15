#!/bin/bash

set -e

python3 /app/src/vcf2db.py -d varmt -u postgres -l db -t

exec streamlit run /app/src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
