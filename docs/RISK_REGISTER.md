# Risk Register — ACE Services

Top risks, impact, likelihood, and mitigations.

1. Paywalled / commercial feed dependency
- Impact: High (loss of high-quality leads)
- Likelihood: Medium
- Mitigation: Start with government feeds (SAM.gov), keep commercial feeds optional until ROI justified; record dependency in docs.

2. Licensing / redistribution restrictions
- Impact: High (legal exposure)
- Likelihood: Medium
- Mitigation: Legal review for every commercial provider; store provenance and do not redistribute raw payloads without contract permissions.

3. Email deliverability / reputation issues
- Impact: High (blocked outreach)
- Likelihood: Medium
- Mitigation: Use Postmark or reputable provider, domain verification, warm-up, suppression lists, bounce handling.

4. Data quality & deduplication errors
- Impact: Medium
- Likelihood: High
- Mitigation: Conservative auto-merge thresholds, manual review UI, provenance retention.

5. LLM hallucination in email copy
- Impact: Medium
- Likelihood: Medium
- Mitigation: Use grounding in prompts, include source citations, require human approval before send for sensitive claims.

6. PII / compliance (GDPR, state regulations)
- Impact: High
- Likelihood: Low–Medium (depends on target geography)
- Mitigation: Provide suppression/unsubscribe flows, privacy policy, legal review for EU-targeted outreach.

7. Cost overruns (embeddings, feeds)
- Impact: Medium
- Likelihood: Medium
- Mitigation: Cost caps, batching, monitoring, choose self-hosted embeddings if needed.

8. Vendor lock-in
- Impact: Medium
- Likelihood: Medium
- Mitigation: Adapter pattern, store canonical data, avoid embedding-only dependencies in core functions.

9. Operational outages (DB, queue)
- Impact: High
- Likelihood: Medium
- Mitigation: Monitoring, alerts, DR plan, backups, runbooks.

Review cadence: Review register monthly during early rollout and after major provider integrations.
