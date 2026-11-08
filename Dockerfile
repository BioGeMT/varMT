FROM python:3.12-slim

WORKDIR /app

COPY environment.txt .
RUN python3 -m pip install -r environment.txt

COPY src/ src/
COPY docker/start.sh docker/helpers.sh docker/db_init.sh docker/create_reader_role.py /app/
COPY docker/db_connection.yml config/db_connection.yml
COPY config/browser_policy.yml config/browser_policy.yml

RUN chmod +x /app/start.sh /app/db_init.sh

EXPOSE 8501

CMD ["/app/start.sh"]
