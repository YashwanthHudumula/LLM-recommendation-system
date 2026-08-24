# Project documentation

This folder is the consolidated documentation set for **Who Gets Seen? Auditing Item-Side
Exposure Disparities Induced by Personality-Conditioned Prompting in LLM-Based Recommender
Systems**.

The study is an inference-only, counterfactual audit of three frozen local LLM snapshots over
movie and music recommendation. A persona's content preference and candidate catalog remain
fixed while Big-Five trait wording and instruction phrasing vary. The study measures changes in
individual recommendation lists, aggregate item exposure, and relevance.

## Documentation map

1. [Project history and architecture](01_PROJECT_HISTORY_AND_ARCHITECTURE.md) explains the
   original architecture, the failed protocol-v1 diagnostic, closed-catalog-v2, the 100-persona
   confirmatory design, and amendment A1.
2. [Six pilot tests](02_SIX_PILOT_TESTS.md) records the Qwen, Gemma, and Llama movie/music
   pilots, their exact results, caveats, and provider-free v3 replay.
3. [Confirmatory design and collection](03_CONFIRMATORY_DESIGN_AND_COLLECTION.md) records the
   frozen population, matrix, model snapshots, sequence, quality gates, and current collection.
4. [Data, pipeline, metrics, and analysis](04_DATA_PIPELINE_METRICS_AND_ANALYSIS.md) documents
   datasets, persona construction, storage, grounding, metrics, statistics, and separation of
   immutable source records from derived analysis.
5. [Reproducibility and operations](05_REPRODUCIBILITY_AND_OPERATIONS.md) provides commands,
   pause/resume rules, workstation controls, verification, backup, and publication workflow.
6. [Audit and source index](06_AUDIT_AND_SOURCE_INDEX.md) maps claims to frozen configuration,
   machine-readable audits, manifests, code, and prior documentation.

## Current status snapshot

Snapshot date: **2026-08-06**. The confirmatory design is
`persona-relevance-v2-100-a1`, protocol `closed-catalog-v2-a1-retry`, frozen bundle SHA256
`f847715539c3d97c569cb597b9df50190c68be5bcd8eeb423f50871b84555d50`.

- Qwen/movie: 13,200/13,200 records, manifest completed, final operational verification passed.
- Qwen/music: collection in progress and resumable.
- Llama/movie, Llama/music, Gemma/movie, Gemma/music: pending in the frozen sequence.
- No confirmatory trait-level fairness outcomes have been inspected.

Collection status is operational and changes over time. The authoritative live source is each
partition's `run_manifest.json` plus its immutable Parquet record count.

## Interpretation boundary

Pilot outputs establish feasibility, grounding behavior, runtime, relevance controls, and
analysis-pipeline behavior. They are not publishable confirmatory fairness findings because the
pilot contained only six independent personas per domain. Confirmatory scientific conclusions
must wait until all six 13,200-record partitions pass final integrity checks and the frozen
analysis is run.
