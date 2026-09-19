# Product Roadmap — ACE Services

This roadmap outlines milestones for building the ACE Services MVP and subsequent phases.

Milestones
1. Research & architecture (COMPLETE)
   - Provider research
   - System and DB design

2. MVP Implementation (Phase 1) — $0 Development Mode
   - Constraints: No paid providers, no required API keys, Dry-run email default.
   - Provider adapters (FREE-first): SAM.gov, USAspending, OpenCorporates (FREE TIER), State license boards.
   - Ingestion pipeline, normalization, geocoding using FREE sources or local geocoder (OpenStreetMap / Nominatim self-host or simple Haversine distances).
   - Deterministic rule-based matching engine (geography, trade overlap, project size, history).
   - Basic UI for project review and contractor matches with clear "EMAIL NOT SENT — DEVELOPMENT MODE" banners.
   - Email generation: deterministic templates and operator approval; no real sends (DRY_RUN).

3. Hybrid Matching & Enrichment (Phase 2)
   - Embeddings + semantic matching
   - Contractor enrichment (licenses, past projects)
   - Email personalization via LLMs (OpenAI)

4. Supervised Ranking & Automation (Phase 3)
   - Supervised ranking models; feedback loop
   - Campaign automation and A/B testing
   - Integrations with CRM and bidding workflows

5. Scale & Commercialization
   - Add paid provider adapters (ConstructConnect, Dodge)
   - Advance analytics and bidding success prediction

Dependencies & Notes
- Phase 1 (FREE): does not require paid APIs. Use synthetic datasets, government sources, and local processing.
- Phase 2 (optional): Add embeddings and hosted LLMs only after budget or free-tier keys available; local open-source models can be explored before purchasing APIs.
- Phase 4 benefits from labeled outcome data (email replies, shortlisted, won) which may require real-world testing or optional paid provider integrations.

This roadmap is prioritized for early value: government projects first, then paid commercial feeds after revenue justification.
