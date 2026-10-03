from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.providers.contracts import OpportunityProvider


class SAMGovProvider(OpportunityProvider):
    """Local, deterministic SAM.gov-shaped opportunity provider.

    This project does not perform live SAM.gov API calls. The fixture is synthetic and
    intentionally labeled as local test data. It mirrors the official SAM.gov contract
    fields verified in the Phase 8 design work while remaining fully offline.
    """

    def __init__(self, fixture_path: str | None = None):
        base = Path(__file__).resolve().parents[2]
        self.source_name = "samgov"
        self.fixture_path = Path(fixture_path) if fixture_path else base / "docs" / "fixtures" / "phase9_samgov_opportunities.json"
        self.records = self._load_fixture()

    def _load_fixture(self) -> list[dict[str, Any]]:
        if not self.fixture_path.exists():
            return []
        with open(self.fixture_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("projects", [])
        return []

    def list_projects(self, filters: dict[str, Any] | None = None, page_token: str | None = None):
        records = self.records
        if filters:
            source_id = filters.get("source_id")
            if source_id:
                records = [row for row in records if str(row.get("source_id")) == str(source_id)]
            state = filters.get("state")
            if state:
                records = [row for row in records if ((row.get("placeOfPerformance") or {}).get("state") or "").upper() == str(state).upper()]
            limit = filters.get("limit")
            if limit is not None:
                try:
                    bounded = max(int(limit), 1)
                except (TypeError, ValueError):
                    bounded = len(records)
                records = records[:bounded]
        return {
            "projects": records,
            "next_page_token": None,
            "meta": {
                "source": self.source_name,
                "fixture": str(self.fixture_path),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "synthetic": True,
                "live_integration_disabled": True,
            },
        }

    def get_project_details(self, source_id: str):
        for row in self.records:
            if str(row.get("source_id") or row.get("solicitationNumber")) == str(source_id):
                return row
        raise KeyError(source_id)

    def health_check(self):
        return {
            "status": "ok",
            "info": {
                "source": self.source_name,
                "fixture": str(self.fixture_path),
                "synthetic": True,
                "live_integration_disabled": True,
            },
        }
