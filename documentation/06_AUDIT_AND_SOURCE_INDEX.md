# Audit and source index

## 1. Source hierarchy

When documentation disagrees, use this order:

1. Frozen machine-readable design/configuration and bundle hashes.
2. Immutable query records and `run_manifest.json`.
3. Machine-readable audit JSON.
4. Frozen sampling/amendment documents.
5. Consolidated narrative documentation.
6. Conversational notes or temporary timing estimates.

Current collection truth is always the manifest plus actual immutable file count.

## 2. Frozen design and configuration

| Purpose | Source |
|---|---|
| Pilot v1 design | `config/persona_relevance_design_v1.yaml` |
| 100-persona parent design | `config/persona_relevance_design_v2_100.yaml` |
| Active A1 collection override | `config/full_run_v2_100_a1.yaml` |
| Model registry and digest prefixes | `config/models.yaml` |
| Frozen candidate/persona bundle | `data/relevance_labels/persona_relevance_bundle_full_v2_100_a1_frozen.json` |
| Sampling/analysis contract | `docs/SAMPLING_PLAN_V2_100.md` |
| Retry amendment | `docs/DESIGN_AMENDMENT_V2_100_A1.md` |
| Frozen sequence | `data/audits/collection_sequence_v2_100_a1.json` |

## 3. Pilot architecture and results

| Evidence | Source |
|---|---|
| Protocol-v1 failure and v2 amendment | `data/audits/pilot_protocol_amendment_v2.json` |
| Qwen/movie pilot | `data/audits/qwen_movie_pilot_closed_catalog_v2.json` |
| Qwen/music pilot | `data/audits/qwen_music_pilot_closed_catalog_v2.json` |
| Gemma/movie pilot | `data/audits/gemma_movie_pilot_closed_catalog_v2.json` |
| Gemma/music pilot | `data/audits/gemma_music_pilot_closed_catalog_v2.json` |
| Llama/movie pilot | `data/audits/llama_movie_pilot_closed_catalog_v2.json` |
| Llama/music pilot | `data/audits/llama_music_pilot_closed_catalog_v2.json` |
| Consistent provider-free v3 replay | `data/audits/pilot_regrounding_v3.json` |

## 4. Population and preflight evidence

| Evidence | Source |
|---|---|
| Population feasibility, wording, leakage | `data/audits/population_feasibility_v2_100.json` |
| Design matrix | `data/audits/design_matrix_v2_100.json` |
| Candidate pool audit | `data/audits/candidate_pools_v2_100.json` |
| Semantic phrasing | `data/audits/semantic_phrasing_v2_100.json` |
| Power/precision | `data/audits/power_precision_v2_100.json` |
| Parent Phase E preflight | `data/audits/preflight_v2_100.json` |
| Resume preflight | `data/audits/resume_preflight_v2_100.json` |
| A1 Llama/music preflight | `data/audits/preflight_v2_100_a1_llama_music.json` |

## 5. Dataset and wording evidence

| Evidence | Source |
|---|---|
| Dataset provenance/checksums/licenses | `data/DATA_SOURCES.md` |
| Blind wording audit | `data/audits/blind_wording_audit_v1.json` |
| V1 frozen labels/bundle | `data/relevance_labels/persona_relevance_bundle_pilot_v1_frozen.json` |
| V2 movie population | `data/relevance_labels/population_movies_full_v2_100_frozen.json` |
| V2 music population | `data/relevance_labels/population_music_full_v2_100_frozen.json` |
| V2 movie pools | `data/relevance_labels/candidate_pools_movies_full_v2_100_frozen.json` |
| V2 music pools | `data/relevance_labels/candidate_pools_music_full_v2_100_frozen.json` |

## 6. Confirmatory collection evidence

| Partition | Manifest/status source |
|---|---|
| Qwen/movie | `outputs/queries/design=persona-relevance-v2-100-a1/stage=full/protocol=closed-catalog-v2-a1-retry/model=ollama_qwen3_8b/domain=movie/run_manifest.json` |
| Qwen/music | `outputs/queries/design=persona-relevance-v2-100-a1/stage=full/protocol=closed-catalog-v2-a1-retry/model=ollama_qwen3_8b/domain=music/run_manifest.json` |

Future Llama and Gemma manifests will appear under the same versioned hierarchy when started.

## 7. Code ownership map

| Area | Source modules |
|---|---|
| Dataset/catalog | `src/recllm_fairness/data` |
| Persona construction | `src/recllm_fairness/personas` |
| Prompting | `src/recllm_fairness/prompting` |
| Model clients | `src/recllm_fairness/models` |
| Parsing/grounding | `src/recllm_fairness/parsing` |
| Immutable schema and manifests | `src/recllm_fairness/storage` |
| Collection/analysis orchestration | `src/recllm_fairness/pipeline` |
| User/item/relevance metrics | `src/recllm_fairness/metrics` |
| Bootstrap/mixed models/correlation | `src/recllm_fairness/stats` |
| Regression tests | `tests` |

## 8. Historical narrative sources

- `documentation.md`: earlier consolidated project overview.
- `progress.md`: chronological implementation and verification log through A1 readiness.
- `docs/FULL_RUN_PLAN_100_PERSONAS.md`: gated Phase A-H execution plan.
- `docs/EXPERIMENT_PROTOCOL.md`: reproducible experimental protocol.
- `docs/WORKSTATION_MIGRATION.md`: workstation and external-drive procedure.
- `docs/METRICS.md`: mathematical metric definitions.
- `research_proposal_recllm_item_side_fairness (1).md`: research motivation and proposal.

These are retained for history. This folder reorganizes them but does not replace the frozen
machine-readable evidence.
