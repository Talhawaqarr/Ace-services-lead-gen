from typing import Dict, Any


class MockEnrichmentProvider:
    def enrich_company(self, company_id: str) -> Dict[str, Any]:
        # Return deterministic minimal enrichment
        return {
            "company_id": company_id,
            "licenses": [],
            "emails": [],
            "confidence_scores": {"overall": 0.5},
        }
