# Matching Contract — ACE Services

## Current contract (Phase 2 deterministic engine)

This contract reflects the actual current implementation, not future architecture.

### In-scope input fields
The deterministic matcher is only allowed to read fields that exist in the current model and migrations:

- `project.city`, `project.state`, `project.latitude`, `project.longitude`, `project.trades`, `project.bid_date`
- `contractor.city`, `contractor.state`, `contractor.latitude`, `contractor.longitude`, `contractor.trades`

No other fields are considered available to the current matcher.

### Output schema
Each match result includes:

- `project_id`
- `contractor_id`
- `contractor_name`
- `raw_score` (float)
- `max_available_score` (float)
- `match_score` (float in [0,1])
- `feature_completeness` (float in [0,1])
- `confidence` (LOW | MEDIUM | HIGH)
- `positive_factors` (list of strings)
- `negative_factors` (list of strings)
- `unknown_factors` (list of strings)
- `components` (breakdown object)
- `matcher_version`
- `ranking`

### Normalized score contract
The public/domain score is normalized to [0,1]:

- `match_score = raw_score / max_available_score`
- if `max_available_score == 0`, then `match_score = 0.0`

This ensures that missing information does not become a mismatch and that available features are normalized against the maximum applicable weight for those known features only.

### Component weights
Supported current weights:

- trade overlap = 35
- geography = 18 max, with state-only=12 and same-city=18
- bid timing = 5

The current matcher does not claim normalized weights beyond the supported components above.

### Confidence semantics
Confidence is deterministic and based on both score strength and feature completeness:

- HIGH if `match_score >= 0.75` and `feature_completeness >= 0.67`
- MEDIUM if `match_score >= 0.45` and `feature_completeness >= 0.34`
- LOW otherwise

Confidence is not a probability estimate.

### Missing-data semantics
The matcher explicitly distinguishes:

- MATCH: a positive known condition exists
- MISMATCH: a known incompatible condition exists (state mismatch, trade mismatch)
- UNKNOWN: required data is absent or unsupported

Examples:

- missing contractor city is UNKNOWN, not mismatch
- missing project trade is UNKNOWN, not mismatch
- missing bid date is UNKNOWN, not a negative match

### Versioning and determinism
- `matcher_version` is a required output field
- same input must return the same ordering and score breakdown
- tie-breaking uses `contractor_name` ascending

### Not available / future
The following are explicitly out of scope for the current engine and must not be used as if they exist:

- contractor capacity or financial fit
- license status
- years in business
- service areas
- project type
- semantic similarity / embeddings / AI
- any future Phase 3 features

These remain `NOT_AVAILABLE` or `FUTURE` in the feature catalog, not implemented placeholders.
