from typing import Protocol, List, Dict, Any


class BidProvider(Protocol):
    def list_projects(self, filters: Dict[str, Any], page_token: str = None) -> Dict[str, Any]:
        ...


class ProjectProvider(Protocol):
    def get_project_details(self, source_id: str) -> Dict[str, Any]:
        ...


class ContractorProvider(Protocol):
    def search_companies(self, query: str, page_token: str = None) -> Dict[str, Any]:
        ...


class EnrichmentProvider(Protocol):
    def enrich_company(self, company_id: str) -> Dict[str, Any]:
        ...


class GeocodingProvider(Protocol):
    def geocode(self, address: str) -> Dict[str, Any]:
        ...


class EmailProvider(Protocol):
    def send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...


class LLMProvider(Protocol):
    def generate(self, prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...
