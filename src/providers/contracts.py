from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class OpportunityProvider(Protocol):
    source_name: str
    def list_projects(self, filters: dict[str, Any] | None = None, page_token: str | None = None) -> dict[str, Any]: ...
    def get_project_details(self, source_id: str) -> dict[str, Any]: ...
    def health_check(self) -> dict[str, Any]: ...


@runtime_checkable
class ContractorProvider(Protocol):
    source_name: str
    def list_contractors(self, filters: dict[str, Any] | None = None, page_token: str | None = None) -> dict[str, Any]: ...
    def get_contractor_details(self, source_id: str) -> dict[str, Any]: ...
    def health_check(self) -> dict[str, Any]: ...


@runtime_checkable
class ContractorEnrichmentProvider(Protocol):
    source_name: str
    def enrich_contractor(self, source_id: str) -> dict[str, Any] | None: ...
    def health_check(self) -> dict[str, Any]: ...


__all__ = ["ContractorEnrichmentProvider", "ContractorProvider", "OpportunityProvider"]
