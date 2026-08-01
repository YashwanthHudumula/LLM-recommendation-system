# RecLLM item-side exposure fairness

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
  Benjamini-Hochberg correction, and pre-registered RQ3 scenario classification.

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

# Full collection only after the matching pilot and budget gate pass
uv run recllm-collect --config-dir config --model openai --domain movie --stage full

# Analysis never calls a model
uv run recllm-analyze --config-dir config
```

See `data/DATA_SOURCES.md` before downloading data, and `progress.md` for implementation
and verification status. The research proposal is the scientific source of truth;
`AGENTS.md` is the engineering architecture.

The persona/relevance design remains a draft until the cooling-off and independent blind
wording reviews recorded in `config/persona_relevance_design_v1.yaml` are complete. Collection
uses the generated label JSON directly and refuses to proceed if the required stage file is
missing.

For publication runs, follow [the experiment protocol](docs/EXPERIMENT_PROTOCOL.md) and
cite formulas exactly as operationalized in [the metric specification](docs/METRICS.md).
The smoke pilot is not empirical evidence; it validates software and storage only.
