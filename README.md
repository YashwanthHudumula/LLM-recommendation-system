# RecLLM item-side exposure fairness

**Current status:** confirmatory collection is complete with 79,200 immutable records across
three local model snapshots, two domains, 100 personas per domain, and three repeats. The frozen
provider-free primary analysis, both registered sensitivity views, and persona-clustered robust
fit diagnostics are complete and checksummed. The within-candidate-opportunity sensitivity is
also complete across all six domain/views. Final figures, the manuscript, bibliography
verification, and external archival deposition remain pending before journal submission.

This repository implements the study **Who Gets Seen? Auditing Item-Side Exposure
Disparities Induced by Personality-Conditioned Prompting in LLM-Based Recommender
Systems**. It is an inference-only, counterfactual audit: fixed preferences and catalog,
varying Big-Five language and prompt phrasing, with both individual-list and aggregate
catalog-exposure evaluation.

## Scientific design

Each base persona keeps the same stated content preferences across every counterfactual.
The experiment crosses persona, Big-Five trait, trait level, prompt phrasing, domain,
model, and repeat. Raw query records are append-only and are the sole source of truth.
All metrics are derived later, so analysis can be rerun without model calls.

The primary outcomes are:

- user side: Jaccard@K, SERP*@K, PRAG*@K, SNSR, SNSV, and PAFS;
- item side: Gini, HHI, average recommendation popularity, catalog/long-tail coverage,
  MGU, and DGU;
- utility controls: Precision@K and NDCG@K;
- inference: persona-resampled confidence intervals, mixed-effects models,
  Benjamini-Hochberg correction, pre-registered RQ3 scenario classification, and transparent
  persona-clustered robust alternatives when mixed models are singular.

## Safety and cost controls

The default pilot uses a deterministic mock model and synthetic data, so it makes no API
calls and costs nothing. Real providers are disabled until a model snapshot, price, key
environment variable, pilot cost estimate, and hard budget cap are configured. Collection
is resumable and one immutable Parquet file is written per completed query.

## Setup

Python 3.11–3.13 is supported. The project uses `uv` and pins all declared dependencies.

```powershell
python -m pip install uv
uv sync --extra dev
uv run pytest
```

## Typical workflow

```powershell
# Deterministically build pilot relevance labels from the downloaded datasets
uv run recllm-build-labels --stage pilot

# No-cost end-to-end validation
uv run recllm-pilot --config-dir config

# Same-model/domain scientific pilot after editing config/models.yaml
uv run recllm-collect --config-dir config --model openai --domain movie

# Reproduce analysis from the completed immutable query collection; no model call is made
uv run recllm-analyze --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --stage full --domain movie --analysis-version confirmatory-analysis-v2

# Registered exact-10, paired-neutral sensitivity view
uv run recllm-analyze --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --stage full --domain movie `
  --analysis-version confirmatory-analysis-v2-sensitivity-exact10 `
  --sensitivity exact-10-grounded

# Fit remediation over an existing analysis package
uv run python -m recllm_fairness.pipeline.run_fit_diagnostics `
  outputs/tables/analysis/<analysis-package>

# Opportunity-adjusted replay from a frozen paired-analysis package
uv run recllm-opportunity-analyze `
  outputs/tables/analysis/<analysis-package> `
  --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --analysis-version confirmatory-analysis-v3-opportunity `
  --bootstrap-resamples 2000
```

See `data/DATA_SOURCES.md` before downloading data, and `progress.md` for implementation
and verification status. The research proposal is the scientific source of truth;
`AGENTS.md` is the engineering architecture.

The consolidated architecture, methodology, audit history, pilot diagnostics, limitations,
execution workflow, and publication gates are maintained in
[documentation.md](documentation.md).
The completed clean-environment replay and sensitivity gate are documented in
[documentation/14_REPRODUCIBILITY_GATE_AND_SENSITIVITY_V2.md](documentation/14_REPRODUCIBILITY_GATE_AND_SENSITIVITY_V2.md).
The opportunity-adjusted sensitivity and its results are documented in
[documentation/15_WITHIN_OPPORTUNITY_SENSITIVITY_V3.md](documentation/15_WITHIN_OPPORTUNITY_SENSITIVITY_V3.md).

The six-persona v1 pilot and 100-persona A1 confirmatory designs are frozen. Collection verifies
the frozen bundle on disk and refuses incompatible or unfrozen designs before loading a model or
full dataset. The complete confirmatory evidence is preserved locally with per-file and
per-archive SHA-256 manifests; raw datasets and model-response Parquet files remain excluded from
Git because of size, privacy, and licensing constraints.

For publication runs, follow [the experiment protocol](docs/EXPERIMENT_PROTOCOL.md) and
cite formulas exactly as operationalized in [the metric specification](docs/METRICS.md).
The smoke pilot is not empirical evidence; it validates software and storage only.
