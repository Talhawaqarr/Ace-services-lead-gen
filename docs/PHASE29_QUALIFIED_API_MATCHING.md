# Phase 29 — Qualified API Matching

The project match-generation endpoint now follows the same qualification and candidate-discovery rules as the offline pipeline.

Before generating matches it requires the opportunity to pass the default qualification rules (active and construction-relevant). It then uses deterministic contractor candidate filtering for the project's source, state, and available trade evidence.

An unqualified opportunity returns HTTP 409 and no matches are generated.
