# Phase 23 — Transaction Boundary Hardening

## Goal

Keep database transaction ownership at the application boundary instead of allowing ingestion helpers to commit independently.

## Changes

- ingest_source_records() no longer calls session.commit().
- ingest_contractors() no longer calls session.commit().
- Callers decide when the transaction is committed.
- The standalone POST /ingestion/{source}/run endpoint now commits after successful ingestion.
- The end-to-end local pipeline already owns its transaction and continues to commit once after the complete pipeline finishes.
- Added a regression test proving an ingestion call can be rolled back without leaving partial canonical, raw, or run records.

## Why

A lower-level ingestion helper committing internally can create partial state when a higher-level workflow performs multiple operations. For example, opportunity ingestion could commit successfully and contractor ingestion or matching could fail afterward, leaving the pipeline only partially persisted.

The Phase 23 boundary is:

API / workflow -> transaction -> ingestion + normalization + persistence -> commit or rollback

Ingestion services perform database writes and flushes needed for generated IDs and constraint checks, but they do not finalize the transaction.

## Scope

This phase changes transaction ownership only. It does not add a job queue, distributed transactions, retries, or live external providers.
