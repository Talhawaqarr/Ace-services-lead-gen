# ACE Services — Demo Runbook

## 1. Start the stack

From the repository root:

```powershell
docker compose build api
docker compose up -d
docker compose ps
```

Verify readiness:

```powershell
(Invoke-WebRequest -Uri "http://localhost:8000/health/ready").Content
```

Expected:

```json
{"status":"ready","database":"ok"}
```

## 2. Enable live SAM.gov mode

The live demo requires the existing `SAMGOV_API_KEY` and:

```text
INGESTION_MODE=samgov
```

The Compose configuration already passes these values into the API container.

The demo deliberately makes **one request for one record**. It does not auto-page through the source.

## 3. Open the workspace

Open:

```text
http://localhost:8000/
```

The top of the page contains **Demo controls**.

Default demo lookup:

- Keyword / solicitation: `36C26126Q1279`
- State: `CA`
- NAICS enforced by the server: `236220`
- Records requested: `1`
- Maximum pages: `1`

The default is a real SAM.gov Contract Opportunity selected for the current demo window. The keyword and state can be changed in the UI if the notice expires or another real construction opportunity is preferred.

## 4. Run the live sync

Click **Run tiny live SAM.gov sync**.

The API performs:

1. live SAM.gov lookup;
2. raw-record capture;
3. normalization;
4. construction-relevance boundary;
5. PostgreSQL persistence;
6. contractor fixture ingestion;
7. opportunity qualification;
8. deterministic contractor matching.

The UI then refreshes the opportunity list.

## 5. Review a match

Select the newly ingested opportunity.

If no matches exist, use the candidate/evidence state shown by the workspace rather than weakening matching rules.

If matches exist:

1. Open the match.
2. Inspect score, confidence, and evidence.
3. Click **Approve**.

The review audit history should show the status transition.

## 6. Generate and approve outreach

After a match is approved:

1. Click **Generate Outreach Draft**.
2. Read the deterministic draft.
3. Click **Approve Draft**.

The draft is still not sent.

## 7. Queue safely

After draft approval:

1. Click **Queue outreach (not sent)**.
2. The workspace should show **Queued safely — NOT SENT**.

Queueing only persists a delivery intent. The current demo does not deliver email.

## Safety invariants

- Live SAM.gov request is hard-bounded to one record and one page.
- The API key is never rendered in the UI.
- Match approval is required before outreach generation.
- Outreach draft approval is required before queueing.
- Queueing does not send email.
- Existing DRY_RUN/mock-email safety remains in effect.
- Synthetic contractor contacts are demo-only records and must not be contacted.

## If live SAM.gov quota is exhausted

Do not repeatedly retry.

Wait for the quota reset and keep the demo request at one record. The API returns HTTP 429 without committing a failed demo run.

For a fully offline rehearsal, use the existing fixture-backed local pipeline:

```powershell
Invoke-WebRequest -Method Post -Uri "http://localhost:8000/pipeline/local/run"
```

Then refresh the workspace.

## Final verification

Before the demo:

```powershell
docker compose exec api python -m pytest -q
```

The expected baseline from the last verified run is **153 passed**. New demo-flow tests should also pass before treating the implementation as release-ready.
