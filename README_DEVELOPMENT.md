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

Notes:
- All external providers use `providers/mock` by default.
- DRY_RUN is `true` by default in `.env.example` — no real emails or API calls will be made.
