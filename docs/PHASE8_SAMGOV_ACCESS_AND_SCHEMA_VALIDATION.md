# Phase 8 — SAM.gov Access + Schema Validation

## 1. Objective

This phase validates the official SAM.gov Contract Opportunities API and data model enough to determine whether the ACE project can safely design a fixture-backed integration contract before writing production code.

The purpose is not to implement the provider. The purpose is to remove uncertainty around:
- official API access
- authentication requirements
- data field availability
- lifecycle/status semantics
- dates and deadlines
- location and value structures
- document availability
- the realistic $0 fixture-first path

## 2. Repository integration contract

The current repository expects providers to return raw source records that the ingestion layer validates, normalizes, deduplicates, and then persists into the existing canonical `Project` model.

Relevant repository files reviewed:
- [src/providers/interfaces.py](../src/providers/interfaces.py)
- [src/providers/usaspending.py](../src/providers/usaspending.py)
- [src/ingestion/service.py](../src/ingestion/service.py)
- [src/models/core.py](../src/models/core.py)
- [src/tests/test_phase5_ingestion.py](../src/tests/test_phase5_ingestion.py)
- [docs/PHASE7_ACTIVE_OPPORTUNITY_SOURCE_VALIDATION.md](PHASE7_ACTIVE_OPPORTUNITY_SOURCE_VALIDATION.md)

The current runtime `Project` model is intentionally minimal and includes:
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

This matters because the next provider must be able to map into that contract without redesigning the architecture. A raw SAM.gov payload may contain richer fields, but the canonical model remains narrower unless a verified future schema change is justified.

## 3. Official SAM.gov access findings

### Verified facts

Official source: SAM.gov Contract Opportunities page and official public API documentation at `https://open.gsa.gov/api/get-opportunities-public-api/`

VERIFIED:
- The official API name is the SAM.gov Get Opportunities Public API.
- The API endpoint is `https://api.sam.gov/opportunities/v2/search` in production.
- The alpha environment is `https://api-alpha.sam.gov/opportunities/v2/search`.
- The API requires an `api_key` parameter.
- A user must request a public API key from their SAM.gov account details page.
- The page says this API is for the newest active version of the opportunity, and older versions are available via Data Services.
- The API supports pagination and requires a date range (`postedFrom`, `postedTo`) and it enforces a one-year maximum range.
- There are public download/data-services pathways in addition to the API.

This means the official contract is real and is not a random blog claim. It is a GSA-hosted API with documented request and response parameters.

### Important distinction

VERIFIED:
- Public browsing/search on SAM.gov is available without payment.
- Official API usage is not the same as anonymous public web browsing.
- The public API is access-controlled via API key, not open unauthenticated access.

This is the crucial business fact for ACE: public discovery is not the same as free automated API access with no account or credential.

## 4. Authentication findings

### Verified findings

Official documentation states:
- A public API key is required.
- A user may request a public API key from the Account Details page on SAM.gov.
- The user must enter the account password to view the API key information.
- The key is visible until the user navigates away from that page.
- If the API key is invalid, the API returns an invalid `api_key` error.

Classification:
- API key required: VERIFIED
- Account required: VERIFIED
- Free access: VERIFIED for public web browsing; API access is not described as a no-account free endpoint in the official API docs.
- Credential acquisition path: VERIFIED via SAM.gov account details

Important implication:
- A live SAM.gov provider is not a true no-credentials design in the current repo.
- A fixture-backed provider is still a valid local-$0 design.
- A live provider would require actual credential handling and secure storage later.

## 5. API/access constraints

### Verified from official docs

VERIFIED:
- `api_key` is required in the request.
- `postedFrom` and `postedTo` are mandatory for search requests.
- `limit` is valid between 0 and 1000.
- `offset` supports pagination.
- Response errors include invalid API key, missing API key, invalid dates, and date-range validation.
- Data returns on the web are available through public data services and the API.

UNKNOWN / REQUIRES FURTHER VERIFICATION:
- exact rate limits by role type
- exact quota behavior per account and per day
- whether the public API key is always free or tied to a specific account model
- whether production and alpha environments differ for key issuance and permissions

The official docs explicitly say request/day limits vary by federal or non-federal or general roles, but the exact numeric values are not fully visible in the excerpt we retrieved.

## 6. Opportunity data model

Official docs for the public API include a long response parameter list. The following are clearly documented as fields returned by search responses:

### Identity and control fields
- `title`
- `solicitationNumber`
- `noticeid` (request field)
- `type`
- `baseType`
- `archiveType`
- `archiveDate`
- `active`
- `links`
- `resourceLinks`
- `uiLink`
- `fullParentPathName`
- `fullParentPathCode`
- `organizationType`
- `department`
- `subtier`
- `office`

### Date fields
- `postedDate`
- `reponseDeadLine` (documented as `reponseDeadLine`; likely response deadline field)
- `archiveDate`
- `data.award.date` when award data exists

### Status fields
- `active`
- `type`
- `baseType`
- `archiveType`
- `status` request field accepts `active`, `inactive`, `archived`, `cancelled`, `deleted`

### Description and documents
- `description` (a link; requires API key to access; returns “Description Not Found” when not available)
- `resourceLinks` (direct URL to download attachments)
- `additionalInfoLink`
- `uiLink`
- `data.pointOfContact.additionalInfo`

### Classification fields
- `naicsCode`
- `classificationCode`
- Set-aside codes and descriptions (`setAside`, `setAsideCode`)

### Location fields
- `placeOfPerformance`
- `data.placeOfPerformance.streetAddress`
- `data.placeOfPerformance.city`
- `data.placeOfPerformance.state`
- `data.placeOfPerformance.country`
- `data.placeOfPerformance.zip`
- `officeAddress`
- `state` request parameter for place-of-performance state
- `zip` request parameter

### Value fields
- `data.award.amount`
- `data.award.date`
- `data.award.awardee`
- likely award-based data when available

### Agency and organization fields
- `organizationCode`
- `organizationName`
- `department`
- `subtier`
- `office`
- `fullParentPathName`

### Contact fields
- `data.pointOfContact.type`
- `data.pointOfContact.title`
- `data.pointOfContact.fullname`
- `data.pointOfContact.email`
- `data.pointOfContact.phone`
- `data.pointOfContact.fax`
- `data.pointOfContact.additionalInfo`

### Award fields
- `data.award.number`
- `data.award.amount`
- `data.award.date`
- `data.award.awardee.name`
- `data.award.awardee.location.*`

## 7. Opportunity types

The official API request docs define `ptype` options including:
- `u` = Justification (J&A)
- `p` = Pre-solicitation
- `a` = Award Notice
- `r` = Sources Sought
- `s` = Special Notice
- `o` = Solicitation
- `g` = Sale of Surplus Property
- `k` = Combined Synopsis/Solicitation
- `i` = Intent to Bundle Requirements

This is important because not every SAM.gov notice is a live construction opportunity. ACE must clearly filter for a subset of notice types relevant to construction.

The likely relevant categories are:
- `o` = Solicitation
- `p` = Pre-solicitation
- `k` = Combined Synopsis/Solicitation
- possibly `s` or `r` depending on construction-related procurements
- `a` = award notice is not a lead source for bidding, but is relevant for historical or post-award analysis

Classification:
- opportunity type filter is VERIFIED
- construction relevance is not guaranteed from notice type alone
- construction filtering should rely on NAICS / classification / description / title heuristics

## 8. Construction relevance

### Verified classification fields

Verified fields from the SAM.gov API documentation:
- `naicsCode`
- `classificationCode`
- `typeOfSetAside`
- `setAside`
- `setAsideCode`

These are the strongest verified classification fields for identifying construction or public works relevance.

### Future heuristic guidance

The project should not assume that any field alone defines construction. A practical future heuristic would use:
- NAICS codes relevant to construction and heavy civil work
- title keywords
- description text
- procurement type
- place-of-performance location
- set-aside information where relevant

This should be treated as:
- VERIFIED CLASSIFICATION: `naicsCode`, `classificationCode`, `ptype`
- FUTURE HEURISTIC: keyword-based construction matching from title/description

The key distinction is that the API exposes classification metadata, but construction relevance still requires business-specific filtering logic that may vary by ACE’s target markets.

## 9. Date/deadline findings

### Verified fields

Official docs document:
- `postedDate`
- `reponseDeadLine` (response deadline field)
- `archiveDate`
- `postedFrom` and `postedTo` request parameters
- `rdlfrom` and `rdlto` response deadline date filters

These fields are enough to support a future normalized deadline contract and a basic active opportunity check.

### Important nuance

The field names are slightly inconsistent in the official docs (`reponseDeadLine` is spelled with a missing `n`), so the ingestion layer must normalize the source schema carefully instead of assuming a perfect field name.

## 10. Location findings

### Verified fields

Official docs clearly include:
- `state` request parameter
- `zip` request parameter
- `placeOfPerformance` object
- `data.placeOfPerformance.city.*`
- `data.placeOfPerformance.state.*`
- `data.placeOfPerformance.country.*`
- `data.placeOfPerformance.zip`

This is enough to build a future normalized location mapping for `city`, `state`, `zip`, and maybe coordinates when those are later available.

## 11. Value findings

### Verified fields

The API docs include value-related award information under:
- `data.award.amount`
- `data.award.number`
- `data.award.date`

This means the API has some value data, but it is likely award-value oriented. It is not necessarily the same as current opportunity budget or estimated value on an active solicitation.

Important distinction:
- award amount is verified
- active opportunity value range is not clearly guaranteed for all notices

This matters because ACE will likely want to normalize an estimated value field, but the public source may provide only award amounts for some notice types.

## 12. Agency findings

### Verified fields

Official docs include:
- `organizationCode`
- `organizationName`
- `fullParentPathName`
- `fullParentPathCode`
- `department`
- `subtier`
- `office`
- `organizationType`

This supports agency ownership and routing context for future review and outreach flows.

## 13. Document/attachment findings

### Verified facts

Official docs state:
- `description` is a link to opportunity description data
- the description requires the API key to access
- the response includes `resourceLinks` for direct downloads of attachments
- the API may return `additionalInfoLink`
- `uiLink` is direct UI link to the opportunity, but requires a role to view in the UI

This is important for ACE because document access matters for true estimating workflows.

### Separation of metadata vs actual content access

VERIFIED:
- metadata exists for attachments and descriptions
- attachment URLs exist in the API payload

UNKNOWN / REQUIRES FURTHER VERIFICATION:
- whether every attachment is downloadable without additional authentication or restrictions
- whether plan/specification documents are consistently provided for all notice types
- whether document download is always permitted under the API policy and site terms

The API docs show metadata and link fields are present, but not every attachment will necessarily be a downloadable plan package.

## 14. Contact findings

### Verified fields

The official API includes contact metadata:
- `data.pointOfContact.type`
- `data.pointOfContact.title`
- `data.pointOfContact.fullname`
- `data.pointOfContact.email`
- `data.pointOfContact.phone`
- `data.pointOfContact.fax`
- `data.pointOfContact.additionalInfo`

This supports future contact extraction and review workflows, but contact data is not guaranteed for every notice.

## 15. Raw provider contract

A SAM.gov raw provider should return a source record preserving enough metadata for reprocessing and debugging. At minimum it should include:
- source
- source_id
- fetched_at
- raw_payload
- source_url
- original source metadata

This aligns with the existing repository ingestion model in [src/ingestion/service.py](../src/ingestion/service.py) and the raw record model in [src/models/core.py](../src/models/core.py).

A raw SAM.gov record should not be flattened prematurely. The raw payload must contain the original notice object so the ingestion layer can be corrected later without requerying the source.

## 16. Normalization contract

### Source-to-normalized mapping table

| SAM.gov field | Normalized field | Transformation | Required? | Nullable? | Notes |
|---|---|---|---|---|---|
| `title` | `title` | trim + clean text | Yes | No | core identity |
| `description` | `description` | preserve text or link metadata | No | Yes | may be a link-only value |
| `placeOfPerformance.city.name` | `city` | normalize to title-case | Usually | Yes | likely available |
| `placeOfPerformance.state.code` | `state` | uppercase 2-letter code | Usually | Yes | likely available |
| `placeOfPerformance.zip` | `zip` | normalize string | Usually | Yes | may be absent |
| `postedDate` | `posting_date` | ISO-like normalization | Yes | No | strong candidate |
| `reponseDeadLine` | `bid_deadline` | map to normalized date | Usually | Yes | field name typo in docs |
| `active` | `project_status` | map active/inactive/archived | Usually | Yes | later canonical field |
| `ptype` | `procurement_type` | preserve enumerated value | No | Yes | useful for filtering |
| `naicsCode` | `naics_code` | preserve string/code | No | Yes | classification field |
| `classificationCode` | `classification_code` | preserve string/code | No | Yes | classification field |
| `setAsideCode` | `set_aside_code` | preserve string | No | Yes | relevant for set-aside workflows |
| `organizationName` / `fullParentPathName` | `owner_or_agency` | preserve string | No | Yes | later canonical field |
| `solicitationNumber` | `solicitation_number` | preserve string | No | Yes | useful identity |
| `resourceLinks` | `documents` | preserve list of URLs | No | Yes | later canonical field |
| `uiLink` | `source_url` | preserve official link | Yes | No | important review/reference field |
| `data.award.amount` | `estimated_value` | numeric conversion if present | No | Yes | may be award value only |

Only the mappings above are supported by the verified public docs. Anything else should be labeled as a future assumption until verified.

## 17. Current canonical mapping

### Fields that can safely populate the current canonical Project model

The current runtime `Project` model includes `name`, `source`, `source_id`, `city`, `state`, `trades`, `bid_date`, `estimated_value`, `provenance`.

| SAM.gov field | Current Project field | Safe? | Transformation | Loss of information? | Notes |
|---|---|---|---|---|---|
| `title` | `name` | Yes | direct mapping | Some nuance lost | safe |
| `source` | `source` | Yes | fixed as `sam_gov` or equivalent | none | provider identity |
| `noticeid` or stable ID | `source_id` | Yes | source identifier | none | canonical dedupe key |
| `placeOfPerformance.city.name` | `city` | Yes | lower/normalize map | minor | safe |
| `placeOfPerformance.state.code` | `state` | Yes | uppercase 2-letter | minor | safe |
| `postedDate` | `bid_date` | Maybe | use as posting date only if no better date exists | some semantics lost | not always a bid deadline |
| `data.award.amount` | `estimated_value` | Maybe | numeric conversion | may be award value, not estimate | use only where appropriate |
| `resourceLinks` / `description` | `provenance` or raw payload | Yes | retain in raw / provenance only | none | keep outside minimal canonical model |
| `naicsCode` | none | No, not currently | keep in raw / normalized data only | n/a | future field |
| `reponseDeadLine` | `bid_date` | Not safe | could be confusing if it is a deadline rather than a posting date | moderate | must remain raw / normalized first |

### Fields that should remain raw/normalized only for now

These are not safe for the current canonical model without a verified schema change:
- `status`
- `reponseDeadLine`
- `archiveDate`
- `naicsCode`
- `classificationCode`
- `setAsideCode`
- `resourceLinks`
- `uiLink`
- `organizationName`
- `description` (if it is a generated link instead of full text)
- `data.pointOfContact.*`
- `data.award.*`

## 18. Minimum future schema expansion

The following fields are the most likely minimum set to eventually add, if the source is chosen and validated:

| FIELD | WHY NEEDED | SOURCE | RELIABLE? | MATCHER NEED? | REVIEW NEED? | OUTREACH NEED? | CAN STAY IN RAW/NORMALIZED FIRST? |
|---|---|---|---|---|---|---|---|
| `project_status` | active vs archived | `active`, `type`, `archiveType` | High | Yes | Yes | Yes | possible |
| `bid_deadline` | timing crucial | `reponseDeadLine` | Medium-high | Yes | Yes | Yes | better in normalized first |
| `posting_date` | freshness | `postedDate` | High | Yes | Yes | Yes | likely canonical later |
| `source_url` | review and trust | `uiLink` | High | No | Yes | Yes | likely canonical later |
| `project_description` | narrative context | `description` | Medium | maybe | Yes | Yes | likely keep in normalized data first |
| `solicitation_number` | tracking | `solicitationNumber` | High | No | Yes | Yes | likely canonical later |
| `owner_or_agency` | procurement ownership | `organizationName` / `fullParentPathName` | High | maybe | Yes | Yes | normalized first |
| `zip` | location precision | `placeOfPerformance.zip` | Medium | maybe | Yes | Yes | normalized first |
| `documents_url` | package access | `resourceLinks` | Medium-high | No | Yes | Yes | normalized first |
| `procurement_method` | context | `ptype` | High | maybe | Yes | Yes | normalized first |
| `naics_code` | classification | `naicsCode` | High | probably | Yes | Yes | normalized first |
| `classification_code` | classification | `classificationCode` | Medium | maybe | Yes | Yes | normalized first |
| `estimated_value` | opportunity scale | `data.award.amount` | Medium | maybe | Yes | Yes | keep as raw or normalized first |

This list is intentionally conservative. No schema change should be made without verified source use.

## 19. $0 development path

### What is feasible at $0

A fixture-backed SAM.gov provider is feasible at $0 because it can be built against a public contract documentation path without a live API key.

This would allow:
- local project ingestion tests
- fixture-based validation of the contract
- pipeline design without credential leakage
- later live integration after credentials are available

### What is not currently feasible at $0

A production live API integration cannot be honestly claimed to be free and no-credential from the official documentation we have verified:
- the public API requires an API key
- there is a documented account-based creation flow
- the docs indicate request limits depending on role type
- the public web UI and API are different access models

Therefore:
- PHASE 8 design supports a fixture-backed provider first
- a live SAM.gov provider would require a real account/credential path later
- no live integration should be implemented without secure credential management and API-validation work

## 20. Phase 9 test plan

The next engineering phase should test the fixture-backed SAM.gov contract, not a live provider. Suggested test cases:

1. valid construction opportunity
2. non-construction opportunity
3. missing optional fields
4. missing required identity
5. malformed dates
6. duplicate opportunity
7. repeated ingestion
8. status handling
9. deadline normalization
10. location normalization
11. classification extraction
12. document metadata preservation
13. source provenance preservation
14. idempotency across repeated runs
15. raw payload preservation

This is the right level of test coverage for the next provider design without introducing a live API dependency.

## 21. Security considerations

All SAM.gov records should be treated as untrusted input.

Future requirements should include:
- sanitization of HTML/script content before rendering or feeding into any later language-model workflow
- URL validation and safe allow-listing for official source links
- attachment validation and size limits
- malformed payload handling
- unexpected field handling
- document content isolation before local storage or parsing
- no blind trust of field values from public notices

This is a design note only; no security infrastructure is being implemented in this phase.

## 22. Verified facts

VERIFIED:
- SAM.gov provides a public Contract Opportunities API.
- API endpoint is `https://api.sam.gov/opportunities/v2/search`.
- `api_key` is required by the official API docs.
- Public SAM.gov search is available without a payment flow.
- The API supports date range requests and pagination.
- It includes fields for `title`, `solicitationNumber`, `postedDate`, `reponseDeadLine`, `naicsCode`, `classificationCode`, `active`, `placeOfPerformance`, and `resourceLinks`.
- It includes contact metadata and agency/organization metadata.
- The API docs clearly distinguish between official API access and public UI browsing.

## 23. Unknowns

UNKNOWN / REQUIRES FURTHER VERIFICATION:
- exact numeric rate limits by user role
- exact free-vs-paid licensing model for automated API access
- exact production credentials model for all account types
- whether all opportunity types provide consistent document attachments
- whether all relevant construction filters can be identified reliably from official fields
- whether the official API supports every future ACE workflow without additional data sources

This means we do not yet have enough proof to implement a live production SAM.gov provider without further verification and credential setup.

## 24. Exact Phase 9 prerequisites

Phase 9 should not begin until all of the following are true:
1. the official SAM.gov API endpoint and auth model are fully reviewed and documented
2. the relevant response fields for construction-relevant notices are verified
3. the minimum canonical fields are approved
4. the fixture-backed provider contract is designed to mirror the official payload
5. the live API credential path is documented and securely handled
6. the project confirms that a fixture-backed first implementation is a realistic $0 path
7. the provider contract is aligned to the current ingestion architecture without requiring schema redesign

## 25. Conclusion

This phase is best classified as BLOCKED rather than PASS.

Why:
- the official docs confirm that SAM.gov is a valid public federal contract-opportunity source
- they also confirm that the public API requires an API key and a SAM.gov account
- they do not give us enough complete end-to-end documentation to implement a production live provider without further validation
- the source is promising and worth designing against, but it is not yet ready for live implementation

Therefore, the correct next step is not production integration. The correct next step is a fixture-backed SAM.gov contract model that reflects the official API contract while staying local and $0-compatible.

Phase 8 succeeded in reducing uncertainty, but it did not fully eliminate the outstanding credential and schema-validation questions.

## 26. Phase 9 outcome

Phase 9 implements the locally validated contract without bypassing the Phase 8 decision. The repository now includes a deterministic SAM.gov fixture provider that maps the verified public contract fields into the existing ingestion architecture while remaining fully local and offline.

This phase intentionally keeps the live integration disabled. No live HTTP call, network dependency, credential, or real SAM.gov account is required for repository execution.
