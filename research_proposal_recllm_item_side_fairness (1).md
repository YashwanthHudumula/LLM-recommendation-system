# Research Proposal

## Title
**Who Gets Seen? Auditing Item-Side Exposure Disparities Induced by Personality-Conditioned Prompting in LLM-Based Recommender Systems**

---

## 1. Abstract

Large Language Model-based recommender systems (RecLLMs) have been extensively audited for **user-side** fairness — whether a given user receives worse or different recommendations when their prompt reveals a demographic attribute or an implied personality trait (e.g., FaiRLLM, CFaiRLLM, FairEval). What remains almost entirely unexamined is the **item-side** consequence of this same phenomenon: when many users with different personality-implying prompts query a RecLLM, does the *aggregate exposure distribution across the item catalog* shift systematically — favoring certain genres, providers, or popularity tiers depending on the personality profile invoked? A May 2026 systematic survey of fairness in LLM-based recommendation explicitly identifies the intersection of item-side fairness with social/attribute (including personality) bias as **"rarely studied explicitly"** in the current literature. This project proposes to close that specific, recently confirmed gap: a counterfactual auditing study that holds catalog and item metadata fixed, varies personality-implied user prompts, and measures resulting **item-level exposure inequality** using established item-side fairness metrics, alongside the existing user-side personality-fairness metrics for comparison. The study is inference-only (no model training), uses public datasets and metadata, and is scoped to be completed within a masters-level timeline.

---

## 2. Background and Motivation

RecLLMs generate recommendations directly from natural-language prompts rather than from collaborative-filtering signals, introducing new bias pathways rooted in pretrained knowledge, prompt phrasing, and decoding behavior. A well-established line of work audits **user-side** fairness in this setting:

- **FaiRLLM** (Zhang et al., RecSys 2023) introduced the Sensitive-to-Neutral Similarity Range/Variance (SNSR/SNSV) metrics to quantify how much a user's recommendation list shifts when a sensitive attribute is revealed.
- **CFaiRLLM** (Deldjoo & Di Noia, ACM TIST, "Just Accepted" as of March 2025) extended this to intersectional demographic attributes and benefit-based (rather than purely similarity-based) fairness. Cite the arXiv preprint (arXiv:2403.05668) alongside the TIST venue until final volume/page numbers are assigned.
- **FairEval** (Sah et al., arXiv 2025) and its follow-up, **"Uncertainty and Fairness Awareness in LLM-Based Recommendation Systems"** (Sah et al., arXiv 2026, accepted at IASEAI'26), extended the same paradigm to **personality traits**, introducing the Personality-Aware Fairness Score (PAFS) and testing robustness to prompt perturbations (typos, translation).
- **PerFairX** (Sah et al., ICCV 2025 workshop) sits directly at the personality/fairness intersection this project targets and must be read and explicitly distinguished from this proposal's contribution in the related-work write-up — it asks whether a *balance* between personalization and fairness exists at the user-list level, whereas this project asks what happens to the *catalog* as a result of that same balance-seeking behavior, aggregated across a population.

All of these studies ask: *does this one user's list change?* None of them ask the complementary question that traditional (pre-LLM) recommender fairness research has long emphasized: *what happens to the item catalog as a whole?* Item-side fairness — exposure concentration, provider fairness, popularity/long-tail bias — is a mature, well-metricized area in classical recommender systems (Gini Index, HHI, ARP, group-level exposure metrics such as MGU/DGU). The closest existing item-side work in the LLM setting, Jiang et al. (2024, WWW), introduces exactly this style of metric (MGU/DGU) but does so for a **fine-tuned** LLM-based recommender (LLaMA fine-tuned on MovieLens/Steam interaction data) — a fundamentally different pipeline from the **zero-shot, prompting-only** RecLLM setting this project and the personality-fairness literature (FaiRLLM/CFaiRLLM/FairEval) study. Their metrics are directly reusable, but their findings about *why* item-side disparities arise (training-data and fine-tuning artifacts) do not transfer to a setting with no training step at all — which is precisely the gap this project targets. Per the May 2026 survey "Rethinking Fairness in LLM-Based Recommender Systems" (Ma et al., arXiv:2606.28340), **the combination of item-side fairness with social/attribute bias mechanisms — the category personality bias falls under — is explicitly marked as rarely studied** in their taxonomy of the field (their Table 1). The survey's own "Open Challenges" section explicitly calls for research that moves beyond filling these missing intersections and investigates how fairness objectives interact across stakeholders, citing the risk that improving user-side personalization may amplify provider exposure disparities.

This project directly answers that call for the personality dimension specifically.

**Why an effect would be expected at all.** The hypothesized mechanism is representational rather than an accuracy failure: pretrained LLMs plausibly encode associative links between personality-trait language and cultural-product stereotypes (e.g., text patterns associated with "openness" co-occurring with arthouse or experimental framing; patterns associated with "conscientiousness" co-occurring with structured, mainstream, or highly-rated content). If such associations exist and are consistently activated across many users who share a trait profile, the effect on any single user's list may look like ordinary, defensible personalization — while the same consistent nudge, summed across a population, concentrates exposure onto a narrower set of items, genres, or providers. This distinguishes the phenomenon under study from a relevance or accuracy collapse, and is the theoretical basis for expecting user-side and item-side fairness to potentially diverge (see RQ3 below).

---

## 3. Problem Statement

> It is currently unknown whether conditioning RecLLM prompts on different implied user personality traits produces systematic, aggregate shifts in item-level exposure across the recommendation catalog — as distinct from the already-studied question of whether any single user's individual recommendation list changes.

---

## 4. Research Questions

| # | Research Question |
|---|---|
| RQ1 | When aggregated across many personality-conditioned prompts, does item-level exposure (which items/genres/providers appear in recommendation lists) shift systematically compared to a neutral-prompt baseline? |
| RQ2 | Do certain Big Five personality profiles (e.g., high Openness vs. high Conscientiousness) correlate with systematically different item popularity-tier exposure (head/mid/tail) or genre-category concentration? |
| RQ3 | Does user-side fairness (individual list stability, measured via SNSR/SNSV/PAFS) correlate with item-side fairness (aggregate exposure equality, measured via Gini/HHI/MGU/DGU) — or can a system appear "fair" on one axis while unfair on the other? This question is a direct empirical test, in the RecLLM setting, of the general individual-vs-group fairness tension formalized by Dwork et al. (2012, "Fairness Through Awareness"): a system can satisfy an individual-level fairness criterion for every case while still producing an unequal population-level allocation, because small, consistent per-case effects compound when summed across many cases. |
| RQ4 | Are observed item-side disparities consistent across LLM providers and model scale? |
| RQ5 (stretch) | Can a lightweight, inference-only mitigation (e.g., system-role fairness instruction or post-hoc re-ranking) reduce item-side exposure disparity without materially harming user-perceived relevance? |

---

## 5. Objectives

1. Construct a counterfactual persona × prompt-phrasing benchmark (reusing validated Big Five persona and phrasing design from prior RecLLM fairness work) across a large simulated "user population."
2. Query multiple current-generation LLMs and aggregate the resulting recommendation lists at the catalog level.
3. Compute both item-side exposure metrics (aggregate) and user-side fairness metrics (individual), enabling direct comparison — the first study to report both together for personality-conditioned prompting.
4. Test whether item-side disparities are consistent across model families/scale.
5. (Stretch) Evaluate one lightweight mitigation strategy and report its effect on the disparity–relevance trade-off.

---

## 6. Literature Review Scope

**Primary anchor papers (read these first, in this order):**
1. Zhang et al. (2023), *Is ChatGPT Fair for Recommendation?* — FaiRLLM, RecSys 2023 (foundational SNSR/SNSV)
2. Deldjoo & Di Noia (2025), *CFaiRLLM*, ACM TIST
3. Sah et al. (2025), *FairEval*, arXiv:2504.07801 (personality + PAFS)
4. Sah et al. (2026), *Uncertainty and Fairness Awareness in LLM-Based Recommendation Systems*, arXiv:2602.02582
5. Sah et al. (2025), *PerFairX: Is There a Balance Between Fairness and Personality in Large Language Model Recommendations?*, ICCV 2025 workshop (closest adjacent work — read carefully and state explicitly in the related-work section how this project's item-side, aggregate framing differs from PerFairX's user-list, individual framing)
6. Jiang et al. (2024), *Item-Side Fairness of Large Language Model-Based Recommendation System*, WWW 2024 (item-side metrics, but for a **fine-tuned** LRS, not zero-shot prompting — reuse the metrics, not the causal story)
7. Ma et al. (2026), *Rethinking Fairness in LLM-Based Recommender Systems: A Survey*, arXiv:2606.28340 (use this to structure your related-work section and to justify the gap explicitly — cite their Table 1 taxonomy directly)

**Scopus / ACM DL / arXiv search strings:**

```
TITLE-ABS-KEY ( ( "large language model*" OR "LLM*" ) AND ( "recommend*" ) AND ( "item-side" OR "item side" ) AND ( "fairness" OR "exposure" ) )

TITLE-ABS-KEY ( ( "personality" OR "Big Five" OR "psychographic*" ) AND ( "recommend*" ) AND ( "large language model*" ) )

TITLE-ABS-KEY ( ( "provider fairness" OR "exposure fairness" OR "popularity bias" ) AND ( "large language model*" OR "LLM*" ) AND ( "recommend*" ) )

TITLE-ABS-KEY ( ( "Gini" OR "Herfindahl" OR "HHI" OR "long-tail" ) AND ( "recommend*" ) AND ( "large language model*" ) )
```

---

## 7. Methodology

### 7.1 Overall Design

Reuse the validated **persona × phrasing counterfactual framework** from FairEval/FaiRLLM (user-side), but add a **catalog-aggregation layer**: instead of only analyzing each user's own list in isolation, pool recommendation outputs across the full simulated population of personas to construct an aggregate exposure distribution over the item catalog, per condition (personality trait level, phrasing type, model).

### 7.2 Domains and Item Pools

| Domain | Item Pool Source | Notes |
|---|---|---|
| Movies | MovieLens (1M/25M) metadata | Rich genre/popularity metadata; used across nearly all prior RecLLM fairness studies, enabling direct comparability |
| Music | LastFM-1K / LastFM-360K metadata | Cross-domain generalization check |

Fix the candidate pool per query (as recommended by prior FaiRLLM-style protocols) to prevent hallucinated titles from corrupting exposure measurement.

### 7.3 Persona and Prompt Design (reused, cite source)

| Attribute | Description |
|---|---|
| `persona_id` | Synthetic persona identifier |
| `stated_preferences` | Fixed content-preference statement, identical across all trait variants of a base persona |
| `personality_trait`, `trait_level` | One of the Big Five traits, High/Low/Neutral, using validated IPIP-NEO-style marker language |
| `phrasing_variant` | Formal / casual / direct / indirect (validated for semantic equivalence) |
| `domain` | Movies / Music |

Generate a large simulated population (e.g., 200–500 persona instances per trait level, crossed with phrasing) to give the item-side aggregation statistical power — this is the key design difference from prior user-side-only studies, which typically only need enough personas to detect *individual* list shifts, not catalog-level shifts.

### 7.4 Models to Audit

| Model | Access | Rationale |
|---|---|---|
| Current-generation closed model (e.g., a GPT-5-class model via API) | API | State-of-the-art baseline — note prior work (FairEval) used GPT-4o/Gemini 1.5 Flash, now a generation behind |
| Current-generation Claude model (via API) | API | Cross-provider comparison |
| Current-generation Gemini model (via API) | API | Cross-provider comparison |
| Open-weight model (e.g., a current Llama-family model, small and large variant) | Hugging Face / hosted inference | Tests RQ4 (scale effect), reproducible without paid API access |

*(Check current model availability and naming at query time — model generations move quickly; use whichever current-generation models are accessible via your institution's API budget.)*

### 7.5 Metrics

**A. User-side fairness (existing, for RQ3 comparison — reuse directly from prior work)**

| Metric | Source |
|---|---|
| SNSR@K, SNSV@K | Zhang et al. 2023 |
| PAFS@K | Sah et al. 2025 |
| Jaccard@K, SERP\*@K, PRAG\*@K | Zhang et al. 2023; Sah et al. 2025 |

**B. Item-side fairness (aggregate, the core novel measurement of this project)**

| Metric | Purpose | Source |
|---|---|---|
| Gini Index (over aggregate item exposure) | Overall exposure inequality across the catalog | Standard; used in Deldjoo 2025, Li et al. 2023 |
| Herfindahl-Hirschman Index (HHI) | Exposure concentration | Deldjoo 2025 |
| Average Recommendation Popularity (ARP@K) | Mean popularity of items surfaced, per condition | Li et al. 2026; Lu et al. 2025 |
| Long-tail coverage / catalog coverage | % of catalog ever recommended, per condition | Standard |
| Group-level unfairness: MGU@K (max group unfairness), DGU@K (disparity in group unfairness) | Whether specific item/genre groups are disproportionately over/under-exposed across personality conditions | Jiang et al. 2024 |

**C. Relevance/utility control (to confirm disparities aren't just "worse recommendations")**

| Metric | Purpose |
|---|---|
| Precision@K / NDCG@K against stated preferences | Confirms exposure shifts aren't simply accuracy collapse |

### 7.6 Experimental Protocol

1. **Pilot (small scale):** Validate persona/phrasing semantic equivalence and prompt pipeline on one model/domain before scaling up.
2. **Full data collection:** Query each model with the full persona × phrasing matrix, N repeats per condition (e.g., N = 3–5) at fixed decoding parameters (temperature ≈ 0.7).
3. **Per-user analysis:** Compute user-side metrics (A) per persona, as in prior work — this reproduces/validates against known FairEval-style findings as a sanity check.
4. **Aggregate analysis (core contribution):** Pool all recommendation outputs by condition (trait level × phrasing × model) into an aggregate item-exposure distribution; compute item-side metrics (B).
5. **Cross-metric comparison (RQ3):** Statistically test whether user-side fairness rank-orders models/conditions differently than item-side fairness does. Interpret the result against three named, pre-registered scenarios so that any outcome is a reportable finding rather than a null result in search of a story:
   - **Concordant** — the two metric families move together. Finding: cheaper, already-common user-side audits are a sufficient proxy for item-side/catalog harm in this setting.
   - **Independent** — no significant correlation. Finding: a system can pass user-side fairness audits while still concentrating exposure at the catalog level, exposing a blind spot in current auditing practice.
   - **Inverse** — stronger individual-list stability correlates with *worse* aggregate concentration (e.g., because personalizing well to a shared trait nudges many users toward the same subgenre). This is the most theoretically novel outcome and would provide direct empirical evidence for the personalization/provider-exposure tension flagged in Ma et al.'s Open Challenges section.
6. **Cross-model comparison (RQ4):** Repeat across all models; compare disparity magnitude and direction.
7. **(Stretch) Mitigation test (RQ5):** Apply one inference-time intervention (e.g., a fairness-aware system prompt, following Rotar et al. 2026's "can fairness be prompted?" framing) and re-measure both metric families.

### 7.7 Statistical Analysis

- Bootstrap confidence intervals on Gini/HHI/ARP given the aggregate nature of the metric (resample personas with replacement).
- Mixed-effects model with trait, phrasing, and model as fixed effects, persona as random effect, for RQ1/RQ2.
- Spearman rank correlation between user-side and item-side metric rankings across conditions, for RQ3.
- Multiple-comparison correction (Benjamini-Hochberg) across the five traits and phrasing types.

### 7.8 Tools

| Tool | Purpose |
|---|---|
| OpenAI / Anthropic / Google APIs | Closed-model querying |
| Hugging Face Transformers + Inference Endpoints | Open-weight model querying |
| Python (pandas, numpy, scipy, statsmodels) | Metric computation, statistics |
| sentence-transformers | Semantic equivalence validation for phrasing variants |
| Weights & Biases or structured CSV/Parquet logging | Tracking the large condition matrix |

---

## 8. Expected Contributions

1. First empirical study to measure **item-side** exposure disparity arising from **personality-conditioned** prompting in RecLLMs — directly addressing a gap explicitly flagged as understudied in a May 2026 field survey.
2. Direct empirical evidence on whether user-side and item-side personality fairness are correlated, independent, or in tension — a novel diagnostic finding regardless of direction.
3. A reusable, documented benchmark and pipeline (persona generation, prompt matrix, dual-metric evaluation) that other researchers can extend to new models or domains.
4. (Stretch) An evaluated mitigation strategy with a reported disparity–relevance trade-off.

---

## 9. Ethical Considerations

- All personas are synthetic; no real user data is used, avoiding privacy/GDPR concerns.
- Personality marker language should be drawn from validated psychometric instruments (e.g., IPIP-NEO), not invented stereotypes, and the write-up should avoid framing any finding as confirming personality stereotypes as "true" — the object of study is algorithmic behavior, not personality psychology itself.
- Findings should be reported as statistical patterns in specific models/datasets at a specific point in time, not as permanent or universal claims about any provider's system, given how quickly underlying models change.
- Budget and cache API calls carefully — the population-scale design (needed for aggregate item-side metrics) will use substantially more queries than a purely user-side study; estimate costs during the pilot phase before committing to full scale.

---

## 10. Timeline (approx. 16 weeks)

| Weeks | Milestone |
|---|---|
| 1–2 | Literature review (anchor papers + survey), persona/phrasing design and validation |
| 3 | Pilot run: one model, one domain, small persona sample; validate pipeline and cost estimate |
| 4–6 | Full-scale data collection across models × domains × personas × phrasings |
| 7–8 | Compute user-side metrics (validate against known prior findings) and item-side metrics (core contribution) |
| 9–10 | Cross-metric (RQ3) and cross-model (RQ4) statistical analysis |
| 11–12 | (Stretch) Mitigation experiment (RQ5) |
| 13–14 | Results synthesis, figures |
| 15–16 | Manuscript drafting, advisor feedback, submission formatting |

---

## 11. Target Venues

| Venue | Type | Fit |
|---|---|---|
| ACM Transactions on Recommender Systems (TORS) | Journal | Direct fit |
| ACM Transactions on Intelligent Systems and Technology (TIST) | Journal | Direct fit (same venue as CFaiRLLM) |
| ACM Transactions on Information Systems (TOIS) | Journal | Strong fit |
| Information Processing & Management | Journal | Good fit |
| RecSys (main conference or a fairness-focused workshop) | Conference | Highest-visibility venue for this exact topic if a conference route is preferred |

---

## 12. References (starting set — expand via the literature review)

- Zhang, J., Bao, K., Zhang, Y., Wang, W., Feng, F., & He, X. (2023). Is ChatGPT Fair for Recommendation? Evaluating Fairness in Large Language Model Recommendation. *RecSys 2023*.
- Deldjoo, Y., & Di Noia, T. (2025). CFaiRLLM: Consumer Fairness Evaluation in Large-Language Model Recommender System. *ACM TIST* (Just Accepted, March 2025); preprint at *arXiv:2403.05668*.
- Sah, C. K., Lian, X., Xu, T., & Zhang, L. (2025). FairEval: Evaluating Fairness in LLM-Based Recommendations with Personality Awareness. *arXiv:2504.07801*.
- Sah, C. K., Lian, X., Zhang, L., Xu, T., & Shah, S. S. (2026). Uncertainty and Fairness Awareness in LLM-Based Recommendation Systems. *IASEAI 2026*; *arXiv:2602.02582*.
- Sah, C. K., et al. (2025). PerFairX: Is There a Balance Between Fairness and Personality in Large Language Model Recommendations? *ICCV 2025 Workshop (MCL)*.
- Jiang, M., Bao, K., Zhang, J., Wang, W., Yang, Z., Feng, F., & He, X. (2024). Item-Side Fairness of Large Language Model-Based Recommendation System. *WWW 2024*.
- Ma, S.-D., Chen, C.-Y., Li, B.-A., Chen, P.-Y., Hsu, S.-Y., & Chen, Y.-N. (2026). Rethinking Fairness in LLM-Based Recommender Systems: A Survey. *arXiv:2606.28340*.
- Rotar, M., Rampisela, T. V., & Maistro, M. (2026). Can Fairness Be Prompted? Prompt-Based Debiasing Strategies in High-Stakes Recommendations. *arXiv:2603.12935*.
- Dwork, C., Hardt, M., Pitassi, T., Reingold, O., & Zemel, R. (2012). Fairness Through Awareness. *ITCS 2012*. (Theoretical grounding for RQ3's individual-vs-group fairness framing.)
