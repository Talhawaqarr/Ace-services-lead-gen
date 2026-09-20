from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.providers.contracts import ContractorEnrichmentProvider


class FixtureContractorEnrichmentProvider(ContractorEnrichmentProvider):
    """Offline enrichment source using explicitly synthetic contact records."""

    source_priority = 10

    def __init__(self, fixture_path: str | None = None):
        base = Path(__file__).resolve().parents[2]
        self.source_name = "fixture-enrichment"
        self.fixture_path = Path(fixture_path) if fixture_path else base / "docs" / "fixtures" / "phase44_contractor_enrichment.json"
        self.records = self._load_fixture()

    def _load_fixture(self) -> dict[str, dict[str, Any]]:
        if not self.fixture_path.exists():
            return {}
        with open(self.fixture_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        rows = payload.get("contractors", []) if isinstance(payload, dict) else payload
        return {str(row["source_id"]): row for row in rows if isinstance(row, dict) and row.get("source_id")}

    def enrich_contractor(self, source_id: str) -> dict[str, Any] | None:
        row = self.records.get(str(source_id))
        if row is None:
            return None
        result = dict(row)
        result["source"] = self.source_name
        result["source_priority"] = int(result.get("source_priority", self.source_priority))
        result["fetched_at"] = datetime.now(timezone.utc).isoformat()
        result["synthetic"] = True
        return result

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "info": {"source": self.source_name, "fixture": str(self.fixture_path), "synthetic": True, "source_priority": self.source_priority}}
