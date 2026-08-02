# Project progress

Last updated: 2026-08-01

## Engineering status

- [x] Read the research proposal and engineering brief.
- [x] Scaffold the package, configuration, outputs, CI, and locked `uv` environment.
- [x] Record publisher URLs, versions, checksums, citations, and license restrictions.
- [x] Implement MovieLens 1M/25M and LastFM-1K/360K artist-level loaders.
- [x] Implement deterministic, preference-aware stratified candidate pools, closed-catalog
  prompting, coded entries, deterministic order shuffling, and full-catalog grounding.
- [x] Implement IPIP-style Big-Five markers, counterfactual persona controls, four phrasing
  variants, and the pre-spend semantic-equivalence gate.
- [x] Implement mock, Ollama, OpenAI, Anthropic, Google, and Hugging Face clients behind one
  protocol, including retry/backoff, rate limiting, immutable model snapshots, and hard cost
  limits.
- [x] Implement conservative parsing; separate hallucinated and catalog-valid/off-list titles.
- [x] Implement append-only, partitioned Parquet storage and exact-key resumability.
- [x] Implement Jaccard, reference-compatible SERP*/PRAG*, SNSR, SNSV, and PAFS.
- [x] Implement Gini/HHI/ARP/coverage, popularity/genre MGU/DGU, group shares, neutral deltas,
  and relevance controls.
- [x] Implement persona and paired persona bootstrap intervals, mixed-effects models,
  Benjamini-Hochberg correction, Spearman comparison, and explicit RQ3 scenarios.
- [x] Implement synthetic pilot, scientific pilot/full collection, analysis, and guarded
  mitigation entrypoints.
- [x] Document the metric contract, experiment protocol, ethics/reporting constraints, and
  software citation metadata.

## Verification status

- [x] Dependency lock is current: 90 resolved packages.
- [x] Unit/integration suite: 32 tests passed.
- [x] Lint: zero findings.
- [x] Strict typing: zero issues across 54 source files.
- [x] No-cost end-to-end pilot: 120 query records and 12 derived analysis tables.
- [x] Resumability replay: zero duplicate calls and exactly 120 records retained.
- [x] Standalone analysis replay: completed from Parquet without importing/calling a provider.
- [x] FaiRLLM metric normalization cross-checked against the authors' public notebook.

## Study execution gates (require researcher inputs or budget)

- [x] Download all four raw datasets and independently verify their MD5 checksums.
- [x] Freeze structured base-persona preferences and independent `relevant_item_ids` after
  automated construction, independent blind wording review, and the cooling-off review.
- [x] Select and verify three accessible immutable local model snapshots in
  `config/models.yaml`; local inference price is USD 0 and no API credentials are needed.
- [x] Run the sentence-transformer phrasing gate and no-cost technical compatibility check.
- [ ] Run the scientific pilot for every model/domain pair; inspect repeated-query parse yield,
  hallucination/off-list rates, relevance, run time, and projected full-collection duration.
  Both Qwen domains and Gemma/movie have passed under `closed-catalog-v2`; three model/domain
  pairs remain.
- [ ] Run full collection only after every matching pilot passes the hard budget gate.
- [ ] Perform confirmatory analysis, diagnose model convergence, and freeze result tables.
- [ ] Run mitigation only after RQ1-RQ4 results are reviewed.
- [ ] Add journal-specific manuscript, figures, author metadata, archival repository URL/DOI,
  and venue checklist before submission.

## Decisions and known limitations

- Music exposure is measured at artist level in both LastFM releases because LastFM-360K is
  user-artist-play data; LastFM-1K events are aggregated to the same unit.
- Zero-exposure items remain in Gini/HHI denominators. Removing them would understate catalog
  concentration.
- Jiang et al.'s MGU/DGU historical-share reference is adapted to fixed candidate-pool
  opportunity in the primary zero-shot analysis. Historical-reference sensitivity analysis
  should be added when defensible persona histories exist.
- The software smoke pilot is not a scientific result. Existing pilot rows predate relevance
  labels, so their relevance output is intentionally missing; the tested current schema stores
  fixed labels for all future scientific records.
- Dataset files, embedding model weights, API credentials, and scientific collection responses
  are not committed. The small local technical-compatibility record is retained as an audit
  artifact. Licensing/provider terms must be checked before archiving scientific raw responses.
- The frozen persona design uses exactly 11 framings per base preference: ten Big-Five
  poles and one shared no-personality neutral condition. With four wording variants this is
  264 conditions per domain before stochastic repeats and model multiplication.
- The proposed LastFM cosine threshold of 0.1 was rejected before any real model output was
  collected because it produced 4,887–5,183 relevant artists. A documented pre-results grid
  selected 0.5, producing 33–381 relevant artists across S1–S6.
- The frozen combined persona/relevance artifact SHA256 is
  `4604a8a3d247e3f43249424bf1d94b64b58445b20a97af9985b3390ffc348178`.
- The independent wording survey contained 34 responses and 340 classifications. Aggregate
  accuracy was 86.2%; item-level accuracy ranged from 76.5% to 94.1%. Because no numeric pass
  threshold was specified in advance, this is recorded transparently as support for the
  qualitative “reliably distinguishable” criterion rather than a post-hoc confirmatory test.
- The raw survey workbook contains optional respondent names and is explicitly gitignored. The
  committed research record should use only the de-identified aggregate JSON audit.
- Six Ollama models are locally available. The frozen primary comparison models are
  `qwen3:8b` (`500a1f067a9f`), `gemma3:12b` (`f4031aab637d`), and `llama3.1:8b`
  (`46e0c10c039e`). The client verifies the full installed digest before each run, uses one
  concurrent request, a 2,048-token context, and explicit model unloading for this machine.
- The technical compatibility check passed for all three models with zero hallucinated or
  off-list titles. Parse yield was 9/10 for Qwen and 10/10 for Gemma and Llama in this single
  stochastic smoke query. This is not a scientific result; repeated-query rates remain a pilot
  gate.
- The first 264-record Qwen/movie pilot is retained as protocol-v1 diagnostic evidence but is
  excluded from scientific results. It exposed a global-pool relevance imbalance (only 3–26
  relevant items per preference), 295 hallucinated titles, and 116 catalog-valid/off-list
  titles. No fairness hypothesis results were inspected before amending the protocol.
- `closed-catalog-v2` fixes one 120-item pool per base preference, guarantees at least 30
  independently relevant items where available, preserves the 50/25/25 popularity-tier mix,
  shuffles display order deterministically, uses coded `C### | title` entries, and versions the
  output path so protocol-v1 records cannot be silently reused.
- A six-preference Qwen technical check of protocol-v2 matched 58/60 requested items with zero
  hallucinated or off-list titles and preceded the successful full 264-query corrected pilot.
- The corrected Qwen/movie scientific pilot passed: 264 unique records, all responses with at
  least 8 matched items, 250/264 with exactly 10, no off-list titles, mean Precision@10 0.5784,
  mean NDCG@10 0.6551, zero cost, and 35.8 minutes elapsed. Four conservative fuzzy-title flags
  (0.15% of requested exposure) all carried valid candidate codes and remain excluded in the
  immutable stored matches.
- Provider-free analysis replay produced all 12 tables. A neutral-baseline grouping bug found
  because the paired delta-bootstrap table was empty was fixed and regression-tested; the table
  now has all 120 expected rows. User-side mixed models converged. Item-outcome mixed models did
  not converge with only six pilot personas, so full-scale convergence remains a gate.
- The six-preference Qwen/music protocol-v2 check matched 60/60 items with zero hallucinated or
  off-list titles, clearing the way for the Qwen/music scientific pilot.
- The Qwen/music scientific pilot passed: 264 unique records, all responses with at least 9
  matched artists, 251/264 with exactly 10, mean Precision@10 0.6152, mean NDCG@10 0.6397,
  zero cost, and 57.4 minutes elapsed. Twelve conservative duplicate-artist-name flags (0.45%
  of requested exposure) carried valid candidate codes and remain excluded from stored matches.
- Qwen/music analysis produced all 12 tables and all 120 paired delta-bootstrap intervals.
  Six pilot RQ3 correlations were undefined because an input rank was constant, and the three
  item-outcome mixed models did not converge with six base personas; these are pilot sample-size
  limitations, not paper findings.
- Gemma/movie passed its six-preference protocol-v2 preflight with 60/60 matches and zero
  hallucinated/off-list titles. The 195.7-second preflight projects roughly 2.4 hours for 264
  queries before allowing for longer responses and loading overhead.
- The Gemma/movie scientific pilot passed: 264 unique records, 261/264 responses with exactly
  10 matched movies, zero hallucinated/off-list titles, mean Precision@10 0.7678, mean NDCG@10
  0.7945, zero cost, and 113.3 minutes elapsed. Analysis produced all 12 tables, 120 paired
  delta-bootstrap intervals, and 27/27 defined pilot RQ3 correlations.
- Gemma/music preflight grounded 59/60 artist entries with zero off-list output. The sole flag
  was the already documented LastFM duplicate collaboration name attached to a valid candidate
  code, so the domain is cleared with that conservative-matcher caveat.

## Verification log

| Date | Check | Result |
|---|---|---|
| 2026-07-31 | Proposal and `AGENTS.md` reviewed | Passed |
| 2026-07-31 | Publisher provenance/checksum record | Passed |
| 2026-07-31 | `uv lock --check` | 90 packages resolved |
| 2026-07-31 | `pytest` | 23 passed |
| 2026-07-31 | `ruff check .` | Passed |
| 2026-07-31 | `mypy src` (strict) | 50 files passed |
| 2026-07-31 | Synthetic pilot and analysis replay | Passed |
| 2026-07-31 | Resumability replay | 120 before / 120 after |
| 2026-07-31 | MovieLens 1M archive MD5 | `c4d9eecfca2ab87c1945afe126590906` — Passed |
| 2026-07-31 | MovieLens 25M archive MD5 | `6b51fb2759a8657d3bfcbfc42b592ada` — Passed |
| 2026-07-31 | LastFM-1K archive MD5 | `a79a6808f54f73354789a9fb02cb1e41` — Passed |
| 2026-07-31 | LastFM-360K archive MD5 | `635e6ed3fc873aa4ba33aba0ebce02b1` — Passed |
| 2026-07-31 | Real pilot dataset loader validation | MovieLens 1M: 3,706 items; LastFM-1K: 176,694 artists — Passed |
| 2026-07-31 | Trait framing length parity (≤3 words per pole pair) | Passed |
| 2026-07-31 | Movie pilot relevance labels (M1–M6) | 69–669 items; Passed |
| 2026-07-31 | Music seed minimum (≥30 listeners) | 149–710 listeners per seed; Passed |
| 2026-07-31 | Music relevance threshold sensitivity | 0.5 selected before model collection; 33–381 items; Passed |
| 2026-07-31 | Shared-neutral condition matrix | 6 × 11 × 4 = 264 conditions/domain; Passed |
| 2026-07-31 | Semantic phrasing gate | Movie minimum 0.8380; music minimum 0.8671; threshold 0.82 — Passed |
| 2026-08-01 | Draft audit bundle SHA256 | `8a0151b6b6b3f84d0411acc655361dc1066e2abb3d6e8edad076ad3e353c8ee5` |
| 2026-07-31 | Updated unit/integration suite | 27 passed |
| 2026-07-31 | Updated lint and strict typing | Passed; 52 source files |
| 2026-08-01 | Independent blind wording audit | 34 responses; 293/340 correct (86.2%); item range 76.5%–94.1% — Passed with documented caveat |
| 2026-08-01 | Survey privacy control | Raw named workbook gitignored; aggregate-only audit saved |
| 2026-08-01 | Local Ollama inventory | Llama 3.1 8B, Qwen 3/3.5, Gemma 3 12B, DeepSeek-R1 8B, and Qwen 2.5 Coder available; exact digests recorded |
| 2026-08-01 | Cooling-off design review | Passed; no wording changes required |
| 2026-08-01 | Final semantic phrasing gate | Movie minimum 0.8719; music minimum 0.8827; threshold 0.82 — Passed |
| 2026-08-01 | Frozen audit bundle SHA256 | `4604a8a3d247e3f43249424bf1d94b64b58445b20a97af9985b3390ffc348178` |
| 2026-08-01 | Ollama technical compatibility | Qwen 9/10, Gemma 10/10, Llama 10/10; zero hallucinated/off-list titles — Passed |
| 2026-08-01 | Final unit/integration suite | 30 passed |
| 2026-08-01 | Final lint and strict typing | Passed; 54 source files |
| 2026-08-01 | Qwen/movie protocol-v1 pilot | 264/264 immutable records; failed grounding gate and excluded from scientific results |
| 2026-08-01 | Protocol-v2 candidate opportunity | M1–M6 contain 30–36 relevant items; 50/25/25 tier mix retained — Passed |
| 2026-08-01 | Protocol-v2 semantic phrasing gate | Movie minimum 0.8834; music minimum 0.9033; threshold 0.82 — Passed |
| 2026-08-01 | Protocol-v2 Qwen six-preference check | 58/60 matched; zero hallucinated/off-list titles — Passed |
| 2026-08-01 | Qwen/movie protocol-v2 pilot | 264/264 unique; mean 9.936/10 matched; 0 off-list; 4 conservative flags — Passed |
| 2026-08-01 | Qwen/movie analysis replay | 12 tables; paired bootstrap 120 rows; user-side models converged — Passed with item-model pilot caveat |
| 2026-08-01 | Qwen/music six-preference check | 60/60 matched; zero hallucinated/off-list titles — Passed |
| 2026-08-01 | Protocol-v2 verification suite | 32 tests; lint and strict typing passed |
| 2026-08-02 | Qwen/music protocol-v2 pilot | 264/264 unique; mean 9.958/10 matched; 12 conservative duplicate-name flags — Passed |
| 2026-08-02 | Qwen/music analysis replay | 12 tables; paired bootstrap 120 rows — Passed with pilot sample-size caveats |
| 2026-08-02 | Gemma/movie six-preference check | 60/60 matched; zero hallucinated/off-list titles; 195.7 seconds — Passed |
| 2026-08-02 | Gemma/movie protocol-v2 pilot | 264/264 unique; mean 9.989/10 matched; zero hallucinated/off-list — Passed |
| 2026-08-02 | Gemma/movie analysis replay | 12 tables; paired bootstrap 120 rows; 27/27 RQ3 correlations defined — Passed with item-model pilot caveat |
| 2026-08-02 | Gemma/music six-preference check | 59/60 matched; one known valid-code duplicate-name flag; zero off-list — Passed with documented caveat |
