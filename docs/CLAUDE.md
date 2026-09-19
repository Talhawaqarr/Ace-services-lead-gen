## Claude (Anthropic) Notes — ACE Services

This file records notes about using Anthropic/Claude as an optional LLM provider.

Project rule (permanent):
- Development must work with zero paid APIs.
- Never assume the user has API keys.
- Never require a paid provider for MVP.
- Paid providers must be optional adapters and never required for development.
- Default to local/free implementations for LLM needs (deterministic templates, rule-based fallbacks, or local models).
- Never send real emails during development; Dry-run email mode is the default.
- Never fabricate real-world data; synthetic data must be clearly labeled.
- Never bypass provider restrictions or recommend purchasing an API as a prerequisite unless absolutely unavoidable.

Notes for Claude-specific evaluation (optional POST-MVP):
- Claude offers strong few-shot reasoning but differs in safety/compliance characteristics.
- When offering as a provider, ensure `LLM_CONTRACT.md` mappings are satisfied.
- Tokens and pricing: document when evaluating as alternative to OpenAI.
- Implement adapter with `embed` and `generate` methods as in `PROVIDER_CONTRACTS.md`.

Keep this as a reference when evaluating Anthropic for fallback.

## $0 Development Checklist (appendix)
- Ensure all developers can run the system end-to-end without API keys.
- Default to `DRY_RUN=true` in `.env.example` for all outbound integrations.
- Add synthetic dataset examples and a developer script `scripts/load_synthetic_data.py` to populate the DB.
- Provide a `providers/mock` adapter set for BidProvider/ContractorProvider/EmailProvider/LLMProvider that returns deterministic fixtures.
- Document in `docs/ENVIRONMENT.md` how to toggle paid adapters when (and only when) keys are available.