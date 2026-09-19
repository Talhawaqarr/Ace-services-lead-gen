# Matching Scoring Specification

## Current implementation status
This document describes the actual deterministic matcher currently implemented in the repository. It does not describe future or unsupported features.

## Supported scoring components
The current engine uses only the following supported components:

- `trade_overlap` = up to 35
- `geography` = up to 18
- `bid_timing` = up to 5

## Exact formula

The engine computes a raw score for each supported feature:

- trade overlap: `35 * overlap_count / max(project_trade_count, 1)`
- same city + same state: `18`
- same state only: `12`
- distance <= 25 km: `14`
- distance <= 100 km: `8`
- bid date present: `5`

Then it normalizes over the maximum available score for the known features only:

`match_score = raw_score / max_available_score` when `max_available_score > 0`

No unsupported feature is included in the numerator or denominator.

## Missing-data semantics

- missing project trade or contractor trade = UNKNOWN, not mismatch
- missing contractor city but same state known = same-state geography still counts; missing city is not a geographic mismatch
- missing bid date = UNKNOWN; no penalty
- known state mismatch = explicit mismatch and contributes 0 to geography

This is the required distinction for the current implementation.

## Confidence semantics
The confidence label is derived deterministically from both score strength and feature completeness:

- HIGH if `match_score >= 0.75` and `feature_completeness >= 0.67`
- MEDIUM if `match_score >= 0.45` and `feature_completeness >= 0.34`
- LOW otherwise

This is a score label, not a probability estimate.

## Hard disqualifiers
There are no hard disqualifiers in the current Phase 2 deterministic engine.

The system treats missing information as UNKNOWN and keeps the contract conservative.

## Explainability contract
Every explanation in the current implementation must correspond to an actual observed condition:

- positive: known trade overlap, same state, same city, within distance threshold, bid date present
- negative: known mismatch only when supported by actual data
- unknown: explicit `unknown_factors` list when data is absent

No explanation may assert historical capacity, licensing, or service area coverage if those fields are not present in the canonical model.
