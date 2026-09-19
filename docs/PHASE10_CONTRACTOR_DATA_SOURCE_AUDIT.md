# Phase 10 — Contractor Data Source + Discovery Architecture Audit

## 1. Purpose and scope

This phase does not implement contractor discovery. It audits the current repository and the most relevant public contractor data sources to determine what is feasible in a local, zero-cost development environment and what a future contractor data contract should look like.

The goal is to keep ACE honest:
- do not invent fields that are not currently supported by the runtime model
- do not assume public contractor data is automatically usable for mass outreach
- do not treat website browsing as equivalent to a free API contract
- do not implement a live contractor source without explicit source validation and terms review

## 2. Repository findings: what the current runtime actually supports

### Current runtime fields

The current runtime canonical fields for contractor records are defined in [src/models/core.py](../src/models/core.py) and are explicitly documented in [docs/CANONICAL_MODELS.md](CANONICAL_MODELS.md).

Current Contractor runtime fields:
- id
- company_name
- normalized_name
- source
- source_id
- city
- state
- trades
- primary_email
- provenance

This is the actual runtime model used by the deterministic matcher and review workflow.

### Supporting code paths

Relevant repository evidence:
- [src/models/core.py](../src/models/core.py): canonical Contractor model
- [src/providers/interfaces.py](../src/providers/interfaces.py): provider abstractions
- [src/providers/mock/mock_contractor.py](../src/providers/mock/mock_contractor.py): local mock contractor provider
- [src/matching/engine.py](../src/matching/engine.py): current supported matcher features
- [src/review/service.py](../src/review/service.py): persisted contractor rows and match persistence
- [src/templates/index.html](../src/templates/index.html): review workspace display
- [src/api.py](../src/api.py): review and ingestion endpoints
- [src/ingestion/service.py](../src/ingestion/service.py): ingestion lifecycle

### Current runtime contract

The current deterministic matcher only knows how to work with fields that are explicitly present in the canonical model and the matching design documents.

Supported contractor-side fields today:
- company_name / normalized_name
- source and source_id
- city and state
- trades
- primary_email (present in schema but not used by the current deterministic scoring logic)
- provenance

Current matching features are limited to:
- trade overlap
- geography
- bid timing

This is documented in [docs/MATCHING_FEATURES.md](MATCHING_FEATURES.md) and [docs/MATCHING_ENGINE.md](MATCHING_ENGINE.md).

### Important boundary

The following are future ideas, not current runtime fields:
- website
- phone
- license number
- license status
- service area
- project history
- contractor size
- classification / NAICS on the contractor record
- previous project descriptions
- verification status
- historical project evidence
- confidence score
- entity merge history

These are architecture intent only and must not be treated as already implemented.

## 3. ACE contractor data requirements

### CURRENT RUNTIME FIELDS

The current repo already supports:
- company_name
- normalized_name
- source
- source_id
- city
- state
- trades
- primary_email
- provenance

These are sufficient for basic synthetic/local contractor records and the current deterministic match workflow.

### FUTURE BUSINESS FIELDS

The following are needed for a realistic contractor discovery workflow, but are not currently implemented and should be treated as future design requirements:
- legal/business identity
- DBA / alias names
- website
- business location
- ZIP
- service area / trade area
- trade / specialty
- construction type
- NAICS
- federal or state license number
- license state
- license status
- contractor classification
- business status
- project/value capacity
- public phone number
- business email
- source URL
- verification status
- data freshness / fetched_at
- provenance / audit trail
- confidence / completeness
- history of public projects and awards

Not all of these fields will be available from every source, and some may be commercially restricted.

## 4. Source-by-source evidence

### Summary matrix

| Source | Geography | Contractor identity | Trade | Location | License | Contact | Historical project evidence | API | Authentication | Free access | Machine-readable | Automation suitability | Data freshness | Terms/usage concerns | ACE relevance | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SAM.gov entity / registration data | U.S. federal | VERIFIED | VERIFIED / INFERRED | VERIFIED | INFERRED | INFERRED | INFERRED | VERIFIED for official API/data services | VERIFIED: account likely required | VERIFIED for public access, but not necessarily free API without credentials | VERIFIED / UNKNOWN | MODERATE | VERIFIED / INFERRED | Public government terms apply | Primary candidate for government contractor identity and registration context | Not a complete contractor directory; more identity/context than direct contractor scoring |
| USAspending | U.S. federal | VERIFIED | VERIFIED / INFERRED | VERIFIED | UNKNOWN | UNKNOWN | VERIFIED | VERIFIED | UNKNOWN / often public | VERIFIED | VERIFIED | HIGH | HIGH | Supplemental / historical evidence | Post-award only; not new contractor discovery by itself |
| State contractor license registries | State-specific | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED / INFERRED | UNKNOWN | VERIFIED / UNKNOWN | VERIFIED / UNKNOWN | VERIFIED / UNKNOWN | VERIFIED / UNKNOWN | MODERATE | HIGH | State terms vary | Strong supplemental / validation source | Fragmented, inconsistent, often state-specific |
| OpenCorporates | Multi-jurisdiction | VERIFIED | UNKNOWN | VERIFIED / INFERRED | UNKNOWN | UNKNOWN | UNKNOWN | VERIFIED | VERIFIED: API key / plan | FREE TIER / PAID PLANS | VERIFIED | MODERATE | MODERATE | Licensing and redistribution restrictions | Good entity normalization and legal identity support | Not a direct construction contractor feed |
| ConstructConnect | U.S. / broad construction | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | VERIFIED / INFERRED | VERIFIED | VERIFIED / RESTRICTED | VERIFIED: paid account | NO | VERIFIED | HIGH | HIGH | Commercial licensing and terms | Post-MVP commercial contractor discovery | Paid access required |
| Dodge | U.S. / broad construction | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | VERIFIED / INFERRED | VERIFIED | VERIFIED / RESTRICTED | VERIFIED: paid account | NO | VERIFIED | HIGH | HIGH | Commercial licensing and terms | Post-MVP commercial contractor discovery | Paid access required |
| PlanHub / Blue Book / similar | U.S. / local project feeds | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | VERIFIED / INFERRED | VERIFIED | VERIFIED / RESTRICTED | VERIFIED: paid account | NO | VERIFIED | HIGH | HIGH | Commercial licensing and terms | Post-MVP enrichment | Paid access required |
| Public business directory / chamber / city directories | Local / regional | VERIFIED / INFERRED | UNKNOWN | VERIFIED | UNKNOWN | VERIFIED / INFERRED | UNKNOWN | UNKNOWN | UNKNOWN | SOMETIMES | UNKNOWN | LOW / MODERATE | MODERATE | Public web terms vary | Supplemental | Not reliable enough for core workflow |

### Evidence notes by source

#### A. SAM.gov entity / registration data

Verified / documented:
- SAM.gov is the official U.S. federal contractor registration and contract-opportunity system.
- The entity and registration side contains official public identity and organizational information relevant to contractor/firm identity.
- The government data model includes organization and agency metadata, legal-name-oriented identity, and activity metadata.
- Public access exists, but official API access may require account-based or service-based access paths.

Implications:
- SAM.gov is a strong candidate for contractor identity and registration context.
- It is more useful as an identity / verification source than as a complete contractor-discovery directory.
- It is not enough to replace a full contractor list or trade/coverage database.

#### B. USAspending

Verified / documented:
- USAspending exposes award and awardee records.
- Recipient names, locations, and award history are available.
- This is valuable as historical project evidence and federal contractor history.
- It is not equivalent to a live contractor discovery directory.

Implications:
- Best used as historical evidence or enrichment, not as a primary discovery use case.
- Strong for historical federal performance evidence and award tracking.

#### C. State contractor/license registries

Verified / inferred:
- Many states publish public contractor license registries or permit lookups.
- The data often includes license number, trade classification, status, business address, and licensed trades.
- Coverage and access patterns vary considerably by state.

Implications:
- Strong supplemental source for validation, licensing, and local contractor market context.
- Not a single universal model; each state requires separate contract or parsing strategy.
- A future contractor registry strategy should treat these as per-state adapters, not a single monolithic source.

#### D. OpenCorporates

Verified / documented:
- OpenCorporates is a public company registry aggregator with API access and account tiers.
- It is useful for legal entity normalization and company identity resolution.
- It is not a direct reconstruction of contractor specialization or bidding activity.

Implications:
- Useful for entity identity, aliases, and legal structure.
- Not enough for trade specialization or live opportunity discovery by itself.

#### E. Commercial construction data providers

Verified / inferred:
- ConstructConnect, Dodge, PlanHub, Blue Book, and similar services provide contractor/project data and plan-room information.
- They are generally paid / licensed and have restrictive commercial terms.
- They are not a no-cost local development path.

Implications:
- Useful as post-MVP commercial enrichment or procurement-lead sources.
- Not suitable for a $0 local development environment.

## 5. $0 development path

### What is possible without paying money

The following are realistic within a zero-cost local path:
- synthetic contractor fixtures
- deterministic local contractor records in tests
- local entity normalization logic with explicit source_id identities
- parser or adapter skeletons for free/public source contracts
- local provenance storage and raw contractor payload retention
- test fixtures that model likely source shapes
- no-network local-first development with DRY_RUN behavior

### What is not equivalent to a free API

These are not interchangeable:
- public website search
- public browse pages
- manual form submissions
- pages behind logins or paywalls
- scraping protected content
- public PDFs without clear reuse rights

A contractor source must be explicitly validated as a documented public API, data feed, or generated data source before the repo should treat it as a real automation source.

### Strongest fixture contract candidate

The strongest fixture candidate for the future is not a commercial database; it is a conservative public-source shape that can model:
- company name
- source + source_id
- city / state / ZIP
- trade list
- license status or public classification
- business website / phone when present
- provenance / fetched_at / source URL

This should be built from a combined model of:
- real public government sources where legally acceptable
- synthetic fixture data for tests
- explicit provenance-only records for unsupported fields

## 6. Contractor identity strategy

The most important design rule is:
- source + source_id is the stable identity key
- company name alone is not a universal identity key

Why this matters:
- the same company may appear under multiple legal names, DBAs, or variants
- a single contractor may appear in multiple sources with different identifier systems
- public entity records may update names, addresses, or business status over time
- source-specific identities are necessary while entity resolution remains future work

A realistic future contractor identity contract should track:
- source
- source_id
- legal_name
- dba_name(s)
- normalized_name
- website_domain
- address_hash or normalized address
- registration jurisdiction
- alias set
- verification status

This is future design, not current runtime behavior.

### Entity resolution is future work

The repo must not implement automatic cross-source entity merging in this phase. It should keep source identity strict and preserve provenance so that later entity-resolution logic can be built safely.

## 7. Future normalized contractor record

The following is a proposed normalized future contract, not a production schema change.

| Source field | Normalized field | Transformation | Required/Optional | Provenance | Confidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| company legal name | legal_name | trim + canonical case | required when present | source provenance | HIGH | legal entity identity |
| DBA / alternate name | aliases | list of normalized names | optional | source provenance | MEDIUM | not always present |
| source-specific ID | source_id | preserve as provided | required | source provenance | HIGH | stable identity key |
| public website | website | normalized URL | optional | source provenance | MEDIUM | may be absent or not public |
| business address | address | normalized address object | optional | source provenance | MEDIUM | city/state/ZIP may be more reliable |
| city | city | title-case | optional | source provenance | HIGH | likely usable for geography |
| state | state | uppercase 2-letter | optional | source provenance | HIGH | useful for matching |
| ZIP | zip | preserve normalized string | optional | source provenance | MEDIUM | may not be present |
| trade categories | trades | normalized list | optional | source provenance | MEDIUM | likely match-critical |
| NAICS | naics_codes | list of codes | optional | source provenance | MEDIUM | should be preserved as source metadata |
| license number | license_number | preserve original string | optional | source provenance | HIGH | state-specific |
| license status | license_status | preserve enum/status | optional | source provenance | MEDIUM | may be dynamic |
| contact phone | phone | normalized string | optional | source provenance | MEDIUM | may be restricted |
| public email | primary_email | normalized email | optional | source provenance | MEDIUM | outreach must be checked against terms |
| source URL | source_url | normalized URL | optional | source provenance | HIGH | preserve attribution |
| fetched_at | fetched_at | UTC ISO timestamp | required for source audit | local capture | HIGH | supports freshness checks |
| verification status | verification_status | preserve enum | optional | source provenance | MEDIUM | not always present |
| historical award evidence | historical_evidence | preserve list or references | optional | source provenance | MEDIUM | used for trust but not required initially |

This contract intentionally avoids adding these fields to the production schema until a real source strategy and validation process justify it.

## 8. Contact data and outreach constraints

### Publicly visible contact data is not the same as permitted automated outreach

The repo must distinguish between:
- publicly visible information
- permitted automated collection and use
- allowed outreach under terms

Examples:
- public company websites may list phone numbers and contact forms
- public business email addresses may exist but require permission to automate use
- procurement contacts may be public but still governed by procurement or source terms
- scraping contact data from protected sites or pages behind access barriers is not allowed as a default design pattern

Engineering constraints:
- no mass scraping
- no CAPTCHA bypass
- no robots.txt bypass
- no authentication bypass
- no paywall bypass
- no secret or credentialed access without explicit approval
- no broad outbound spam or unauthorized outreach automation

ACE should treat contact data as a higher-cost, higher-risk field that requires source-specific policy review before any automation.

## 9. Matching implications

Current supported feature set is intentionally narrow and limited in [docs/MATCHING_FEATURES.md](MATCHING_FEATURES.md).

Future contractor-side fields that would meaningfully help matching include:
- trade specialization
- service area / geography
- NAICS classification
- license / classification category
- project history and historical awards
- activity status / inactive flag
- contractor size and capacity
- public contact availability

### Feature-to-field mapping

| Future matching feature | Project-side field | Contractor-side field | Notes |
| --- | --- | --- | --- |
| trade fit | `project.trades` | `contractor.trades` | supported in current model, but still shallow |
| geography fit | `project.city`, `project.state`, latitude/longitude | `contractor.city`, `contractor.state`, latitude/longitude | supported in current model |
| service area match | `project.city` or `project.region` | `contractor.service_areas` | future field, not currently implemented |
| construction type match | `project.construction_type` | `contractor.specialty` or `contractor.trade_classification` | future field |
| NAICS fit | `project.naics_code` | `contractor.naics_codes` | future field |
| license suitability | `project.license_or_trade_requirements` | `contractor.license_status` / `license_number` | future field |
| historical project evidence | `project.raw_evidence` or `project_history` | `contractor.historical_evidence` | future field |
| capacity fit | `project.estimated_value` | `contractor.value_capacity` | future field, but only if source contract is explicit |
| recency/activity | `project.bid_date` or project activity | `contractor.last_active_date` or status | future field |

This is not a proposed implementation; it is a design note about what would eventually make the matching engine stronger.

## 10. Future contractor discovery pipeline

The recommended architecture is:

SOURCE
→ RAW CONTRACTOR
→ VALIDATION
→ NORMALIZATION
→ DEDUPLICATION
→ ENTITY RESOLUTION
→ ENRICHMENT
→ CANONICAL CONTRACTOR
→ MATCHING

### MVP boundary

MVP / near-term scope:
- raw contractor payload storage
- deterministic validation
- minimal normalization
- source + source_id identity
- deterministic dedupe on source + source_id
- canonical contractor table with current runtime fields only

### Future boundary

Future phases may include:
- entity-resolution pipelines across sources
- public-company records enrichment
- state license validation
- historical award evidence import
- address normalization and service-area modeling
- richer contact handling with explicit permission review

### Provider boundary

External contractor sources must remain behind provider interfaces, just as project/provider sources are isolated today in [src/providers/interfaces.py](../src/providers/interfaces.py).

## 11. Data quality requirements

Future contractor data quality should include:
- source provenance
- fetched_at
- freshness
- verification status
- completeness
- conflicting source values
- stale license status
- inactive businesses
- duplicate entities
- place/address uncertainty

This should not be turned into a fake numerical confidence model without a defined methodology.

A safe design is to preserve qualitative status fields and provenance rather than pretending there is a universal numeric confidence score.

## 12. Security / trust requirements

Contractor data is external and untrusted. Future source handling should include:
- URL validation
- HTML sanitization where values are rendered
- contact data handling rules
- audit log of raw imports and normalized values
- source attribution and legal provenance storage
- rate limiting and backoff for remote sources
- secret storage for API keys and credentials
- source-content safety controls
- prompt injection resistance if future AI is added for outreach or summarization

No implementation is required for this phase.

## 13. Legal / terms boundary

This phase should explicitly document engineering boundaries, not legal conclusions.

### Hard constraints

- Public data does not automatically mean unrestricted automated collection.
- API access does not automatically mean unrestricted commercial use.
- Source terms, licenses, and robots/access controls must be reviewed before automation.
- CAPTCHA, paywalls, authentication walls, or access controls must not be bypassed.
- Commercial databases must be treated as commercial sources with licensing constraints.

This is only an engineering and source-policy boundary, not a legal opinion.

## 14. Recommended source strategy by role

### Primary candidate

- SAM.gov contractor/entity context
- Why: official U.S. federal source with high trust and source identity value; useful for identity and public registration context.

### Supplemental

- USAspending awardee / recipient data
- State contractor license registries
- OpenCorporates
- Why: useful for historical evidence, registration context, local validation, and normalization.

### Enrichment

- OpenCorporates
- State license registries
- Public directory records where access is clearly public and permitted
- Why: these are validation or enrichment sources, not direct discovery feeds.

### Historical evidence

- USAspending award history
- historical public project records where available
- Why: valuable for experience and performance evidence, not necessarily for active contractor prospecting.

### Post-MVP commercial

- ConstructConnect
- Dodge
- PlanHub / Blue Book / similar
- Why: strong commercial contractor data but paid and licensable; not suitable for the current $0 local-first architecture.

## 15. Recommended future architecture

The future architecture should be modular and source-aware:
- keep provider adapters behind interfaces
- persist raw contractor records for auditability
- normalize into a canonical contractor shape only when a verified source contract justifies it
- maintain provenance and source_id strictly
- defer entity resolution and cross-source merging until required by production use
- keep human review and approval logic outside of the raw data ingest path

## 16. Requirements for Phase 11

Phase 11 should not start automatically. It should only begin after the following prerequisites are satisfied:
- a clear, validated public contractor data source is selected
- the source has a documented API/data contract or publicly supported access pattern
- terms/usage constraints are reviewed
- the exact canonical contractor fields are justified by business need
- a fixture-backed provider contract is designed and tested locally
- no paid or credentialed path is required for initial local development

## 17. Conclusion

This phase is a design-only audit and is intentionally not an implementation pass.

The repository’s actual runtime model confirms that ACE currently supports only a narrow contractor contract: names, source identity, city/state, trade list, email, and provenance. The future real contractor-discovery architecture requires a much richer and more carefully governed model, with public-source validation, source identity discipline, contact-data review, and a modular provider contract.

The correct strategy is to keep the runtime narrow, preserve raw external data, and validate a small set of public contractor sources before adding any production schema changes or outreach automation.
