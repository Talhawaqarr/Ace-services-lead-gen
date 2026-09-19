#!/usr/bin/env python3
"""
Simple script to load synthetic fixtures into a local Postgres database for development.
This is intentionally minimal and should be adapted to the actual DB schema before use.
"""
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db import get_session
from src.models.core import Project, Contractor

load_dotenv()

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "fixtures")


def load_json(filename):
    with open(filename, "r", encoding="utf8") as f:
        return json.load(f)


def upsert_projects(session, projects):
    inserted = 0
    for p in projects:
        existing = session.query(Project).filter_by(source=p.get("source", "synthetic"), source_id=p.get("id")).first()
        if existing:
            continue
        proj = Project(
            name=p.get("title") or p.get("name"),
            source=p.get("source", "synthetic"),
            source_id=p.get("id"),
            city=p.get("city"),
            state=p.get("state"),
            latitude=p.get("latitude"),
            longitude=p.get("longitude"),
            trades=p.get("trade") or p.get("trades"),
            bid_date=p.get("bid_date"),
            estimated_value=p.get("estimated_value"),
            provenance={"synthetic": True},
        )
        session.add(proj)
        inserted += 1
    session.commit()
    return inserted


def upsert_contractors(session, contractors):
    inserted = 0
    for c in contractors:
        source = c.get("source") or "synthetic"
        source_id = c.get("id")
        existing = session.query(Contractor).filter_by(source=source, source_id=source_id).first()
        if existing:
            continue
        cont = Contractor(
            company_name=c.get("company_name"),
            normalized_name=c.get("company_name"),
            source=source,
            source_id=source_id,
            city=c.get("city"),
            state=c.get("state"),
            trades=c.get("trades"),
            primary_email=c.get("primary_email"),
            provenance={"synthetic": True},
        )
        session.add(cont)
        inserted += 1
    session.commit()
    return inserted


def main():
    projects = load_json(os.path.join(FIXTURES_DIR, "synthetic_projects.json"))
    contractors = load_json(os.path.join(FIXTURES_DIR, "synthetic_contractors.json"))
    session = get_session()
    p = upsert_projects(session, projects)
    c = upsert_contractors(session, contractors)
    print(f"Loaded synthetic fixtures: projects_inserted={p} contractors_inserted={c}")


if __name__ == "__main__":
    main()
