# ACE Services — Development README (Phase 1 $0 MVP)

Purpose: Steps to run the developer-safe foundation locally without paid APIs.

Prereqs:
- Python 3.10+
- PostgreSQL running locally and accessible via `DATABASE_URL` in `.env` (default: postgresql://localhost/ace_dev)
- (Optional) Redis if you intend to run background jobs

Quick start:

1. Create and activate a virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create local Postgres DB

```bash
createdb ace_dev
```

3. Run migrations

```bash
alembic upgrade head
```

4. Load synthetic data

```bash
python src/scripts/load_synthetic_data.py
```

5. Verify dev setup

```bash
python src/scripts/verify_dev_setup.py
```

6. Run the test suite

```bash
docker compose exec -T api python -m pytest
```

Run a single phase (example: Phase 11):

```bash
docker compose exec -T api python -m pytest src/tests/test_phase11_samgov_contractors.py -v
```

Notes:
- All external providers use `providers/mock` by default.
- DRY_RUN is `true` by default in `.env.example` — no real emails or API calls will be made.
- The `db` service is intentionally NOT published to the host (see
  `src/tests/test_phase19_container_hardening.py`); it is reachable only as
  `db:5432` inside the compose network. Run tests through `docker compose exec`
  against the `api` service (above) rather than on the host, otherwise pytest
  will try `localhost:5432` from `.env` and fail with `Connection refused`.
  The `api` container already has `DATABASE_URL=...@db:5432/ace_dev` injected.
