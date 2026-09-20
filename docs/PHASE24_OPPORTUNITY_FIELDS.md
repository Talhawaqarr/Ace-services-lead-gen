# Phase 24 — Opportunity Operational Fields

## Goal

Promote the opportunity fields needed for an actual lead-generation workflow from opaque provenance JSON into the canonical project record.

## Canonical fields

- posted_date: source posting timestamp.
- response_deadline: bid/response deadline when supplied by the source.
- status: source-provided opportunity status/active indicator.
- description: normalized opportunity description.
- source_url: canonical source/notice URL.

bid_date remains for backward compatibility with the existing matcher. For SAM.gov-shaped records it continues to fall back to the posting date when no explicit bid date exists.

## Why this matters

The lead-generation product needs to filter and display opportunities by deadline, status, and source link without repeatedly parsing source-specific provenance payloads.

This phase does not add live SAM.gov access, automated outreach, or ML.

## Migration

Alembic migration 0007 adds the nullable columns. Existing records remain valid and can be backfilled from provenance in a later controlled migration/job.
