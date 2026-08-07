# Deployable Boo connector image. LIVE GATE PENDING: needs real env (see .env.example) and a
# public HTTPS ingress for Cowork to reach the MCP endpoint.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BOO_DB_PATH=/data/boo.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY boo_connector ./boo_connector
COPY migrations ./migrations

# Persist the SQLite db (or point BOO_DB_PATH at a managed Postgres in production).
VOLUME ["/data"]

RUN useradd --create-home --uid 10001 boo && mkdir -p /data && chown boo /data
USER boo

# Migrations run automatically on Store() init. The server module wires the MCP transport.
CMD ["python", "-m", "boo_connector.server"]
