FROM python:3.12-slim

RUN apt-get update && apt-get install -y postgresql-17 supervisor

WORKDIR /app

COPY environment.txt .
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY src/ src/
COPY docker/init-db.sh /app/init-db.sh
COPY docker/db_connection.yml config/db_connection.yml

RUN chmod +x /app/init-db.sh

RUN python3 -m pip install -r environment.txt

EXPOSE 8501

ENTRYPOINT ["/app/init-db.sh"]