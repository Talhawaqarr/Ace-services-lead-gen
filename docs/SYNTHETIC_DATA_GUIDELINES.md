# Synthetic Data Guidelines — ACE Services

Purpose: Define rules and fixtures for creating synthetic datasets used in local development and testing. Synthetic data must never be presented as real.

Principles
- Clearly label all synthetic data files and fixtures with `synthetic_` prefix and include a README header stating they are artificial.
- Do not mix synthetic datasets with any licensed or third-party data unless the license allows.
- Provide coverage for key test cases: good matches, bad matches, geographic mismatch, trade mismatch, size mismatch, missing data, duplicates, ambiguous matches.

Files to include
- `fixtures/synthetic_projects.json` — ~200 example projects across multiple states and trades
- `fixtures/synthetic_contractors.json` — ~500 example contractor records with varying completeness
- `fixtures/synthetic_matches.json` — labeled expected matches for evaluation
- `scripts/load_synthetic_data.py` — helper to import fixtures into local Postgres

Labeling
- Each record must include `synthetic: true` and `source: synthetic` fields.
- Provide a `SYNTHETIC_DATA_LICENSE.md` that clarifies reuse and sharing restrictions.

Usage
- Developers should run `scripts/load_synthetic_data.py --drop && --seed` to prepare a local dev DB.
- CI should use a smaller fixture set derived from the main synthetic fixtures for faster runs.

These guidelines ensure safe, repeatable development without requiring any paid data sources.
