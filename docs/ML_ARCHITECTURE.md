# ML Architecture — ACE Services

This document outlines the machine learning components, data flow, model choices, training, deployment, and monitoring strategies for the ACE Services project matching and email personalization features.

## Objectives
- Semantic matching between projects and contractors
- Generate personalized email copy using LLMs with factual grounding
- Use human feedback to train supervised ranking models over time

## Data sources for ML
- Canonical `projects` and `contractors` tables
- `match_feedback` for labelled outcomes
- Email engagement metrics from `email_events` (opens, replies, conversions)
- External enrichment (OpenCorporates records, license checks, past project descriptions)

## Components
1. Embeddings service
   - Provider: OpenAI embeddings (managed) or local sentence-transformers for self-hosting
   - Store embeddings in vector DB (Postgres pgvector or specialized vector DB like Pinecone/Weaviate)

2. Feature store
   - Deterministic features stored in `match_features` or `matches.features`
   - Embeddings referenced by id and kept in sync with `ml_models` versions

3. Model training & orchestration
   - Offline training pipeline using scikit-learn/LightGBM/XGBoost for ranking
   - Use Airflow or simple cron jobs to trigger training when feedback thresholds met
   - Persist models in model registry (`ml_models` table) with version ids

4. Inference
   - Deterministic scoring in Python service (FastAPI worker) for realtime
   - Hybrid scoring: server-side combine deterministic + embedding similarity
   - Supervised model served via lightweight prediction service (FastAPI endpoint) or integrated into workers

5. Email generation
   - LLM prompt templates with grounding context (project text, contractor brief facts)
   - Constrain generation with extractive placeholders; require list of claims + sources

## Storage
- Vector storage choices:
  - `pgvector` extension on Postgres for MVP
  - Or Pinecone/Weaviate for managed scaling
- Model artifacts stored in object storage (S3) with metadata in `ml_models`

## Training data & labels
- Label positive examples: contractor engaged, replied, shortlisted, awarded
- Negative examples: emailed but bounced, not relevant feedback
- Use positive sampling balancing to avoid bias

## Evaluation
- Track precision@K, recall, AUC
- Monitor distribution shift in embeddings and feature statistics
- Track fairness across geographies and trade types (avoid over-representing large contractors)

## Monitoring & Retraining
- Data drift detectors on embeddings and key scalar features
- Retrain cadence: weekly or when N new labelled examples available
- Use incremental training where possible

## Explainability
- Use SHAP for supervised models to extract feature importance
- Always surface deterministic rule reasons for transparency

## Cost considerations
- Embedding costs for OpenAI; batch embeddings off-peak
- Storage costs for vector DB and S3

This ML architecture favors a pragmatic progression: start deterministic, add embeddings for semantic recall, then train supervised models as labelled feedback accumulates.
