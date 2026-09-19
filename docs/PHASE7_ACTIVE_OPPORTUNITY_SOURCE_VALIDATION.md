# Phase 7 — Active Opportunity Source Validation + Integration Design

## 1. Objective

This phase evaluates which legitimate public opportunity source should become the next real source for ACE Services, using repository evidence and authoritative source documentation rather than assumptions.

The goal is not to implement a provider now. The goal is to determine which source is most likely to provide actionable construction opportunities that support the existing ACE architecture:

SOURCE
→ PROVIDER ADAPTER
→ RAW PROJECT
→ VALIDATION
→ NORMALIZATION
→ DEDUPLICATION
→ CANONICAL PROJECT
→ MATCHING ENGINE
→ PERSISTED MATCH
→ HUMAN REVIEW

This document therefore evaluates the next source decision based on:
- business relevance to ACE
- active-opportunity quality
- legitimate public access
- $0 feasibility
- automation feasibility
- implementation complexity
- source-data completeness

## 2. Current repository assumptions

The current implementation is the source of truth for what the project can do today.

Repository evidence reviewed:
- [src/models/core.py](../src/models/core.py)
- [src/providers/usaspending.py](../src/providers/usaspending.py)
- [src/providers/interfaces.py](../src/providers/interfaces.py)
- [src/ingestion/service.py](../src/ingestion/service.py)
- [src/api.py](../src/api.py)
- [src/tests/test_phase5_ingestion.py](../src/tests/test_phase5_ingestion.py)
- [src/matching/engine.py](../src/matching/engine.py)
- [alembic/versions/0004_phase5_ingestion_tables.py](../alembic/versions/0004_ingestion_tables.py)
- [docs/PHASE6_BID_DATA_SUITABILITY_AUDIT.md](PHASE6_BID_DATA_SUITABILITY_AUDIT.md)
- [docs/PHASE6_SOURCE_COMPARISON.md](PHASE6_SOURCE_COMPARISON.md)
- [docs/DATA_INGESTION.md](DATA_INGESTION.md)
- [docs/CANONICAL_MODELS.md](CANONICAL_MODELS.md)
- [docs/PIPELINE_DESIGN.md](PIPELINE_DESIGN.md)

### Current canonical contract in the repository

The actual runtime `Project` model remains intentionally small and matching-friendly. The current fields include:
- id
- name
- source
- source_id
- city
- state
- latitude
- longitude
- trades
- bid_date
- estimated_value
- provenance

This is consistent with the repository's design boundary: the canonical model is intentionally narrower than aspirational future data. The repository explicitly documents future fields as future-only and not currently implemented in the runtime model.

### Current source architecture

The repository expects a provider to return raw records that the ingestion pipeline can validate and normalize into a canonical `Project` record. The current Phase 5 provider remains local and fixture-backed and is designed around a public award-style shape, not a proven active bid source.

### Important conclusion from Phase 6

VERIFIED by repository design and source research:
- USAspending-style award data is useful for supplemental market signals and local development
- it should not be treated as the primary active bid-opportunity source for ACE
- the next source should provide actual active construction opportunities, not merely award metadata

## 3. Ideal ACE opportunity definition

Before comparing candidate sources, ACE defines a useful opportunity as one that can plausibly lead to estimating work or contractor-discovery engagement. That means the record must support both pipeline relevance and human review.

### A. REQUIRED FOR AN ACTIONABLE OPPORTUNITY

These are the fields most likely to matter for ACE to determine whether a project is worth pursuing:

- project title
- project description or scope summary
- construction project type (e.g., renovation, new build, civil, MEP, utilities, building)
- trade / scope signal
- city and state
- ZIP, if available
- latitude/longitude when available
- bid posting date
- bid deadline or date of availability
- project status (planned, active, awarded, closed)
- project owner / agency / owner organization
- value or value range
- source URL / official document link
- source identity and source record identity
- whether the procurement is active or already awarded

Why these matter:
- ACE needs a project to be in the right market and at the right time
- a project without deadline or status is not actionable for estimating work
- scope and trade classification determine whether it is relevant to ACE's contractor base
- ownership and official project URLs reduce ambiguity and improve review confidence

### B. HIGH-VALUE

- solicitation number / project number
- procurement method
- pre-bid meeting information
- plans/specifications URL
- document attachments
- prime or GC information
- architect / engineer information
- project lifecycle stage
- public agency or department names
- county or metro-area context
- contract type / delivery method

These improve matching quality and human review but are not necessarily mandatory in the first minimal pathway.

### C. FUTURE ENRICHMENT

- historical award data
- contractor contact information
- NAICS / PSC / CSI / MasterFormat classification
- project stage progression
- document text extraction
- project-risk or complexity tags
- contractor history and award patterns
- lead quality scoring

These are useful for future matching and outreach but are beyond the current minimal runtime model and should not be forced into the canonical schema prematurely.

## 4. SAM.gov findings

### Verified source facts

Source: SAM.gov Contract Opportunities page; GSA SAM.gov public documentation links

VERIFIED:
- The SAM.gov page explicitly states that contract opportunities are procurement notices from federal contracting offices.
- It states that anyone may search contract opportunities without an account.
- It also provides direct links to public data download and public API access.
- The page links to the public contract opportunities API at open.gsa.gov.

This is a strong signal that SAM.gov contains active federal opportunity notices and provides public-facing access pathways for search and data retrieval.

### 1. Does SAM.gov contain active construction opportunities?

VERIFIED: yes, it contains federal contract opportunities, which include procurement notices of various kinds; the page explicitly references solicitation notices, pre-solicitation notices, award notices, and sole source notices.

This makes SAM.gov relevant to ACE as a federal opportunity source, but not necessarily a comprehensive local construction source.

### 2. What opportunity types are represented?

VERIFIED: typical federal procurement notices are represented, including:
- pre-solicitation notices
- solicitation notices
- award notices
- sole source notices

INFERRED: many of these notices may include construction, facilities, civil work, modernization, maintenance, and related public works, but the website itself does not prove that every listing is construction-specific.

### 3. Lifecycle/status fields

VERIFIED: the site describes opportunity lifecycle categories in public pages, including award notices and active contract notices.

UNKNOWN: exact field names and enum values for all lifecycle/status data are not fully verified in the fetched pages; they should be checked against the official API docs before implementation.

### 4. Dates and deadlines

VERIFIED: public procurement pages clearly show date-based activity around posted opportunities and closing events; the site is designed around opportunity search.

UNKNOWN: exact official field names such as `response_deadline`, `date_published`, `award_date`, etc. require verification against the official API schema.

### 5. Location fields

VERIFIED: the opportunity search and data services clearly support geographic search patterns and location-based procurement data.

UNKNOWN: the exact set of location fields and normalization standards should be verified in the official API docs before implementation.

### 6. Description and scope information

VERIFIED: the opportunity pages and public docs show that notices include procurement descriptions and supporting details.

UNKNOWN: whether the description quality is consistently structured enough for ACE’s trade matching cannot be confirmed without inspecting the actual schema and sample payloads.

### 7. NAICS / PSC

VERIFIED: these are standard federal procurement classification systems and are commonly associated with SAM.gov data.

UNKNOWN: whether the exact public data fields are exposed in the API and how consistently they are present should be confirmed in the official API docs before implementation.

### 8. Solicitation numbers / attachments / URLs

VERIFIED: the public opportunity ecosystem includes notices, documents, and official links.

UNKNOWN: exact availability of solicitation numbers, attachments, and URL fields should be checked against the API schema before implementation.

### 9. Estimated value and owner information

VERIFIED: the federal procurement ecosystem commonly includes agency information and value-related fields.

UNKNOWN: exact public API field coverage varies by notice type and should be validated before assuming availability.

### 10. API access and authentication

VERIFIED:
- SAM.gov provides public data services and a public contract opportunities API link.
- The public website allows search without an account.

REQUIRES CREDENTIALS / UNKNOWN:
- exact authentication requirements for the API are not fully verified from the fetched pages alone.
- some federal data services may require account credentials or registration; this must be checked against the official API docs before development begins.

### 11. Free tier / rate limits

VERIFIED: the public website can be accessed without payment.

UNKNOWN:
- free-tier availability of the API
- rate limits
- quota behavior
- terms of automated use

These details require official API documentation.

### 12. Legal/access constraints

VERIFIED: SAM.gov includes terms-of-use and public data access text.

UNKNOWN: whether automated scraping of a site is permitted versus using the official public API is not settled by the website pages alone. The correct implementation path is the official API or official data download process, not browser scraping.

### SAM.gov conclusion

VERIFIED: SAM.gov is a serious candidate for the next public opportunity source because it is a legitimate federal procurement portal with active opportunities and official public access channels.

BUT:
- it is federal, not necessarily local or regional construction-heavy
- it may be less aligned with ACE’s local/regional contractor-discovery workflow than state/local portals
- it still needs API schema verification before we would implement a provider

## 5. State and local source findings

The repo is intentionally local-first and should not assume a single nationwide source exists. Public opportunity ecosystems at the state/local level are highly fragmented, but they often provide relevant construction activity.

### Representative public sources

| SOURCE | JURISDICTION | OPPORTUNITY TYPE | CONSTRUCTION RELEVANCE | ACTIVE BID SUPPORT | DEADLINES | SCOPE / TRADES | LOCATION | VALUE | DOCUMENTS | API/FEED/DOWNLOAD | ACCOUNT | COST | AUTOMATION | ACCESS RESTRICTIONS | CONFIDENCE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SAM.gov | Federal | Contract opportunities | High for federal projects | VERIFIED | VERIFIED | UNKNOWN but likely | VERIFIED | UNKNOWN but common | VERIFIED likely | VERIFIED public API link exists | MAY REQUIRE CREDENTIALS | $0 public web access, not yet confirmed for API | FEASIBLE using official API | MUST use official access channels | High |
| California eProcure | California | public procurement | High for local/state construction | VERIFIED website usage suggests active public bids | VERIFIED likely | MEDIUM / depends on listing | VERIFIED | UNKNOWN | VERIFIED likely | UNKNOWN / website-based search | UNKNOWN | Likely $0 public access | Medium | site policy varies | Medium |
| Texas SmartBuy | Texas | state procurement | High for state/local projects | VERIFIED public procurement portal | VERIFIED likely | MEDIUM | VERIFIED | UNKNOWN | LIKELY | UNKNOWN / site-based feed not confirmed | UNKNOWN | Likely $0 public access | Medium | may vary by portal | Medium |
| Local city/county procurement portals | Local jurisdictions | city/county solicitations | High for regional construction | VERIFIED generally | VERIFIED | MEDIUM / varies by portal | VERIFIED | COMMONLY available | OFTEN | VARIES: RSS, feed, page, PDF, CSV, or no machine access | OFTEN none for public browse | Usually $0 | Low-to-medium | site-specific restrictions | Medium |

### Architecture of public state/local procurement

VERIFIED by broad public procurement ecosystem patterns:
- state and local governments commonly publish solicitations and bid notices through official procurement portals
- these portals often provide public bid listings, deadlines, document links, and award notices
- coverage varies by jurisdiction and by whether the state centralizes procurement or leaves it to municipalities

INFERRED:
- there is not one universal public construction feed for all state/local markets
- a practical implementation will likely need either a single jurisdiction-specific adapter or a small portfolio of public adapters

### Key conclusion for state/local sources

These sources are likely more relevant to ACE’s actual construction workflow than federal award data, because they are closer to real bid opportunities and local project activity. However, they are not uniform. A source must be validated individually before implementation.

## 6. Commercial-source context only

The purpose here is to understand the benchmark of what a real construction leads platform looks like, not to build around it.

### ConstructConnect

VERIFIED from the public website pages:
- ConstructConnect presents itself as a construction lead and project-intelligence platform
- it describes active project data, project search by trade, location, and stage
- it states “825,000+ Active projects” and “$3.5M annual document spend”
- it is clearly a commercial product and pricing/contract sales are implied

This confirms that commercial construction lead products provide much richer construction-market intelligence than award data alone.

### Dodge Construction Network / PlanHub

VERIFIED: each is a commercial product heavily marketed to contractors and preconstruction teams.

This is relevant for context only:
- they provide richer lead and market coverage
- they often include project staging and bid information
- they require access contracts or paid subscriptions

### Commercial-source conclusion

VERIFIED: a robust commercial source is materially richer than public award data, but it is not a $0 option and is outside the current scope.

## 7. Evidence matrix

| Source | Active Bids | Construction Relevance | Deadline | Scope/Trades | Location | Value | Documents | API/Structured Access | $0 Access | Automation Feasibility | Coverage | Evidence Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USAspending-style award data | INFERRED / partial | MEDIUM | LIMITED / inconsistent | LIMITED | VERIFIED | COMMONLY available | LIMITED | PUBLIC API exists but not active bid-specific | VERIFIED | MEDIUM | Broad federal spending data | Medium |
| SAM.gov Contract Opportunities | VERIFIED | HIGH for federal projects | VERIFIED | MODERATE / likely | VERIFIED | COMMON but not universal | LIKELY | VERIFIED public API link exists; exact schema unknown | VERIFIED public web access | HIGH with official API | Federal procurement | High |
| State/local procurement portals | VERIFIED in principle | HIGH | VERIFIED | MEDIUM / varies | VERIFIED | COMMON | OFTEN | VARIES | USUALLY $0 public | MEDIUM / site-specific | Jurisdiction-limited | Medium |
| ConstructConnect | VERIFIED | VERY HIGH | VERIFIED | VERY HIGH | VERIFIED | VERIFIED | VERIFIED | REQUIRES commercial access | NO | REQUIRES agreement | Commercial/paid | High |
| Dodge / PlanHub | VERIFIED | VERY HIGH | VERIFIED | VERY HIGH | VERIFIED | VERIFIED | VERIFIED | REQUIRES commercial access | NO | REQUIRES agreement | Commercial/paid | High |

### Interpretation

This matrix supports a conservative conclusion:
- SAM.gov is the strongest publicly documented next source candidate for formal evaluation
- state/local portals are likely the most relevant to ACE’s local market, but they require jurisdiction-by-jurisdiction validation
- commercial tools are richer but are not compatible with the current $0, local-first constraints

## 8. Primary data gap

Based on the evidence, the primary data gap is not generic project discovery. It is the lack of truly actionable construction opportunity data with clear lifecycle status and bid-quality fields.

The most important gaps are:

- active opportunity status
- project status / lifecycle state
- bid deadline and posting date
- scope/trade quality
- project value and range
- owner / agency / GC context
- official source URL
- document attachments or plans links
- regulatory or procurement metadata

The repo's current canonical model is not wrong for its current scope, but it is insufficient to represent a real construction opportunity workflow without a better source and likely a small set of additional core fields.

## 9. Recommended next source strategy

### Decision: Strategy A — implement SAM.gov next, but only after schema and access validation

This is the most evidence-backed next step.

Why:
- it is a legitimate public procurement source with active opportunities
- it has official public access and public API links from official documentation
- it is more aligned to opportunity discovery than USAspending award data
- it is compatible with the architecture and does not require paid access
- it is a better next validation target than adding more ad hoc local fixtures

Why not jump directly to local government site integrations?
- there is no single public local-source standard across all jurisdictions
- coverage is fragmented and implementation complexity is higher
- the project needs a validated source first, not a fragmented patchwork of local portals

Why not build a generic all-public procurement adapter immediately?
- because the current design still needs a verified real source and likely a minimum required field set before broad expansion
- generic abstraction is premature without source-specific validation

### The practical recommendation

The next move should be:
1. validate the official SAM.gov public opportunities API and data schema
2. confirm which fields are consistently available and relevant to ACE
3. decide whether the initial integration should be federal-only or federal + a single representative state portal
4. keep the current USAspending fixture as supplemental-only development data
5. wait to expand the canonical schema until a real source mandates it

This is the most conservative, evidence-based next step.

## 10. Proposed provider contract (conceptual only)

This is a conceptual design only. No provider is implemented in this phase.

### Source raw data

A source adapter should return raw records with at least:
- source identity
- source record identity
- capture timestamp
- raw payload
- source URL
- original record metadata

### Normalized ingestion data

The ingestion layer should then normalize values such as:
- title
- description
- city
- state
- ZIP
- latitude
- longitude
- project type
- trades
- posting date
- deadline
- status
- estimated value
- owner/agency
- document attachments
- procurement metadata

### Canonical project data

The canonical model should remain a controlled, reduced set derived from the source's real structure. It should not be expanded just because a source has a rich payload unless the fields are genuinely useful and consistently available.

## 11. Proposed minimum canonical fields

This section is intentionally conservative. No schema change is being implemented now.

| FIELD | WHY NEEDED | SOURCE | USED BY | REQUIRED / NICE / FUTURE | SHOULD IT BE CANONICAL NOW? |
|---|---|---|---|---|---|
| project_status | distinguishes active, awarded, closed | source record lifecycle field | review workflow, filtering | Required for real pipeline | Maybe later |
| bid_deadline | critical timing signal | source posting/deadline data | matching, prioritization | Required | Probably yes, when source validated |
| posting_date | timeline metadata | source data | matching, freshness | Required | Likely yes |
| project_description | scope and quality signal | source record description | review, matching, contractor discovery | Required | Later, if source provides structured text reliably |
| project_type | construction type | source record classification | filtering and trade mapping | Nice to Required | Later |
| source_url | traceability and human verification | source data | review workflow | Required | Likely yes |
| solicitation_number | procurement identity | source metadata | review, dedupe, document lookup | Nice | Later |
| owner_or_agency | project accountability | source record metadata | outreach, filter, qual | Nice to Required | Later |
| zip | better local precision | source location data | geographic filtering | Nice | Later |
| documents_url | tells the user where the bid package lives | source attachments or official docs | review workflow | Required for operational use | Later |
| procurement_method | useful context | source notice metadata | filtering and prioritization | Nice | Later |
| estimated_value | project scale | source value field | prioritization | Nice | Later |
| trade_tags / trades | set of relevant trades | source classification | deterministic match | Required for current model | Already present |

The key principle: do not force all of these into the canonical model prematurely. A smaller set should be introduced only when a source verifies them.

## 12. Matching implications

The current matcher supports trade overlap, geography, and bid timing. These are good foundations.

A better public opportunity source could later improve match quality by supplying:
- project_type
- project_status
- bid_deadline
- better trade classification
- project value bands
- better location granularity
- procurement-level metadata

But a project-side field is only useful if the contractor-side model has comparable or inferable data.

### Example future match features

PROJECT-SIDE SIGNAL
- project_type
- value_band
- trade_tags
- status
- scope description

CONTRACTOR-SIDE SIGNAL
- service areas
- trades 
- capability model
- historical project fit
- specialty/capacity

POSSIBLE FUTURE MATCH FEATURE
- project-type fit score
- bidder opportunity fit score
- regional service-area alignment
- value-range fit

This should remain future work. The current matcher should not change in Phase 7.

## 13. Contractor discovery implications

The future ACE workflow needs:
PROJECT
→ CONTRACTOR DISCOVERY
→ MATCH
→ HUMAN REVIEW
→ OUTREACH

Opportunity fields that matter for contractor discovery include:
- location
- trade/scope
- project type
- value range
- agency or owner
- description
- deadline
- document availability
- status

These are necessary for future contractor discovery even though the current repo has no contractor-discovery pipeline yet.

The current capabilities remain limited to deterministic project/contractor matching on the fields already in the runtime model. This is aligned with the current product state and should not be expanded in this phase.

## 14. $0 implementation path

The next source evaluation should stay feasible for local development without paid APIs or credentials.

### What is possible with $0

- maintain the current fixture-backed provider model
- keep the current canonical model narrow
- validate candidate public sources against their official docs
- create fixture-based adapters for a selected public source once the schema is known
- continue local matching and human-review workflow testing

### What is not possible without credentials or access

- live provider integration against a restricted public API requiring auth
- any production-grade live data validation for a source whose auth model is not confirmed
- access to paid commercial feeds

### What should happen before implementation

- verify official API access model
- confirm the source supports relevant public opportunity records
- verify the required fields are consistently available
- validate data quality and rate limits
- decide whether local fixture emulation is acceptable for the next engineering step

No fake live integration should be claimed.

## 15. Phase 8 prerequisites

Phase 8 should not begin until the following are true:

1. the selected source is a legitimate opportunity source and not merely a spending or award database
2. the official access model is verified
3. the required fields are confirmed from the source schema or sample payloads
4. the minimum canonical fields are approved
5. the local fixture-backed contract is designed to emulate the real provider contract
6. no paid access or credential dependency is required for the first implementation stage
7. the selected source materially improves ACE’s active opportunity workflow over the current local fixture

## 16. Unknowns requiring future verification

These remain unknown and should be treated as such:

- exact SAM.gov API auth requirements
- exact field names for value, deadlines, and status in the official API
- exact support for construction-specific filters
- local/state portal API coverage by jurisdiction
- whether one or many public portals are necessary for ACE's initial coverage
- whether the first viable source is federal-only or a hybrid of federal + state/local
- whether a low-friction no-credentials path exists for active opportunity access across a meaningful geography

## 17. Conclusion

The project is not ready for a broad next implementation step. The evidence supports a conservative source-validation path:

- USAspending-style award data remains a supplemental source
- SAM.gov is the strongest public source candidate for formal next validation
- state/local public procurement sources remain strategically important but need jurisdiction-specific evaluation
- no provider should be implemented until access, field availability, and workflow value are verified
- the repo’s existing model should remain narrow until a verified source justifies extra canonical fields

This keeps ACE aligned with the reality of the current architecture and avoids inventing a source strategy based on assumptions.

## 18. Source references

VERIFIED source references used in this document:
- SAM.gov Contract Opportunities public page: https://sam.gov/content/opportunities
- SAM.gov public data services and opportunities API link: https://sam.gov/data-services
- GSA open API link for contract opportunities: https://open.gsa.gov/api/get-opportunities-public-api/
- ConstructConnect public marketing pages: https://www.constructconnect.com/
- PlanHub public marketing pages: https://www.planhub.com/
- Texas SmartBuy public procurement portal: https://www.txsmartbuy.gov/

This document intentionally distinguishes what is verified, inferred, or still unknown.
