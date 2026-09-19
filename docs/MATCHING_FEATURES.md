# Matching Feature Availability

## Scope
This document reflects the actual Phase 1 canonical model and the currently implemented deterministic matcher only.

## Canonical model in scope
The current implementation may only use fields actually present in the canonical models and migrations:

- Project: `name`, `source`, `source_id`, `city`, `state`, `latitude`, `longitude`, `trades`, `bid_date`, `estimated_value`
- Contractor: `company_name`, `normalized_name`, `source`, `source_id`, `city`, `state`, `latitude`, `longitude`, `trades`

## Supported features

| Feature | Canonical source field(s) | Normalization | Scoring contribution | Missing-data behavior | Evidence/explanation behavior | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Trade overlap | `project.trades`, `contractor.trades` | normalize aliases (general, electrical, civil, plumbing, concrete, landscaping, education) | raw contribution up to 35; overlap proportion relative to project trade set | missing project or contractor trades -> unknown, not mismatch | positive: `Trade overlap: electrical`; negative: actual mismatch only if both sides are known and non-overlapping | IMPLEMENTED |
| Geography | `project.city`, `project.state`, `project.latitude`, `project.longitude`, `contractor.city`, `contractor.state`, `contractor.latitude`, `contractor.longitude` | lowercase city/state; Haversine distance in km | same city same state = 18; same state = 12; <=25 km = 14; <=100 km = 8 | missing city/state/distance becomes unknown; state mismatch is explicit mismatch | positive: `Same city: Sacramento`; negative: `State mismatch: CA vs TX` only when both states are known | IMPLEMENTED |
| Bid timing | `project.bid_date` | presence check only | raw contribution 5 when bid date exists | missing bid date = unknown, no penalty | positive: `Project has bid date available` | IMPLEMENTED |
| Project value | `project.estimated_value` | numeric conversion only | currently not used in public score because value-fit is not supported by actual model | unknown value is excluded from the denominator | not used by current matcher | NOT_AVAILABLE |
| Contractor value capacity | none in current model | none | none | none | none | NOT_AVAILABLE |
| Contractor years in business | none in current model | none | none | none | none | NOT_AVAILABLE |
| Contractor license status | none in current model | none | none | none | none | NOT_AVAILABLE |
| Service area | none in current model | none | none | none | none | NOT_AVAILABLE |
| Project type | none in current model | none | none | none | none | NOT_AVAILABLE |
| Project history | none in current model | none | none | none | none | NOT_AVAILABLE |
| Contractor historical project value | none in current model | none | none | none | none | NOT_AVAILABLE |
| Activity / inactive status | none in current model | none | none | none | none | NOT_AVAILABLE |
| Semantic similarity / embeddings | not in current model and no provider contract in Phase 1 | none | none | none | none | FUTURE |
| Hybrid or supervised scoring | future phase only | none | none | none | none | FUTURE |

## Semantics

- MATCH: a known positive condition is observed
- MISMATCH: a known incompatible value is observed (for example, known state mismatch)
- UNKNOWN: required data is absent or unsupported

Missing information must not automatically become a mismatch.

## Rule
The current deterministic matcher must not access, infer, or assume any field that is not explicitly present in the canonical model above.
