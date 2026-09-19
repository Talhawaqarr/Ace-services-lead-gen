import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SAMGovContractorProvider:
    """Fixture-backed SAM.gov-style contractor source.

    This implementation intentionally remains local-only. It keeps source identity
    anchored on source + source_id and preserves all raw source metadata without
    introducing speculative fields into the runtime Contractor schema.
    """

    def __init__(self, fixture_path: str | None = None):
        base = Path(__file__).resolve().parents[2]
        self.source_name = "samgov"
        self.fixture_path = Path(fixture_path) if fixture_path else base / "docs" / "fixtures" / "phase11_samgov_contractors.json"
        self.records = self._load_fixture()

    def _load_fixture(self) -> list[dict[str, Any]]:
        if not self.fixture_path.exists():
            return []
        with open(self.fixture_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("contractors", [])
        return []

    def list_contractors(self, filters: dict[str, Any] | None = None, page_token: str | None = None):
        records = list(self.records)
        if filters:
            source_id = filters.get("source_id")
            if source_id:
                records = [row for row in records if str(row.get("source_id")) == str(source_id)]
            company_name = filters.get("company_name")
            if company_name:
                records = [row for row in records if str(row.get("company_name") or "").lower() == str(company_name).lower()]
        return {
            "contractors": records,
            "next_page_token": None,
            "meta": {
                "source": self.source_name,
                "fixture": str(self.fixture_path),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "synthetic": True,
                "live_integration_disabled": True,
            },
        }

    def get_contractor_details(self, source_id: str):
        for row in self.records:
            if str(row.get("source_id")) == str(source_id):
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
