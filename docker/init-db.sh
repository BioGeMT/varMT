#!/bin/bash

set -e

if [ ! -f /data/postgresql/PG_VERSION ]; then
    mkdir -p /data/postgresql
    chown -R postgres:postgres /data/postgresql
    su - postgres -c "/usr/lib/postgresql/17/bin/initdb -D /data/postgresql"
fi

su - postgres -c "/usr/lib/postgresql/17/bin/pg_ctl -D /data/postgresql start"

su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = 'varmt'\" | grep -q 1" || python3 /app/src/vcf2db.py -d varmt -u postgres -l localhost -c -t

su - postgres -c "/usr/lib/postgresql/17/bin/pg_ctl -D /data/postgresql stop"

exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
