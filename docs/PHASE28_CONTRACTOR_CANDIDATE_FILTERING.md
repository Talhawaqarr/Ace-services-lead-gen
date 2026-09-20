# Phase 28 — Contractor Candidate Filtering

Phase 28 reduces the contractor candidate set before scoring.

Discovery now applies only deterministic, evidence-backed filters:

- if both project and contractor states are known, they must match;
- if both project and contractor trade sets are known, they must overlap;
- missing contractor trade data remains eligible rather than being treated as a mismatch.

The deterministic matcher remains responsible for scoring and ranking the surviving candidates.

This is intended to reduce unnecessary match records while preserving candidates where evidence is incomplete.
