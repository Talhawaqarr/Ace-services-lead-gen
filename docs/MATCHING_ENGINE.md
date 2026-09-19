# Matching Engine Design

## CURRENT STATUS
This document describes the actual current implementation only.

The current Phase 2 engine is intentionally a deterministic, in-memory scoring layer built on the actual Phase 1 canonical model. It does not implement embeddings, ML, service-area logic, project history, or any other future feature.

## Current in-scope inputs
- `project.city`, `project.state`, `project.latitude`, `project.longitude`, `project.trades`, `project.bid_date`
- `contractor.city`, `contractor.state`, `contractor.latitude`, `contractor.longitude`, `contractor.trades`

## Current deterministic features
- `trade_overlap`
- `geography`
- `bid_timing`

## Current formula
- trade overlap contributes up to 35
- geography contributes up to 18
- bid timing contributes up to 5
- raw score is the sum of the known component score values
- public match score is normalized to [0,1] using the max available score for the known supported features

## Current output contract
The matcher returns a ranked list with:

- match_score in [0,1]
- raw_score
- max_available_score
- feature_completeness
- confidence (LOW / MEDIUM / HIGH)
- positive_factors
- negative_factors
- unknown_factors
- components breakdown
- matcher_version
- ranking

## Current missing-data semantics
- UNKNOWN is the default for missing data
- MISMATCH is only used for actual incompatible values that are known
- missing project or contractor trade is not treated as mismatch
- missing contractor city is not treated as mismatch
- missing bid date is not treated as failure

## FUTURE / NOT AVAILABLE
The following are explicitly not available in the current implementation and must remain excluded until a later schema change introduces those fields:

- contractor value capacity
- historical project value range
- years in business
- license status
- project type
- service areas
- activity flags
- embeddings / semantic similarity
- ML ranking models

## Persistence status
This Phase 2 implementation is intentionally in-memory only. No match persistence is introduced in the current schema.
