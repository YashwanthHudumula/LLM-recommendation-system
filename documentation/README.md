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
7. [Reproducibility gate and sensitivity analysis](14_REPRODUCIBILITY_GATE_AND_SENSITIVITY_V2.md)
   records the clean Python 3.12.5 replay, registered exact-10 and unflagged views, singular-fit
   diagnosis, persona-clustered robust estimates, concordance audit, and remaining publication
   gates.
8. [Within-candidate-opportunity sensitivity](15_WITHIN_OPPORTUNITY_SENSITIVITY_V3.md) defines
   the eligibility-adjusted estimands, validates exact reconstruction, reports paired-bootstrap
   results and robustness, and records the checksummed v3 evidence package.

## Current status snapshot

Snapshot date: **2026-08-25**. The confirmatory design is
`persona-relevance-v2-100-a1`, protocol `closed-catalog-v2-a1-retry`, frozen bundle SHA256
`f847715539c3d97c569cb597b9df50190c68be5bcd8eeb423f50871b84555d50`.

- All six model/domain partitions are complete: 79,200/79,200 immutable records.
- Clean-environment primary replays are complete for movie and music at 2,000 bootstrap resamples.
- Registered exact-10-grounded and exclude-flagged-record sensitivities are complete.
- All six analysis packages have persona-clustered robust fit diagnostics and SHA-256 inventories.
- Within-opportunity primary, exact-10, and unflagged analyses are complete in both domains.
- Final figures, manuscript text, bibliography verification, and external DOI deposition remain.

The authoritative evidence is each partition's `run_manifest.json`, its immutable Parquet record
count, and `data/audits/confirmatory_analysis_v2_reproducibility.json` for the six analysis
packages, plus `data/audits/opportunity_analysis_v3_reproducibility.json` for the v3 sensitivity.

## Interpretation boundary

Pilot outputs establish feasibility, grounding behavior, runtime, relevance controls, and
analysis-pipeline behavior. They are not publishable confirmatory fairness findings because the
pilot contained only six independent personas per domain. Confirmatory scientific conclusions
must wait until all six 13,200-record partitions pass final integrity checks and the frozen
analysis is run.
