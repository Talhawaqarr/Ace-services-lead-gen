#!/bin/sh
set -eu

python - <<'PY'
import os
import time
import psycopg2

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        conn = psycopg2.connect(url, connect_timeout=3)
        conn.close()
        break
    except psycopg2.OperationalError:
        if attempt == 29:
            raise
        time.sleep(2)
PY

alembic upgrade head
exec uvicorn src.api:app --host 0.0.0.0 --port 8000
