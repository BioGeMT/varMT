#!/bin/bash

# Streamlit reads login settings only from secrets.toml, so write it from the environment
write_streamlit_secrets() {
    mkdir -p /app/.streamlit
    cat > /app/.streamlit/secrets.toml <<EOF
[auth]
redirect_uri = "${VARMT_URL}/oauth2callback"
cookie_secret = "${VARMT_COOKIE_SECRET}"
client_id = "varmt"
client_secret = "${VARMT_CLIENT_SECRET}"
server_metadata_url = "http://keycloak:8080/realms/varmt/.well-known/openid-configuration"
EOF
}
