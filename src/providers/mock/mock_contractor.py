import json
from typing import Dict, Any
from pathlib import Path


def _fixture_path(name: str) -> str:
    p = Path(__file__).resolve()
    for parent in p.parents:
        candidate = parent / "docs" / "fixtures" / name
        if candidate.exists():
            return str(candidate)
    return str(Path(__file__).resolve().parents[3] / "docs" / "fixtures" / name)


class MockContractorProvider:
    def __init__(self):
        path = _fixture_path("synthetic_contractors.json")
        with open(path, "r", encoding="utf8") as f:
            self.contractors = json.load(f)

    def search_companies(self, query: str, page_token: str = None) -> Dict[str, Any]:
        q = query.lower() if query else ""
        results = [c for c in self.contractors if q in c.get("company_name", "").lower()]
        return {"companies": results, "next_page_token": None}
