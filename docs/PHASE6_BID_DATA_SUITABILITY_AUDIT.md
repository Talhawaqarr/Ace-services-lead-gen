# Phase 6 — Bid Data Suitability + Source Expansion Audit

## 1. Executive summary

ACE Services needs project and bid data that are actual construction opportunities, not merely federal spending records. The current canonical model and the current Phase 5 USAspending-style provider are useful as a local development foundation, but they are not a sufficient primary source for ACE’s real workflow.

The evidence from the repository is clear:
- the current runtime Project model in [src/models/core.py](src/models/core.py) is intentionally minimal and matching-friendly
- the deterministic matcher in [src/matching/engine.py](src/matching/engine.py) currently supports only trade overlap, geography, and bid timing
- the current Phase 5 provider in [src/providers/usaspending.py](src/providers/usaspending.py) uses fixture-backed rows that resemble public award metadata more than active solicitations
- the repository documentation distinguishes between current runtime models and future aspirational models in [docs/CANONICAL_MODELS.md](docs/CANONICAL_MODELS.md)

The key conclusion is this:

- USAspending-style award records are useful as a supplemental source and as a local $0 fixture
- they are not the same thing as active construction bids or project opportunities that ACE can actually pursue
- ACE’s real product needs active solicitation and project-detail data, with deadlines, scope, status, documents, and pricing context

For the next phase, the best path is not to add more fields to the current minimal model blindly. The best path is to add a better source strategy for active opportunities, while keeping the current canonical model narrow and deterministic.

## 2. ACE opportunity definition

An ideal ACE opportunity record is a project that is both relevant to the company’s estimating work and actionable for contractor outreach. It should support actual business decisions, not just data collection.

### A. REQUIRED fields

The following fields are the minimum needed for ACE to evaluate a project as a real opportunity:

- project name / title
- project description or scope summary
- location: city + state + ZIP where available
- coordinates when available
- construction category / project type
- trade or scope information (e.g., general, electrical, concrete, HVAC, roofing, civil, plumbing)
- bid date or deadline
- project status (planned, soliciting, bidding, awarded, closed)
- source / source_id / source URL
- owner or agency name
- estimated project value or budget range
- whether the opportunity is active, awarded, or closed

These are the fields required for ACE to ask:
- Is this project in my market?
- Is it in the right trade category?
- Is it relevant by timing?
- Is it large enough to matter?
- Is it still open for bidding?

### B. HIGH-VALUE / NICE-TO-HAVE fields

- pre-bid meeting date/time
- solicitation number / project number / award number
- plans/specifications URL
- document presence and document type
- architect / engineer / prime / GC information
- contact names and emails
- project delivery method
- project stage / phase
- estimate type or contract type
- procurement method
- bid bond / prequalification requirements
- public agency and department name
- county / metro area
- project description quality and extraction status

These materially improve matching and human review, especially when ACE needs to prioritize active opportunities and identify likely contractors.

### C. FUTURE ENRICHMENT

- subcontractor lists
- historical award data
- award amounts for similar projects
- owner relationship history
- project timeline / milestone list
- contract documents extracted into searchable text
- geospatial distance to ACE service area
- contractor contact quality scores
- project-risk tags
- historical bid outcomes

These are useful, but they are not required for the first practical opportunity-discovery engine.

## 3. Current canonical Project audit

The actual repository code is the source of truth. The current runtime canonical Project model is defined in [src/models/core.py](src/models/core.py), and the match engine uses those fields in [src/matching/engine.py](src/matching/engine.py).

### Current Project fields in the actual runtime model

| FIELD | CURRENTLY EXISTS? | USED BY | BUSINESS VALUE | REQUIRED / NICE / FUTURE | RECOMMENDATION |
|---|---|---|---|---|---|
| id | Yes | all DB persistence | unique record identity | Required | Keep |
| name | Yes | ingestion, UI, matching | core project identity | Required | Keep |
| source | Yes | deduplication, provenance | data lineage | Required | Keep |
| source_id | Yes | deduplication, provenance | stable source-level identity | Required | Keep |
| city | Yes | matching, review UI | market relevance | Required | Keep |
| state | Yes | matching, review UI | state-level market filtering | Required | Keep |
| latitude | Yes | matching logic (geography) | distance-based matching | Nice | Keep nullable |
| longitude | Yes | matching logic (geography) | distance-based matching | Nice | Keep nullable |
| trades | Yes | matching logic | primary target for scope fit | Required | Keep, but treat as partial/nullable |
| bid_date | Yes | matching logic | timing relevance | Required | Keep, but keep nullable |
| estimated_value | Yes | review and filtering | opportunity size signal | Nice | Keep nullable |
| provenance | Yes | auditing and troubleshooting | raw-source traceability | Required for the current minimal model | Keep |
| description | No | none | useful project narrative | Nice / future | Do not add yet unless a real source provides it at scale |
| project type | No | none | classification of construction type | Nice | Future only |
| ZIP | No | none | geospatial precision | Nice | Future only |
| project status | No | none | active-vs-awarded distinction | Required for real bid workflow | Future required field for the next source strategy |
| project URL / source URL | No | none | document access and validation | Required for real opportunity workflow | Future required field |
| bid status | No | none | active bidding vs award/closed status | Required | Future required field |
| documents / plans URL | No | none | tender package access | Required for actual bid pursuit | Future required field |
| owner / agency | No | none | procurement context and qualification | Nice | Future / perhaps required when source supports it |
| solicitation number | No | none | traceability / procurement identity | Nice | Future |
| architect / engineer / GC | No | none | project stakeholder identification | Nice / future | Future |
| bid time / pre-bid meeting | No | none | schedule precision | Nice | Future |
| project stage | No | none | predictability and urgency | Nice | Future |

### Interpretation

The current model is intentionally optimized for:
- matching deterministically
- review workflow
- source provenance
- basic local development

It is not yet optimized for:
- active bid eligibility
- construction scope certainty
- procurement lifecycle status
- contract documents
- opportunity-quality assessment

### Which fields are currently unused or misleading?

- project name is useful, but not enough on its own for project relevance
- bid_date is present but often not equivalent to an actual submission deadline
- trades is present but may be sparse or incomplete
- estimated_value is useful but often absent or rough in public data
- source and source_id provide clean lineage, but they do not guarantee a good opportunity

### Fields that should remain nullable

- latitude, longitude
- trades
- bid_date
- estimated_value
- project status (future)
- source URL (future)
- source document links (future)

The current repo correctly treats unknown values as unknown, which is essential for a deterministic model. The matcher in [src/matching/engine.py](src/matching/engine.py) already knows how to handle missing values as neutral rather than mismatches.

### Fields that should not be added yet

- speculative natural-language fields that are not currently backed by a legitimate source
- generic project_type values when the source does not actually provide them reliably
- contractor-side enrichment fields before the contractor discovery model is mature
- ML and embedding features in the canonical schema

## 4. Current USAspending-style source audit

### Current Phase 5 source

The current implementation is in [src/providers/usaspending.py](src/providers/usaspending.py) and is backed by [docs/fixtures/phase5_usaspending_projects.json](docs/fixtures/phase5_usaspending_projects.json).

### What the source actually provides

From the repository and public-source docs reviewed: this fixture mirrors a federal-award / spending metadata pattern, not a procurement-bid platform.

Verified facts:
- USAspending is an official federal spending data source for awards, contracts, grants, and related data
- The public docs state the platform provides searchable federal spending data and award-related metadata
- SAM.gov has public contract-opportunity search and data services, with opportunity notices and federal procurement metadata
- The current repository treats the Phase 5 provider as a local fixture-backed source representing a public award-style contract schema

Repository assumptions and current implementation:
- the Phase 5 provider returns project-like records with fields such as title, description, city, state, bid_date, estimated_value, and trades
- these are normalized into the current Project model in [src/ingestion/service.py](src/ingestion/service.py)

### What it does not provide reliably

The current source model does not reliably provide:
- active bid status vs awarded status
- solicitation deadlines
- plans/specifications URL
- bid package documents
- trade-level scope with consistent quality
- project owner / agency context in a contract-bid sense
- pre-bid meeting details
- procurement method
- real-time active bid availability

### Most important distinction: award data vs active opportunity data

This is the central audit issue.

The current source is not automatically equivalent to an active construction bid opportunity. It may contain:
1. active project opportunities, if the public source is an opportunity portal
2. awarded contracts, if the source is post-award data
3. spending records, if the source is award-funded data
4. mixed metadata, if a source is not strictly bid-only

Using the repository evidence and public documentation reviewed:
- USAspending is best understood as award/spending metadata
- SAM.gov contract opportunities is closer to active procurement notices
- the current local provider is closer to a public award-style schema than to an active construction bid room

Therefore, the conclusion is:
- the current source supports development and matching experiments
- it does not ensure the system is ingesting the right kind of business opportunity for ACE without broader source selection

### Verified fact vs repository assumption vs inference

| CATEGORY | SUMMARY |
|---|---|
| Verified fact | USAspending is a public federal spending/award dataset |
| Verified fact | SAM.gov includes public contract opportunity information |
| Repository assumption | the current fixture-backed source is enough for a real bid opportunity workflow |
| Inference | the current fixture-backed source approximates a public opportunity contract more than a live bid-room listing |
| Unknown | whether a real public-source API available to the project is sufficiently rich for ACE’s needs without a commercial source |

## 5. Biggest data gaps

The critical question is what is missing from the current system that most limits ACE’s actual workflow. The biggest gaps are business-critical, not theoretical.

### Gap 1 — Active bid / award distinction

- Why it matters: ACE needs to know whether a project is a live opportunity, an awarded project, or a completed/spending record.
- Current coverage: limited, not explicitly represented in the current canonical Project model
- Impact: high
- Possible data source: SAM.gov contract opportunities, state procurement portals, local agency bid sites

### Gap 2 — Project status and deadlines

- Why it matters: the system cannot prioritize relevant opportunities without bid closure, deadline, and time-to-response context
- Current coverage: bid_date exists, but it is not necessarily the submission deadline or bid status signal
- Impact: high
- Possible data source: government procurement portals, local agency solicitations, public bid notices

### Gap 3 — Scope and trade detail quality

- Why it matters: ACE’s matching engine depends on trade overlap, but real bid scopes are often more detailed than generic metadata
- Current coverage: trades array exists, but it is sparse and often incomplete
- Impact: high
- Possible data source: solicitation descriptions, project specs, NAICS/PSC metadata, plans/specifications data

### Gap 4 — Plans/specifications and document access

- Why it matters: actual estimating work depends on project documents, plans, and specs; outreach also depends on document availability
- Current coverage: none
- Impact: very high
- Possible data source: bid portals, agency solicitations, plan rooms, public project websites

### Gap 5 — Owner / agency / project stakeholder context

- Why it matters: relationship mapping and outreach quality depend on the actual project owner or agency
- Current coverage: none in the canonical model
- Impact: medium-high
- Possible data source: SAM.gov, state procurement portals, public agency project sites

### Gap 6 — Contractor / GC / prime context

- Why it matters: contractor discovery needs to know who is acting as prime or GC when relevant
- Current coverage: not in the canonical Project model
- Impact: high for future contractor discovery
- Possible data source: contractor records, prime/GC listings, public agency project documents

### Gap 7 — Geographic precision beyond city/state

- Why it matters: ACE may need ZIP, county, or geospatial precision for local market segmentation
- Current coverage: city/state/coordinates exist, but not necessarily consistently
- Impact: medium
- Possible data source: agency portal data, geocoding sidecar data, geocoded public records

## 6. Public / free source research

### Source comparison

| SOURCE | SOURCE TYPE | WHAT DATA IT CONTAINS | ACTIVE BIDS OR AWARDS? | CONSTRUCTION RELEVANCE | GEOGRAPHIC COVERAGE | TRADE/SCOPE INFO | DEADLINES | PLANS/DOCUMENTS | CONTRACTOR INFO | ACCESS METHOD | API AVAILABLE? | ACCOUNT REQUIRED? | COST | RATE LIMITS / RESTRICTIONS | AUTOMATION FEASIBILITY | LEGAL / TERMS CONSIDERATIONS | LIKELY VALUE TO ACE | CONFIDENCE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SAM.gov Contract Opportunities | government procurement portal | opportunity notices, solicitations, notices | Active bids / opportunities | High | U.S. federal | Often via agency/NAICS/text | Usually yes | Sometimes | Limited / indirect | Public portal and data services | Yes, official data services are referenced | Some features may require public account or service access | Free | Public service restrictions and rate limits may apply | Moderate | Public government data; verify official terms and access policies | High | High |
| USAspending | government spending/award source | spending, award, recipient metadata | Awards / post-award | Medium | U.S. federal | sometimes via NAICS/PSC, but not always direct construction scope | Usually award date, not bid deadline | Usually no | Recipient data exists | Public API and website | Yes | Usually no mandatory key for public usage, but verify current docs | Free | Public API constraints and rate limits apply | Moderate | Public government data with official terms | Medium | High |
| State procurement portals | government bid portals | state and local solicitations | Active bids / solicitations | High | State-specific | Varies widely | Often yes | Often yes | Sometimes | Public portal or feed | Sometimes | Sometimes | Usually free | portal/data policy varies by state | Moderate | Check each state’s terms and robots/access policy | High | Medium |
| Local government bid portals | public procurement portals | city/county bids and projects | Active bids / opportunities | High | Local / county / city | Varies | Usually yes | Often yes | Sometimes | Public portal or data feed | Sometimes | Sometimes | Usually free | check site policies | Moderate | Must obey site terms and auth rules | High | Medium |
| ConstructConnect | commercial project database | project leads, specs, plans, contacts | Active bids / opportunities | Very high | Broad U.S. construction market | Very strong | Yes | Usually yes | Yes | commercial API/data feed | Yes, but behind paid access | Yes, paid | Paid | Licensing restrictions | High | Involves commercial licensing and cost | Very high | High |
| Dodge Construction Network | commercial data platform | project leads, bids, specs, contacts | Active bids / opportunities | Very high | Broad U.S. market | High | Yes | Often yes | Yes | commercial feed/API | Yes, but paid | Yes | Paid | Licensing restrictions | High | Commercial contract required | Very high | High |
| PlanHub / Blue Book / similar | commercial bid networks | bid opportunities, plans, trade data | Active bids / opportunities | High | Regional / national | Often high | Yes | Usually yes | Sometimes | commercial product or feed | Depends on provider | Yes | Paid | commercial access | High | Commercial terms required | High | High |

### Source access constraints and legal caution

The project must remain within the no-paid/no-credentials/no-bypass requirement during Phase 6. That means:
- no scraping prohibited sites
- no bypassing paywalls or logins
- no using credentials that are not legitimately available
- no assuming a public portal has an API when the public docs do not say so

For the current purposes of the audit, the strongest free/public options are:
- SAM.gov contract opportunities
- state and local procurement portals with public access
- USAspending as a supplemental market signal rather than the primary opportunity source

## 7. Source strategy recommendation

### Recommended outcome

Recommended outcome: Keep USAspending as a supplemental source and do not treat it as the primary ACE opportunity source.

### Rationale

The evidence supports the following:
- USAspending is a strong public-source dataset for federal award/spending metadata
- it is not the same as active bids or opportunity pipeline data
- ACE’s target use case is active construction opportunities with meaningful scope, schedule, and document visibility
- the current canonical model does not yet represent active bid lifecycle information in a way that makes it a good primary source for ACE’s workflow

### Decision by option

A. Keep USAspending as the primary source
- Not recommended

B. Keep USAspending as a supplemental source
- Recommended

C. Replace it as the primary opportunity source
- Recommended direction, but only once a verified public source with active opportunity data is chosen

D. Use multiple source adapters
- Yes, eventually; but only after the source inventory is verified and constrained to legitimate public sources

E. Keep the current provider only as a development fixture
- This is the safest current recommendation for the repository’s $0 local-first architecture

## 8. Whether the canonical Project should change

The core question is whether the current model is sufficient before the next source expansion. The answer is: it is sufficient for the current small deterministic match engine, but not sufficient for a real ACE opportunity pipeline.

### Minimum required changes, if any

The next phase should only add fields that are directly justified by real active-opportunity sources and the business workflow. The minimum set to consider is:

| FIELD | WHY NEEDED | SOURCE | WHO USES IT | NULLABLE? | CURRENT PHASE OR FUTURE? | WHY IT SHOULD EXIST NOW |
|---|---|---|---|---|---|---|
| project_status | distinguishes live vs awarded vs closed | procurement source | review and prioritization | Yes | Future, but likely next required field | without this, the system cannot distinguish active opportunities from historical awards |
| bid_status | distinguishes bid open / closed / awarded | procurement source | human review and prioritization | Yes | Future, but needed soon | distinguishes opportunity from award history |
| project_url / source_url | provides source traceability | public opportunity source | verification and human review | Yes | Future / near-term required | needed for validation and follow-up |
| plans_url / documents_url | actual project package access | public bid source | estimating and qualification | Yes | Future / near-term required | matches core ACE work |
| solicitation_number / project_number | stable procurement identity | public bid source | traceability and dedupe | Yes | Future | reduces ambiguity across portals |
| owner_or_agency | procurement context | public bid source | review and outreach qualification | Yes | Future | critical for project context |
| project_description | project narrative | source text | scope understanding | Yes | Future / next-phase relevant | necessary for scope-quality and human review |
| project_type | classification | source taxonomy | filtering and matching | Yes | Future | useful when source provides it reliably |
| zip | market precision | source location data | local-market segmentation | Yes | Future | valuable for local opportunity targeting |

### What should not change yet

- Do not broaden the canonical model with speculative contractor fields before source strategy is selected
- Do not add ML/embeddings/LLM schema fields for this decision phase
- Do not add commercial-source-specific fields before a verified provider contract exists

## 9. Matching implications

The current deterministic matcher in [src/matching/engine.py](src/matching/engine.py) uses only:
- trade overlap
- geography
- bid timing

Those are still valid for a minimal, deterministic engine. However, they become much more useful when project data is genuinely active and opportunity-quality.

### Which new fields would help deterministic matching?

- project_status: only if active bids are correctly distinguished from awards
- trade/scope quality: better than generic project category
- bid_date / bid_deadline: better timing logic
- ZIP/county/coarse geography: better local targeting
- project_type: better classification when the source provides it reliably

### Which require contractor-side fields that don't exist yet?

- contractor specialty fit
- trade relevance by contractor service area
- actual exposure to project type and region
- contractor contact data for follow-up

These are future contractor-discovery concerns, not immediate Phase 6 implementation.

### What should remain future?

- ML rankers
- embeddings
- LLM classification
- semantic text matching for bid descriptions

The repository is already correctly conservative here, and the audit should keep that boundary intact.

## 10. Impact on future contractor discovery

The eventual ACE workflow requires:

PROJECT → relevant contractors → matching → review → outreach

For contractor discovery to be effective, the project record needs enough information to identify the right people and the right market.

### Currently available

- location (city/state)
- trades (partial)
- bid_date
- estimated_value
- source metadata

### Missing

- degree of project scope detail
- project status / active opportunity state
- documents and plans access
- project number / solicitation number
- owner / agency / GC / prime context
- direct bid date or deadline
- schedule and tender requirements
- project descriptions with enough detail for segmentation

### Future enrichment

- public contractor directories and license registries
- public GC / prime / subcontractor listings
- geospatial service-area matchers
- opportunity-document extraction
- project similarity over time

## 11. $0 development plan

The next step under the project constraints should be narrow and deliberate.

### Build now (still within $0)

- keep the current deterministic matcher unchanged
- keep the current local fixture-backed ingestion architecture
- document the distinction between opportunity data and award data
- add a better source selection decision artifact for Phase 7
- maintain a local fixture that represents a realistic public bid/opportunity source shape, not an award-only record
- add internal docs that clearly mark the gap between procurement notices and award records

### Wait until credentials / contracts / official access are available

- a verified active-bid source with real deadlines and documents
- official procurement portals with reliable solicitation IDs
- project status lifecycle fields from a true bid source
- contractor discovery from public or licensed sources
- real document text extraction and scope parsing
- any integration that requires API keys, commercial license, or public-account verification

### Important guardrail

The project should not assume that the Phase 5 provider is an opportunity source just because it can be connected to the ingest pipeline. The pipeline is real and useful, but the source must still match the business purpose.

## 12. Explicit Phase 7 prerequisites

Before implementing Phase 7, the team should verify:

1. the target source is an actual opportunity or solicitation source, not just award metadata
2. the source provides bid deadlines, project status, and scope details with enough quality to matter
3. the source can be integrated without paid access in local development
4. source-level identity remains stable enough for idempotent ingestion
5. the project fields required for human review are actually present and usable

## 13. Open questions / unknowns

- Which public bid source is the strongest actual fit for ACE without paid access?
- Is a state and local bid portal more important than federal opportunity data for the initial market?
- Does ACE need a true public-opportunity source or can it operate with a broader procurement signal source while it validates contractor discovery?
- Which regions are most important to ACE’s first customers?
- Can the required project documents be obtained from a public source without violating site terms?

## 14. Decision conclusion

ACE should not treat the current USAspending-style source as proof that the system is ingesting true construction bid opportunities. It is a valuable local and supplemental data source, but it is not a sufficient primary source for the business workflow.

The next phase should focus on identifying and validating a real opportunity source—preferably a public procurement source with clearer opportunity lifecycle, deadlines, and scope information—before broadening the canonical model or the matching engine.
