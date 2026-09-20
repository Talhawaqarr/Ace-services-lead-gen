# Phase 25 — Opportunity Qualification

## Goal

Turn the canonical opportunity record into a deterministic lead-generation queue without paid services, ML, or outreach.

## Qualification rules

The default qualification requires ACTIVE status and source provenance marked construction relevance as likely. If a deadline window is requested, a valid response deadline must fall inside that window.

## API

GET /opportunities will expose limit/offset, source, state, active_only, construction_only, and deadline_within_days filters. Results are ordered by response deadline, with missing deadlines last.

## Boundary

This is deterministic qualification, not an ML prediction or business-value ranking. It uses the source's existing construction-relevance heuristic. Live SAM.gov access, paid feeds, enrichment, and outreach remain separate phases.
