# Phase 27 — Deterministic Project Trade Signals

Phase 27 promotes conservative trade signals from already-ingested opportunity data into the canonical `Project.trades` field when explicit trades are absent.

Current rules use stable NAICS prefixes first, then a small set of explicit scope keywords. Existing explicit trade data always wins. This is deterministic enrichment, not an ML classification claim.

The purpose is to give the existing matcher usable trade evidence instead of treating every SAM.gov opportunity as having unknown trade data.

No live provider, paid API, LLM, or embedding service is introduced.
