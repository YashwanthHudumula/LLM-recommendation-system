# Full project report: architecture, collection, results, and confirmatory findings

**Report date:** 2026-08-15
**Project:** Item-Side Exposure Fairness in Personality-Conditioned RecLLMs
**Frozen design:** `persona-relevance-v2-100-a1`
**Collection protocol:** `closed-catalog-v2-a1-retry`
**Analysis version:** `confirmatory-analysis-v1`
**Final collection:** 79,200/79,200 immutable records (100%)

## 1. Executive summary

This project studies whether personality-conditioned prompts change not only an individual
user's recommendation list, but also the aggregate exposure received by items in an LLM-based
recommender. It audits three frozen local model snapshots—Qwen3 8B, Llama 3.1 8B, and Gemma3
12B—across movies and music. The experiment is inference-only: no model was trained or
fine-tuned.

The project completed six pilots, designed and audited 100 independent personas per domain,
collected all six confirmatory model/domain partitions, exhaustively verified the final
Gemma/music partition, and ran the registered provider-free confirmatory analysis for both
domains. Each domain analysis contains 39,600 records; the total collection contains 79,200.

The central empirical result is that personality prompting changes both individual lists and
aggregate item exposure, but the relationship is model- and domain-dependent. Music mostly
shows a concordant relationship between user-list harm and item-side harm. Movies are more
heterogeneous: Qwen/movie shows strong inverse RQ3 patterns, Llama/movie mixes concordant and
inverse patterns, and Gemma/movie is mostly independent after multiplicity correction. This
means a user-side fairness audit is not a universally reliable proxy for item-side exposure
fairness.

Gemma provides the highest average relevance in both domains. Llama provides the broadest catalog
and long-tail coverage, but it also has substantially less stable personality-conditioned lists
and a registered variable-list-length limitation. Qwen is generally intermediate in relevance
and list stability, but its movie RQ3 results show the clearest inverse user/item relationship.

These results are strong enough to support manuscript development, but they are not yet a
submission-ready Q1 paper. Required remaining work includes sensitivity replays, residual and
singular-fit diagnostics, durable archiving/checksums of analysis tables, manuscript figures,
related-work verification, and careful effect-size interpretation against the frozen SESOI.

## 2. Research problem and contribution

Prior RecLLM fairness work largely asks whether revealing a user attribute changes that user's
recommendation list. This project adds the complementary catalog-level question: when the same
personality framing is applied across a population, do many individually plausible shifts
accumulate into unequal exposure for items, popularity groups, genres, or providers?

The project addresses five research questions:

1. Does aggregate item exposure shift relative to a paired neutral prompt?
2. Do Big Five trait conditions change popularity-tier or category exposure?
3. Are user-side and item-side fairness harms concordant, independent, or inverse?
4. Are patterns consistent across model families and domains?
5. Can an inference-time mitigation reduce disparity without materially reducing relevance?

RQ1–RQ4 are now supported by collected and analyzed data. RQ5 remains a deliberately separate
stretch phase and has not been run.

The principal contribution is a controlled, reproducible, zero-shot audit combining individual
list stability, aggregate exposure equality, and utility controls under one frozen design. It
tests whether small personality-conditioned changes that look acceptable at the individual level
can compound into catalog-level allocation differences.

## 3. Architecture evolution

### 3.1 Original architecture

The original system separated the workflow into:

```text
raw datasets
  -> domain loaders and unified item catalog
  -> personas and fixed preferences
  -> prompt construction
  -> provider-independent LLM client
  -> response parsing and catalog matching
  -> append-only Parquet records
  -> provider-free metrics and statistical analysis
```

Important original principles were fixed preferences across counterfactual conditions,
domain-independent item schemas, provider abstraction, deterministic seeding, immutable records,
resume support, pure metric functions, and strict separation between collection and analysis.

The first scientific pilot design, `persona-relevance-v1`, used six hand-specified preferences
per domain. Each preference was crossed with ten Big Five poles, one neutral framing, and four
phrasing variants, giving 264 records per model/domain pilot.

### 3.2 Why protocol v1 was rejected

The first Qwen/movie diagnostic used a global candidate pool. It achieved only 8.3258 matched
items per requested top-10 list, with 34.85% exact-10 output, 295 hallucinated titles, and 116
catalog-valid but off-list titles. Relevant opportunity also varied greatly across the six
preferences. No fairness result was inspected. These records are retained as engineering
evidence but excluded from scientific inference.

### 3.3 Closed-catalog-v2 architecture

The revised protocol introduced one deterministic 120-item candidate pool per persona:

- 60 head items;
- 30 mid-popularity items;
- 30 tail items;
- at least 30 independently relevant candidates;
- an identical pool across all trait and phrasing counterfactuals;
- deterministic display-order randomization;
- coded `C### | exact title` entries; and
- an explicit instruction to recommend only displayed candidates.

The parser and matcher distinguish grounded candidates, non-catalog hallucinations, and
catalog-valid off-list outputs. Invalid outputs remain visible as diagnostics but are excluded
from exposure aggregation.

### 3.4 Provider-free grounding corrections

Immutable pilot responses revealed two software issues: duplicate LastFM artist names could
resolve outside the permitted pool, and Llama often appended annotations after valid titles.
The final derived grounding version, `allowed-title-annotation-v3`, gives priority to exact
allowed titles and accepts annotations only after an explicit delimiter. It does not accept
invalid codes, truncated titles, code/title mismatches, or replacement lines. Raw records were
never modified and no model was recalled for re-grounding.

### 3.5 Confirmatory v2-100 architecture

The confirmatory design replaced the six pilot preferences with 100 independently constructed
personas in each domain. Profiles were sampled without replacement and stratified using activity,
popularity tendency, and diversity. Preference construction and relevance evaluation use
disjoint data splits. Raw source-user identifiers are not placed in prompts or public outputs.

Each persona has a deterministic 120-item candidate pool held constant across all
counterfactuals. The full crossed matrix is:

| Dimension | Count |
|---|---:|
| Personas per domain | 100 |
| Personality framings | 11: ten Big Five poles plus neutral |
| Phrasing variants | 4 |
| Stochastic repeats | 3 |
| Records per persona/model/domain | 132 |
| Records per model/domain | 13,200 |
| Records per domain | 39,600 |
| Total records | 79,200 |

Every version-2 record carries design, bundle, dataset, and protocol provenance. Resume identity
includes the full experimental identity. Run manifests preserve deterministic query order,
lockfile hash, model digest, workstation metadata, and every attempt boundary.

### 3.6 A1 deterministic retry architecture

The parent v2 preflight found that Llama/music returned at least ten grounded items for only
11/14 queries. Before confirmatory output was inspected, amendment A1 added exactly one
format-only retry when the first attempt grounds fewer than ten items. The first attempt remains
at temperature 0.7; the retry uses temperature 0.0 and the same persona, candidate list, item
order, and trait wording. It cannot be triggered by relevance, fairness, taste, or item identity.
The second attempt is final even if still short. Both attempts and temperatures are preserved.

## 4. Data and population controls

| Use | Dataset | Frozen checksum |
|---|---|---|
| Pilot movies | MovieLens 1M | MD5 `c4d9eecfca2ab87c1945afe126590906` |
| Full movies | MovieLens 25M | MD5 `6b51fb2759a8657d3bfcbfc42b592ada` |
| Pilot music/persona construction | LastFM-1K | MD5 `a79a6808f54f73354789a9fb02cb1e41` |
| Full music | LastFM-360K | MD5 `635e6ed3fc873aa4ba33aba0ebce02b1` |

Movie popularity is rating-count rank; music popularity is play-count rank. Movie preferences
use construction-split genres and decades, with held-out positive ratings for relevance. Music
preferences use construction-split top artists, with held-out artists for relevance. All 200
profile statements passed human wording review without personality leakage, hidden controls, or
raw user fields.

The semantic phrasing gate used `all-MiniLM-L6-v2` at cosine threshold 0.82. Minimum observed
similarity was 0.8834 for movies and 0.9033 for music. Thus formal, casual, direct, and indirect
variants passed the frozen equivalence gate.

## 5. Models, workstation, and reproducibility

| Model key | Snapshot | Frozen digest |
|---|---|---|
| `ollama_qwen3_8b` | `qwen3:8b` | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| `ollama_llama3_1_8b` | `llama3.1:8b` | `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e` |
| `ollama_gemma3_12b` | `gemma3:12b` | `f4031aab637d1ffa37b42570452ae0e4fad0314754d17ded67322e4b95836f8a` |

Inference used Ollama locally with concurrency one, context length 2,048, `think: false`, and
temperature 0.7 before any underlength retry. Monetary inference cost was USD 0.

The workstation was Windows 11 host `C334-0021`, NVIDIA RTX 2000 Ada with 16,380 MiB VRAM,
32 GB DDR5 RAM, Python 3.12.5, and Ollama 0.32.5 at qualification. The environment is pinned by
`uv.lock`, whose recorded SHA256 is
`99687297f3fad09232d43cde627f589eede5eea8e879e18be50c5e94ccc22a51`.

The codebase separates datasets, personas, prompting, model clients, parsing, immutable storage,
metrics, statistics, and orchestration. Collection records are atomic append-only Parquet files.
Analysis imports no provider client and re-grounds from stored raw responses.

## 6. Six scientific pilots

Each pilot used six preferences, 11 framings, and four phrasings: 264 records and 44 condition
cells per model/domain. Pilot outputs established feasibility and software behavior, not
confirmatory fairness effects.

| Model/domain | Records | Effective grounding | Precision@10 | NDCG@10 | Runtime | Decision |
|---|---:|---:|---:|---:|---:|---|
| Qwen/movie | 264 | 99.43% top-10 yield | 0.5784 | 0.6551 | 35.8 min | Passed |
| Qwen/music | 264 | 100.00% top-10 yield | 0.6152 | 0.6397 | 57.4 min | Passed |
| Gemma/movie | 264 | 99.89% top-10 yield | 0.7678 | 0.7945 | 113.3 min | Passed |
| Gemma/music | 264 | 100.00% top-10 yield | 0.7402 | 0.7186 | 129.1 min | Passed after re-grounding |
| Llama/movie | 264 | 97.39% top-10 yield | 0.5133 | 0.5733 | 26.1 min | Passed with length caveat |
| Llama/music | 264 | 97.88% top-10 yield | 0.5735 | 0.5924 | 30.3 min | Passed with length caveat |

The consistent v3 replay left two Qwen/movie hallucination flags, one Llama/movie flag, and four
hallucination plus two off-list flags for Llama/music. Other pilot partitions had zero remaining
bad-title flags. Six personas were insufficient for confirmatory aggregate inference; pilot
correlations and mixed-model fits remain diagnostic only.

## 7. Confirmatory collection completion and quality

All six partitions contain exactly 13,200 records and every manifest is `completed`. Total active
collection time across completed attempts was approximately 99.74 hours. Safe interruptions are
retained as provenance and did not create duplicates or overwrite records.

| Partition | Exact-10 | Effective top-10 | Bad-title incidence | Retries | Active hours | Decision |
|---|---:|---:|---:|---:|---:|---|
| Qwen/movie | 95.4394% | Operational gate passed | 0.6101% | 1,303 (9.8712%) | 17.16 | Passed |
| Qwen/music | 99.8485% | Near-complete | 0.0015% | 343 (2.5985%) | 12.93 | Passed |
| Llama/movie | 74.3409% | 99.4621% | 0.0760% | 2,455 (18.5985%) | 13.51 | Passed with registered length caveat |
| Llama/music | 80.3030% | 99.8598% | 0.0369% | 1,233 (9.3409%) | 11.94 | Passed with registered length caveat |
| Gemma/movie | 99.1742% | 99.9174% | 0.0826% | 207 (1.5682%) | 24.07 | Passed |
| Gemma/music | 100.0000% | 100.0000% | 0.0000% | 65 (0.4924%) | 20.13 | Passed |

Across partitions there were 5,606 format retries. The Llama exact-10 threshold is not met and
must never be described as met. Its registered handling truncates overlong lists at rank ten and
leaves short lists short. Effective exposure yield passes the operational threshold.

### Final Gemma/music audit

Gemma/music has 13,200 manifest IDs, 13,200 readable Parquet files, 13,200 unique query IDs, and
zero duplicate experimental identities. All 11 trait/level cells contain 1,200 records. Every
record contains exactly ten grounded candidates: 132,000 parsed titles and 132,000 matches, with
zero hallucinated, off-list, duplicate-matched, or matched-outside-pool items. There are zero
selected-attempt errors, raw/selected mismatches, provenance mismatches, or negative-token rows.
The completed manifest SHA256 is
`59905a7ddb32d1c7d5c997da9ab9fb5231ab9698ec3c5a117f82a14600029f6f`.

## 8. Frozen analysis contract

The primary user-side outcome is Jaccard harm, `1 - Jaccard@10`, against a paired neutral list.
SERP and PRAG harm, SNSR/SNSV, and PAFS are secondary views. Item-side outcomes include exposure
Gini, HHI, ARP@10, catalog coverage, long-tail coverage, and popularity/genre MGU and DGU.
Precision@10 and NDCG@10 are utility controls.

Primary exposure uses grounded ranks 1–10 without imputation. Aggregate item metrics and
trait-minus-neutral deltas use 2,000 persona-cluster bootstrap resamples and 95% intervals.
Mixed models use trait, level, phrasing, and model fixed effects with a persona random intercept.
Benjamini–Hochberg correction is applied at q=0.05 within registered families.

RQ3 orients metrics as harms and classifies Spearman results as concordant when rho is at least
0.20 with adjusted p below 0.05, inverse when rho is at most -0.20 with adjusted p below 0.05,
and independent otherwise. Constant-input correlations remain undefined.

Both completed analysis manifests contain 39,600 records and all three frozen models. Because
inherited Windows ACLs prevented new project output directories, the 26 generated tables were
archived as `recllm_movie_*` and `recllm_music_*` files under:

`C:\Users\yahu25\.codex\visualizations\2026\08\03\019fc76d-e4b9-72c2-97b1-00da6f09b6c0`

This is a storage relocation only. Source records, calculations, seeds, resample counts, and
analysis identities are unchanged.

## 9. Confirmatory descriptive results

The table reports averages across the 40 non-neutral trait/level/phrasing cells per model.
Jaccard, SERP, and PRAG are similarities: lower values mean greater personality-induced change.
Coverage is against the complete domain catalog, so absolute percentages are expected to be
small; cross-model and condition deltas are more interpretable than the absolute level.

### Movies

| Model | Precision@10 | NDCG@10 | Jaccard | SERP | PRAG | Gini | HHI | ARP | Catalog coverage | Tail coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma3 12B | 0.4905 | 0.5266 | 0.5060 | 0.2091 | 0.6981 | 0.998444 | 0.016949 | 44,443.5 | 0.4949% | 0.0799% |
| Llama 3.1 8B | 0.3332 | 0.3604 | 0.2053 | 0.1099 | 0.3733 | 0.997966 | 0.012743 | 35,500.8 | 0.6567% | 0.2219% |
| Qwen3 8B | 0.4073 | 0.4791 | 0.5040 | 0.1999 | 0.6910 | 0.998827 | 0.020472 | 44,102.6 | 0.4072% | 0.1242% |

### Music

| Model | Precision@10 | NDCG@10 | Jaccard | SERP | PRAG | Gini | HHI | ARP | Catalog coverage | Tail coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma3 12B | 0.4628 | 0.4775 | 0.4192 | 0.1812 | 0.6036 | 0.999031 | 0.009451 | 6,030,019.4 | 0.2343% | 0.0696% |
| Llama 3.1 8B | 0.3374 | 0.3622 | 0.1537 | 0.0855 | 0.2941 | 0.998809 | 0.006831 | 4,925,094.3 | 0.3102% | 0.1252% |
| Qwen3 8B | 0.3444 | 0.3814 | 0.3589 | 0.1612 | 0.5492 | 0.999239 | 0.010079 | 5,744,837.4 | 0.1987% | 0.0827% |

## 10. Key findings

### 10.1 Personality conditioning changes item exposure

Of 360 registered bootstrap contrasts for Gini, HHI, and ARP in each domain, 104 movie
intervals and 155 music intervals excluded zero. The affected conditions span all three models,
multiple traits, both high and low poles, and multiple phrasings. This is direct evidence for
RQ1: aggregate exposure can shift when only personality wording changes while preferences and
candidate opportunity remain fixed.

Music shows particularly consistent positive concentration shifts for Gemma. For several
Gemma/music conditions—especially low agreeableness, high conscientiousness, high neuroticism,
and both openness poles—Gini and HHI deltas are positive across all four phrasings. Movie shifts
are more mixed in sign and more dependent on model, trait, and phrasing.

These patterns describe model behavior under the frozen prompts and catalogs. They must not be
interpreted as factual relationships between human personality and cultural preference.

### 10.2 Model choice creates a relevance–coverage trade-off

Gemma has the best average utility in both domains: movie Precision/NDCG of 0.4905/0.5266 and
music Precision/NDCG of 0.4628/0.4775. Qwen is second for movies and slightly exceeds Llama on
music NDCG. Llama has the lowest average utility.

Llama nevertheless exposes a broader and more tail-oriented set of items. It has the lowest
average Gini and HHI, highest catalog coverage, and highest long-tail coverage in both domains.
The result is not that one model is universally best: Gemma leads on relevance, while Llama
leads on exposure breadth. Qwen tends to have the highest concentration and lowest coverage,
especially in music.

### 10.3 Llama is most sensitive at the individual-list level

Llama's mean Jaccard similarity is 0.2053 for movies and 0.1537 for music, far below Gemma and
Qwen. The mixed-model coefficient for Llama relative to the Gemma reference is approximately
+0.3007 Jaccard harm in movies and +0.2655 in music, with corrected significance. Comparable
large effects appear for SERP and PRAG harm. Personality wording therefore changes Llama's
ranked lists much more strongly, even though its aggregate catalog exposure is broader.

Gemma and Qwen have similar movie Jaccard similarity near 0.50. In music Gemma is more stable
than Qwen (0.4192 versus 0.3589).

### 10.4 Extraversion and openness are the strongest recurring trait effects

Across both domains and all three user-side harm outcomes, extraversion and openness have large,
corrected associations relative to the agreeableness reference. Neuroticism is also significant
for all three user-side harms in music. Low trait poles increase harm relative to high poles in
both domains. Formal phrasing generally reduces harm; direct and indirect wording have smaller
domain-dependent effects.

Item-side mixed models in movies show that extraversion lowers ARP and increases tail share,
while openness reduces head share and increases tail share. Model effects are larger than most
trait coefficients: relative to Gemma, Llama substantially lowers ARP and head share and raises
tail share. These coefficients are statistically strong, but their scientific importance must
still be judged against the frozen 0.20-SD SESOI using standardized effect reporting.

### 10.5 RQ3 differs sharply by domain and model

Movies do not support one universal user/item relationship:

- Gemma/movie has one corrected concordant result, PRAG harm versus HHI; the remaining 26
  combinations are not corrected-significant.
- Llama/movie has four corrected concordant and three corrected inverse relationships.
- Qwen/movie has 18 corrected inverse relationships. Correlations are strongest for user harm
  against ARP, catalog coverage, Gini, long-tail coverage, and popularity MGU/DGU; absolute rho
  values reach approximately 0.74.

Music is predominantly concordant:

- Gemma/music has 15 corrected concordant relationships.
- Llama/music has six corrected concordant relationships.
- Qwen/music has 11 corrected concordant relationships.
- No music inverse relationship survives correction.
- Six correlations per model are undefined because music genre outcomes are constant: the
  primary LastFM analysis deliberately does not fabricate missing genre metadata.

The main RQ3 conclusion is therefore conditional rather than universal. User-side audits can be
informative proxies in some model/domain settings—especially music—but can be independent or
move inversely to item-side harm in others, most clearly Qwen/movie. A paper should emphasize
this domain/model interaction instead of claiming a single global scenario.

### 10.6 Prompt phrasing is not a harmless presentation detail

Formal wording reduces all three movie user-side harms and reduces Jaccard and PRAG harm in
music. Direct and indirect phrasing have smaller but sometimes corrected associations. Movie
item outcomes also vary with phrasing: direct/formal phrasing lowers query-level ARP, direct
wording lowers head share, and formal wording lowers tail share in the fitted model. Prompt
templates should therefore be treated as experimental factors, not interchangeable wrappers.

## 11. Statistical and methodological cautions

1. Several mixed-effects fits report singular random-effects covariance, boundary estimates,
   and non-positive-definite Hessians. A `converged=True` flag does not remove these warnings.
   Coefficients must be validated with alternative random-effects specifications, cluster-robust
   models, or persona-level aggregation before manuscript claims are finalized.
2. The music output contains only the 39 user-side mixed-effect rows; item-side music mixed
   models were not produced. This is an unresolved analysis limitation, not evidence of no
   item-side effect. Bootstrap deltas remain available, but the missing fits require diagnosis.
3. Music genre MGU/DGU are zero because the frozen primary LastFM catalog does not silently
   enrich missing genre/provider metadata. Corresponding RQ3 correlations are undefined.
4. Gini values near one and low absolute catalog coverage partly reflect calculation against
   very large full catalogs while each persona sees a fixed 120-item opportunity set. Report
   trait-minus-neutral deltas and within-opportunity sensitivity metrics alongside absolute
   values.
5. Llama's literal exact-10 rates are below the generic gate. The registered first-10 handling
   is defensible and yields near-complete exposure, but exact-10-only sensitivity analysis is
   essential.
6. Repeats estimate decoding variability and are not independent personas. All uncertainty must
   remain clustered at persona level.
7. The current tables are analysis outputs, not yet a frozen manuscript package. Residual checks,
   standardized effect sizes, sensitivity views, and independent reproduction remain pending.

## 12. Ethics, privacy, and interpretation

All personas are synthetic representations derived from public interaction datasets; raw user
identifiers are separated from prompt IDs and should not be released. Construction and
evaluation splits prevent preference/relevance leakage. Personality markers are audit stimuli,
not clinical assessments.

The object of inference is the behavior of three specific model snapshots under specific frozen
prompts, datasets, catalogs, and dates. Results must not be generalized to all LLMs, providers,
future snapshots, or real personality groups. Apparent trait–item associations may reflect
pretraining stereotypes, prompt semantics, decoding behavior, or catalog opportunity; they do
not establish psychological truth.

## 13. Publication assessment

The project now has a credible empirical core for a strong paper: a prespecified gap, controlled
counterfactual design, 100 independent personas per domain, two domains, three frozen models,
79,200 immutable records, paired neutral baselines, utility controls, provider-free replay,
cluster bootstrap inference, and cross-metric RQ3 tests.

The most publishable findings are the domain-dependent RQ3 reversal, the relevance–coverage
trade-off across models, and the evidence that prompt phrasing and personality poles alter
aggregate exposure despite fixed candidate opportunity.

It should not yet be described as Q1-ready. Before submission:

1. resolve or transparently replace singular mixed-effect fits;
2. diagnose and restore the missing music item-side models;
3. run registered exact-10 and flagged-entry sensitivity analyses;
4. add within-candidate-opportunity coverage/concentration sensitivity metrics;
5. standardize coefficients and compare them with the 0.20-SD SESOI;
6. freeze table/figure hashes and create an independent backup;
7. verify all related-work claims and bibliography entries against primary sources;
8. produce manuscript figures and a complete methods/results appendix; and
9. optionally preregister and run RQ5 mitigation as a separately versioned experiment.

## 14. Immediate next steps

### Gate G completion work

- Create a checksummed inventory of all 79,200 Parquet files, six manifests, six verification
  reports, configuration files, bundle, lockfile, and 26 analysis tables.
- Copy that inventory and all immutable evidence to independent storage and verify checksums.
- Re-run both domain analyses from a clean environment and compare file hashes.
- Investigate singular fits and missing music item-side models without modifying raw data.
- Execute the two registered sensitivity views and document concordance with primary results.

### Manuscript work

- Build figures for relevance versus exposure breadth, trait-minus-neutral Gini/HHI/ARP deltas,
  and the model/domain RQ3 scenario matrix.
- Report estimates, 95% intervals, standardized effects, raw p-values, corrected p-values, and
  convergence warnings.
- Separate primary confirmatory results from exploratory trait, genre, and provider slices.
- Draft methods, ethics, limitations, reproducibility, and data-availability sections from this
  report and the frozen source files.

### Optional mitigation

Only after the primary package is frozen, create a new design/version for a fairness-aware system
instruction or post-hoc reranker. Evaluate whether it reduces Gini/HHI and group disparities
without materially reducing Precision@10 or NDCG@10.

## 15. Authoritative evidence index

| Evidence | Location |
|---|---|
| Frozen A1 override | `config/full_run_v2_100_a1.yaml` |
| Analysis-only storage override | `config/full_run_v2_100_a1_analysis.yaml` |
| Frozen design bundle | `data/relevance_labels/persona_relevance_bundle_full_v2_100_a1_frozen.json` |
| Sampling plan | `docs/SAMPLING_PLAN_V2_100.md` |
| A1 amendment | `docs/DESIGN_AMENDMENT_V2_100_A1.md` |
| Collection sequence | `data/audits/collection_sequence_v2_100_a1.json` |
| Dataset provenance | `data/DATA_SOURCES.md` |
| Six pilot audits | `data/audits/*pilot*` and `documentation/02_SIX_PILOT_TESTS.md` |
| Six full manifests | versioned paths under `outputs/queries` |
| Six verification reports | `outputs/tables/full_partition_verification_*.json` |
| Confirmatory analysis tables | archived `recllm_movie_*` and `recllm_music_*` artifact files |
| Architecture and methods | `documentation/01` through `documentation/06` |
| This consolidated report | `documentation/13_FULL_PROJECT_REPORT_AND_CONFIRMATORY_FINDINGS.md` |

## 16. Final status

- Workstation qualification: complete.
- Six pilots: complete.
- Independent population and wording review: complete.
- Frozen A1 design and preflight: complete.
- Confirmatory collection: complete, 79,200/79,200.
- Six partition audits: complete; Llama caveats retained.
- Primary movie and music analyses: complete.
- Full documentation and initial key-findings interpretation: complete.
- Sensitivity analysis, fit remediation, durable archive, figures, mitigation, and manuscript:
  pending.
