# DATA SOURCES PHASE 5

## Source 1: USAspending-style public federal award data

- Source name: USAspending / federal award data
- Organization: U.S. Department of the Treasury / USAspending.gov
- Data type: federal spending award records; public procurement/award metadata
- Geographic coverage: United States federal awards, geographically distributed by state/metro/
- Construction relevance: relevant to public-sector construction and infrastructure spending; useful for public project discovery and market-signal analysis
- Access method: public API / public data endpoints documented by USAspending; this repo uses a local fixture-backed adapter to keep the implementation reproducible and $0-safe
- Authentication requirement: no mandatory API key for basic public access in the public documentation; this project intentionally does not depend on credentials for local execution
- Cost: free/public data
- Rate limits: publicly documented API rate limits vary by endpoint; this implementation is intentionally bounded and local-only
- Terms/usage restrictions: public federal data with government terms and data-use restrictions; this implementation respects local-only usage and does not bypass or redistribute protected material
- Fields available: project/award identifiers, agency, location, award amount, dates, recipient details, NAICS/PSC data when supplied by the source
- Project/bid identifiers: award identifiers and source IDs are available in the public contract
- Bid dates: award dates and relevant transaction dates are available from the public source model
- Location: state, city, and place-of-performance data are available
- Project type/trade information: sometimes present via NAICS/PSC or descriptive text, but not always stable or granular enough for direct trade matching
- Contractor information: recipient and awardee information is publicly available when the source includes it
- Update frequency: public federal award records update as transactions are reported; exact intervals are source-defined
- Implementation difficulty: moderate; source fields vary and require normalization
- Whether it can be used at $0: yes, as a local fixture-backed adapter and future real API integration with public data access
- Phase 5 decision: USE NOW (local fixture-backed)

## Source 2: SAM.gov contract opportunities

- Source name: SAM.gov Contract Opportunities
- Organization: U.S. General Services Administration / SAM.gov
- Data type: federal contract opportunities and notices
- Geographic coverage: U.S. federal contracting opportunities across regions and agencies
- Construction relevance: directly relevant to federal project opportunities
- Access method: public search and data services; public documentation is available; live API access may require account or service-specific integration details
- Authentication requirement: some features require user accounts; public browsing is available, but programmatic access must be verified with the official docs
- Cost: free/public data
- Rate limits: source-specific rate limits may apply; confirm via official documentation before production access
- Terms/usage restrictions: government public-data terms apply
- Fields available: opportunity title, agency, location, date, award amount, NAICS/PSC, contract descriptions
- Project/bid identifiers: opportunity IDs and references are available
- Bid dates: solicitation and response dates are provided in opportunity data
- Location: definitely available by agency and location fields
- Project type/trade information: available via NAICS and textual descriptions, but often variable
- Contractor information: not always directly present; may require a separate contractor lookup flow
- Update frequency: high
- Implementation difficulty: moderate
- Whether it can be used at $0: yes, at the public-data level, but this repo does not require live activation for Phase 5
- Phase 5 decision: LOCAL/SYNTHETIC ONLY for this repository until a verified public access contract is implemented

## Phase 9 status: fixture-backed SAM.gov contract

The repo now supports a local-only, deterministic SAM.gov-shaped opportunity provider at `src/providers/samgov.py` and fixture data in `docs/fixtures/phase9_samgov_opportunities.json`.

This implementation is intentionally not a live integration. It does not make network calls, it does not require an API key, and it does not claim authenticated access to official SAM.gov endpoints.

The source identity rule for this implementation is:
- prefer `solicitationNumber` when it is present
- otherwise fall back to `source_id`
- never use a title as a stable identity key

The fixture preserves raw SAM.gov fields verbatim, including the official `reponseDeadLine` spelling, while the ingestion pipeline keeps an internal normalized `response_deadline` field for downstream logic.

The `data.award.amount` value remains award metadata only; it is not promoted to the canonical project `estimated_value` without an explicit source contract that defines the equivalence.

This keeps ACE cleanly separated between:
- SOURCE INGESTION: preserve raw data and auditability
- CONSTRUCTION RELEVANCE: explicit deterministic heuristics or future filtering layers
- CANONICAL PROJECT MODEL: stable and intentionally narrow

## Source 3: State-level public bid boards

- Source name: state procurement bulletin/contract opportunities
- Organization: state agencies and public portals
- Data type: procurement notices and public construction opportunities
- Geographic coverage: varies by state
- Construction relevance: high for local public construction opportunities
- Access method: public web pages or official API feeds, varies by state
- Authentication requirement: often none for public pages; some data feeds may require API keys or registration
- Cost: usually free/public
- Rate limits: state-specific
- Terms/usage restrictions: varies by jurisdiction
- Fields available: state, date, project title, department, estimated value, location
- Project/bid identifiers: often present but inconsistent across states
- Bid dates: commonly included
- Location: location and jurisdiction are usually included
- Project type/trade information: often in titles or categories
- Contractor information: limited or absent
- Update frequency: varies
- Implementation difficulty: moderate due to heterogeneity
- Whether it can be used at $0: often yes, but only if implemented with official public feeds or human-verified local fixtures
- Phase 5 decision: FUTURE

## Source 4: ConstructConnect / Dodge / PlanHub / Blue Book

- Source name: commercial construction lead providers
- Organization: private commercial vendors
- Data type: project leads and bid opportunities
- Geographic coverage: broad, varying by market
- Construction relevance: very high
- Access method: licensed API/data feeds or web portals
- Authentication requirement: account + commercial contract
- Cost: paid
- Rate limits: vendor-defined
- Terms/usage restrictions: licensing and redistribution restrictions typically apply
- Fields available: project description, trades, location, plan room data, contacts, documents
- Project/bid identifiers: yes, vendor-defined stable IDs
- Bid dates: usually included
- Location: yes
- Project type/trade information: yes, often robust
- Contractor information: often yes
- Update frequency: high
- Implementation difficulty: moderate
- Whether it can be used at $0: no
- Phase 5 decision: FUTURE

## Source 5: OpenCorporates

- Source name: OpenCorporates records
- Organization: OpenCorporates
- Data type: company registry / legal entity metadata
- Geographic coverage: global / country coverage depends on registry data
- Construction relevance: moderate for contractor/entity normalization, not direct project discovery
- Access method: public API or open data access, often with rate limits and account tiers
- Authentication requirement: API key or account may be required
- Cost: free tier exists; commercial use may require paid plan
- Rate limits: documented by provider
- Terms/usage restrictions: license terms vary; do not assume unrestricted redistribution
- Fields available: legal names, addresses, registration data, officers, filing data
- Project/bid identifiers: not project-specific
- Bid dates: not applicable
- Location: yes
- Project type/trade information: not project-level
- Contractor information: yes
- Update frequency: varies
- Implementation difficulty: moderate
- Whether it can be used at $0: possibly for low-volume use, but not required for Phase 5
- Phase 5 decision: FUTURE

## Decision summary

- USE NOW: USAspending-style public federal award data via local fixture-backed adapter
- LOCAL/SYNTHETIC ONLY: SAM.gov integration path until official access is verified
- FUTURE: commercial project feeds, contractor enrichment registries, state-specific data integration
