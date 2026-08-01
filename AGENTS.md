# AGENTS.md — Item-Side Exposure Fairness in Personality-Conditioned RecLLMs

This file gives Codex the architecture and task breakdown for implementing the research
codebase described in `research_proposal_recllm_item_side_fairness.md`. Read that proposal
first if present in the repo; this file translates it into an engineering plan.

---

## 0. Project Goal (one paragraph)

Given a fixed movie/music catalog and a large synthetic population of personas that vary
only in implied Big-Five personality trait level and prompt phrasing, query several LLMs for
recommendations, then measure two things: (A) whether each individual persona's list shifts
relative to a neutral baseline (user-side fairness — reuse SNSR/SNSV/PAFS), and (B) whether
the *aggregate* distribution of recommended items across the whole population shifts — i.e.
does exposure concentrate on certain genres/providers/popularity tiers depending on which
personality trait was implied (item-side fairness — Gini/HHI/ARP/coverage/MGU/DGU). Compare
the two metric families statistically (RQ3). Everything is inference-only: no model training
or fine-tuning happens in this repo.

---

## 1. Repository Structure

```
recllm-item-fairness/
├── AGENTS.md                        # this file
├── README.md
├── pyproject.toml                   # poetry or uv; pin exact versions
├── config/
│   ├── base.yaml                    # shared defaults
│   ├── models.yaml                  # model endpoints, rate limits, pricing
│   ├── personas.yaml                # trait levels, phrasing variants, N per cell
│   └── datasets.yaml                # dataset paths/versions/checksums
├── data/
│   ├── raw/                         # untouched downloads (gitignored)
│   ├── processed/                   # cleaned catalogs, candidate pools (gitignored)
│   └── DATA_SOURCES.md              # exact download URLs, versions, checksums, license notes
├── src/
│   └── recllm_fairness/
│       ├── __init__.py
│       ├── data/
│       │   ├── movielens.py         # loader + cleaner for ML-1M / ML-25M
│       │   ├── lastfm.py            # loader + cleaner for LastFM-1K / 360K
│       │   ├── catalog.py           # unified Item schema, popularity-tier binning
│       │   └── candidate_pool.py    # fixes a per-query candidate pool (anti-hallucination)
│       ├── personas/
│       │   ├── traits.py            # Big Five trait marker language (IPIP-NEO-derived)
│       │   ├── phrasing.py          # formal/casual/direct/indirect templates
│       │   ├── generator.py         # builds the full persona x phrasing matrix
│       │   └── semantic_check.py    # sentence-transformers equivalence validation
│       ├── prompting/
│       │   ├── templates.py         # system/user prompt templates per domain
│       │   └── builder.py           # persona -> final prompt string
│       ├── models/
│       │   ├── base_client.py       # abstract LLMClient interface
│       │   ├── openai_client.py
│       │   ├── anthropic_client.py
│       │   ├── google_client.py
│       │   ├── hf_client.py         # open-weight models via HF Inference/Endpoints
│       │   └── registry.py          # name -> client factory, reads config/models.yaml
│       ├── parsing/
│       │   ├── response_parser.py   # LLM free text -> ordered item list
│       │   └── matcher.py           # fuzzy-match parsed titles to fixed candidate pool;
│       │                            # flags/drops hallucinated (non-catalog) titles
│       ├── metrics/
│       │   ├── user_side.py         # SNSR, SNSV, PAFS, Jaccard@K, SERP*@K, PRAG*@K
│       │   ├── item_side.py         # Gini, HHI, ARP@K, coverage, MGU@K, DGU@K
│       │   ├── relevance.py         # Precision@K, NDCG@K vs stated_preferences
│       │   └── aggregate.py         # pools per-query outputs into per-condition exposure dist
│       ├── stats/
│       │   ├── bootstrap.py         # persona-resample CIs for Gini/HHI/ARP
│       │   ├── mixed_effects.py     # trait+phrasing+model fixed effects, persona random effect
│       │   ├── correlation.py       # Spearman rank corr between user-side and item-side rankings
│       │   └── multiple_comparison.py # Benjamini-Hochberg correction
│       ├── pipeline/
│       │   ├── run_pilot.py         # small-scale end-to-end smoke test
│       │   ├── run_collection.py    # full persona x phrasing x model data collection
│       │   ├── run_analysis.py      # steps 3-6 of the experimental protocol
│       │   └── run_mitigation.py    # stretch: RQ5 fairness-prompt intervention
│       ├── storage/
│       │   ├── schema.py            # Parquet/CSV table schemas (see Section 5)
│       │   └── io.py                # read/write, resumability, dedup on (condition, persona, repeat)
│       └── utils/
│           ├── logging.py
│           ├── costs.py             # token/cost estimator, hard budget cap
│           └── seeding.py           # reproducible RNG seeds per condition
├── notebooks/                       # exploratory only, nothing load-bearing here
├── tests/
│   ├── test_matcher.py
│   ├── test_item_side_metrics.py
│   ├── test_user_side_metrics.py
│   ├── test_candidate_pool.py
│   └── test_stats.py
└── outputs/
    ├── figures/
    ├── tables/
    └── manuscript_assets/
```

---

## 2. Tech Stack

- Python 3.11+, managed with `uv` or `poetry` (pick one, pin lockfile).
- `pandas`, `numpy`, `scipy`, `statsmodels` — metrics and stats.
- `pyarrow` — Parquet storage (preferred over CSV for the large condition matrix).
- `sentence-transformers` — phrasing semantic-equivalence validation.
- `rapidfuzz` — fast fuzzy string matching for `parsing/matcher.py`.
- `httpx` (async) — all LLM API calls, with retry/backoff.
- `pydantic` v2 — config and record schemas.
- `hydra-core` or plain `PyYAML` — config composition (`hydra` recommended given many
  crossed conditions: trait x level x phrasing x model x domain x repeat).
- `pytest` — all metric implementations must have unit tests with hand-computed expected
  values before being trusted on real data.
- Optional: `wandb` for run tracking, gate behind a config flag (`logging.wandb: true/false`)
  since it should never be a hard dependency.

---

## 3. Data Layer

Implement exactly two dataset loaders, each producing a common `Item` schema so downstream
code is domain-agnostic.

**Item schema (Pydantic model in `data/catalog.py`):**
```python
class Item(BaseModel):
    item_id: str
    domain: Literal["movie", "music"]
    title: str
    genres: list[str]
    provider_or_studio: str | None   # best-effort; null if unavailable
    popularity_rank: int             # 1 = most popular, computed from interaction counts
    popularity_tier: Literal["head", "mid", "tail"]  # tertile or configurable cutoffs
    release_year: int | None
```

- **Movies**: MovieLens 1M for pilot, MovieLens 25M for full-scale run. Record exact version
  and checksum in `data/DATA_SOURCES.md`. Popularity = rating-count rank in the dataset.
- **Music**: LastFM-1K for the pilot/persona-preference construction (richer per-user
  listening history), LastFM-360K for full-scale item-side measurement (larger item pool).
  Popularity = play-count rank.
- **Candidate pool fixing (`data/candidate_pool.py`)**: per the proposal, the candidate pool
  must be fixed per query to prevent hallucinated titles from corrupting exposure
  measurement. Implementation: for each domain, pre-select a candidate set (e.g., top-N by
  popularity plus a stratified long-tail sample) and inject it into the prompt as an explicit
  "choose only from this list" instruction where the experimental condition allows, AND
  independently fuzzy-match every parsed output title against the *full* catalog (not just
  the injected candidates) so off-list ("hallucinated") recommendations are logged and
  excluded from item-side aggregation rather than silently kept or silently dropped.
  Log the hallucination rate per condition — it's a useful covariate, not noise.

---

## 4. Persona & Prompt Generation

- `personas/traits.py`: Big Five trait marker phrases must be drawn from IPIP-NEO-style
  language, not invented stereotypes (ethics requirement in the proposal). Store as a
  structured lookup: `{trait: {level: [marker phrases]}}`.
- `personas/generator.py`: builds the full crossed matrix — `persona_id x trait x
  trait_level x phrasing_variant x domain`, each persona also carrying a **fixed**
  `stated_preferences` string that does not vary across trait/phrasing variants of the same
  base persona (critical control — isolates the effect of trait language from actual taste).
- `personas/semantic_check.py`: before spending API budget, embed all phrasing variants of
  the same underlying instruction with `sentence-transformers` and assert cosine similarity
  above a configurable threshold; fail the pipeline loudly if any phrasing variant drifts
  semantically (this was a stated validation step in the proposal, not optional polish).
- Config-driven sample size: start with N=200 personas per trait-level in the pilot config,
  scale to 200–500 in `config/personas.yaml` for the full run, with `N repeats per condition`
  (3–5) at fixed decoding temperature (~0.7) — expose both as config, not hardcoded constants.

---

## 5. Storage Schema

Single wide table per completed query, append-only, Parquet partitioned by
`(model, domain, trait, trait_level)`:

```
query_id, persona_id, model, domain, trait, trait_level, phrasing_variant,
repeat_idx, timestamp, raw_response_text, parsed_titles: list[str],
matched_item_ids: list[str], hallucinated_titles: list[str],
prompt_tokens, completion_tokens, cost_usd
```

This is the single source of truth. User-side metrics, item-side metrics, and relevance
metrics are all *derived views* computed from this table — never compute a metric directly
inside the collection loop. This separation is what makes `run_analysis.py` re-runnable
without re-querying any model (important for cost control and for allowing the metric
implementations to be fixed/improved after data collection without burning more API budget).

Use `storage/io.py` to make collection **resumable**: before issuing a query, check whether
`(persona_id, model, phrasing_variant, repeat_idx)` already has a row; skip if so. This alone
prevents the most common failure mode of long API-cost pipelines (accidental re-billing on
crash-restart).

---

## 6. Model Query Layer

- `models/base_client.py` defines one abstract interface:
  ```python
  class LLMClient(Protocol):
      async def complete(self, system_prompt: str, user_prompt: str,
                          temperature: float, max_tokens: int) -> LLMResponse: ...
  ```
- Each provider client implements this and nothing else leaks provider-specific shape into
  the rest of the codebase.
- `models/registry.py` reads `config/models.yaml` (model name -> provider, endpoint, current
  model string, requests-per-minute limit) so swapping which exact model snapshot is "current
  generation" never requires touching code — only the config, per the proposal's own note that
  model names move fast.
- All clients wrap calls in exponential backoff + jitter, and log every call's token counts
  and cost via `utils/costs.py`. Enforce a **hard budget cap** read from config; the pipeline
  must halt (not just warn) if projected full-scale cost exceeds it — do this estimate at the
  end of the pilot phase, per the proposal's timeline (Week 3).

---

## 7. Metrics — Implementation Notes

Implement `metrics/user_side.py` and `metrics/item_side.py` as pure functions operating on
pandas DataFrames (input: the derived view from Section 5; output: one row per condition).
**Every metric function needs a unit test with a hand-computed toy example before it touches
real data** — these are the numbers the whole paper rests on.

- **User-side** (`user_side.py`): SNSR@K, SNSV@K (Zhang et al. 2023 definitions), PAFS@K
  (Sah et al. 2025 definition), Jaccard@K, SERP*@K, PRAG*@K. These reproduce prior published
  numbers as a pipeline sanity check (Section 7.6 step 3 of the proposal) — write a specific
  test that reruns FaiRLLM/FairEval's published setup where feasible and checks the result is
  in the right ballpark, not just that the code runs.
- **Item-side** (`item_side.py`): Gini index and HHI over aggregate per-condition exposure
  counts, ARP@K, long-tail/catalog coverage %, MGU@K and DGU@K (Jiang et al. 2024 group
  definitions, adapted from a fine-tuned-LRS setting to zero-shot prompting — note this
  adaptation explicitly in a code comment since it's a documented paradigm gap in the
  proposal).
- **Relevance control** (`relevance.py`): Precision@K/NDCG@K against each persona's fixed
  `stated_preferences`, to confirm any observed item-side shift is not simply an accuracy
  collapse.
- **Aggregation** (`aggregate.py`): pools query-level outputs into one item-exposure
  distribution per `(trait, trait_level, phrasing, model)` condition — this pooling step is
  the core novel measurement of the project; keep it as its own reviewable module, not inlined
  into a metrics function.

---

## 8. Statistical Analysis

- `stats/bootstrap.py`: resample personas with replacement to get CIs on Gini/HHI/ARP
  (aggregate metrics need persona-level resampling, not naive row-level resampling — get this
  right, it's a common bug source).
- `stats/mixed_effects.py`: trait, phrasing, model as fixed effects; persona as random effect;
  used for RQ1/RQ2. Use `statsmodels` MixedLM.
- `stats/correlation.py`: Spearman rank correlation between user-side metric rankings and
  item-side metric rankings across conditions, for RQ3. Output should directly support
  classifying the result into one of the three pre-registered scenarios from the proposal
  (Concordant / Independent / Inverse) — implement this classification as an explicit function
  with documented thresholds, not a post-hoc eyeball call.
- `stats/multiple_comparison.py`: Benjamini-Hochberg correction across the five traits and
  phrasing types.

---

## 9. Pipeline Orchestration & Milestones

Map directly to the proposal's 16-week timeline; each `pipeline/run_*.py` script should be a
thin CLI entrypoint (`typer` or `argparse`) over the modules above — no business logic lives
in the pipeline scripts themselves.

| Milestone | Script | Gate before proceeding |
|---|---|---|
| Persona/phrasing validation | `personas/semantic_check.py` | All phrasing variants pass semantic-equivalence threshold |
| Pilot | `pipeline/run_pilot.py` | One model, one domain, small persona sample; verify parsing/matching pipeline and produce a real cost-per-condition estimate |
| Full collection | `pipeline/run_collection.py` | Budget check against pilot-derived estimate passes; resumability tested via a deliberate mid-run interrupt |
| Analysis | `pipeline/run_analysis.py` | User-side metrics reproduce known published ballpark numbers (sanity check) before trusting item-side numbers |
| Mitigation (stretch) | `pipeline/run_mitigation.py` | Only run after RQ1-RQ4 results exist |

---

## 10. Coding Conventions

- Type-hint everything; run `mypy` in CI.
- No metric or statistical function may read from disk or call an API — pure functions only,
  inputs/outputs are DataFrames or plain Python objects. This is what makes them testable and
  what makes `run_analysis.py` safely re-runnable without re-collecting data.
- Every config-driven constant (N personas, N repeats, temperature, popularity-tier cutoffs,
  budget cap) lives in `config/*.yaml`, never hardcoded in `src/`.
- Log hallucination rate, cost, and token counts per condition as first-class outputs, not
  side effects — they're needed for the ethics/budget section and for interpreting results.
- Commit `data/DATA_SOURCES.md` with exact dataset versions/checksums/license notes before
  writing any loader code, so the loaders have a fixed target.

---

## 11. First Tasks for Codex (in order)

1. Scaffold the repo structure above; set up `pyproject.toml`, config loading, logging.
2. Implement `data/movielens.py` and `data/lastfm.py` loaders + `data/catalog.py` unified
   schema; write `data/DATA_SOURCES.md` with exact versions.
3. Implement `data/candidate_pool.py` and its tests.
4. Implement `personas/traits.py`, `phrasing.py`, `generator.py`, `semantic_check.py`.
5. Implement `models/base_client.py` + one concrete client (start with whichever provider has
   the simplest auth in this environment) + `registry.py`.
6. Implement `parsing/response_parser.py` + `parsing/matcher.py` with tests using synthetic
   LLM-response strings (including deliberately hallucinated titles).
7. Implement `metrics/user_side.py` and `metrics/item_side.py` with hand-computed unit tests.
8. Wire up `pipeline/run_pilot.py` end-to-end on a tiny synthetic slice before touching any
   real API budget.
9. Only after (8) passes, implement the remaining model clients, `stats/*`, and the full
   collection/analysis pipeline.
