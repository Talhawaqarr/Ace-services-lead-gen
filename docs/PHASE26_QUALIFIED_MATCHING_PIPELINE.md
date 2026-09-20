# Phase 26 — Qualified Matching Pipeline

Phase 26 connects opportunity qualification to contractor matching.

## Behavior

The existing local fixture pipeline remains unchanged for regression compatibility. The new `run_qualified_fixture_pipeline()` path:

1. ingests SAM.gov-shaped opportunity fixtures;
2. ingests SAM.gov-shaped contractor fixtures;
3. applies the Phase 25 deterministic opportunity qualification rules;
4. discovers contractor candidates only for qualified opportunities;
5. runs the existing deterministic matcher;
6. persists match records through the existing review workflow.

The default qualification criteria are the same as Phase 25: active opportunities and construction relevance marked `likely`. An optional response-deadline window can further restrict the queue.

## Current boundary

This remains a local fixture workflow. It does not call live SAM.gov, use paid feeds, send email, or invoke an LLM.

The original all-opportunity fixture pipeline remains available so earlier ingestion/matching regression tests continue to cover the lower-level workflow.
