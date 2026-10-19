#!/bin/bash

set -e

# Streamlit reads login settings only from secrets.toml, so write it from the environment
mkdir -p /app/.streamlit
cat > /app/.streamlit/secrets.toml <<EOF
[auth]
redirect_uri = "${VARMT_URL}/oauth2callback"
cookie_secret = "${VARMT_COOKIE_SECRET}"
client_id = "varmt"
client_secret = "${VARMT_CLIENT_SECRET}"
server_metadata_url = "http://keycloak:8080/realms/varmt/.well-known/openid-configuration"
EOF

python3 /app/src/vcf2db.py -d varmt -u postgres -l db -t

exec streamlit run /app/src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
