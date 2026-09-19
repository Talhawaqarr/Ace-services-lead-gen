# Matching Evaluation Report

## SYNTHETIC DEVELOPMENT VALIDATION ONLY

This evaluation is limited to the currently supported features in the deterministic matcher and is not a production performance claim.

## In-scope features
The evaluation currently covers only:

- trade overlap
- geography
- bid timing

## Evaluation setup
The test suite in [src/tests/test_matching.py](src/tests/test_matching.py) exercises:

- trade normalization
- trade overlap and mismatch
- same-city and same-state geography
- missing trade and missing geography semantics
- bid timing support
- normalized match_score in [0,1]
- confidence labeling
- deterministic ranking and tie-breaking
- repeated identical input

## Findings

1. Same-city same-state same-trade matches rank first.
2. Trade mismatch lowers the score and records an explicit negative reason.
3. Missing trade data is treated as UNKNOWN rather than a mismatch.
4. Missing city information is tolerated when state information is still useful.
5. Re-running identical input yields the same ranking and output.

## Current interpretation
This is a synthetic development validation of the actual supported deterministic scoring model.
It does not represent real-world match quality, production precision, or operational performance.

## Recommended next evaluation after schema expansion
Only once the canonical model gains additional fields should evaluation include:

- project value compatibility
- contractor track record or licensing signals
- richer geography features
- future hybrid or ML scoring

Until then, the only valid evaluation is the current synthetic validation of the supported deterministic contract.
