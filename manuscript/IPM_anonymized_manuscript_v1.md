# Who Gets Seen? Item-Side Exposure Fairness in Personality-Conditioned Large Language Model Recommendations

Research article — anonymized manuscript

## Abstract

Large language models (LLMs) can personalize recommendations from natural-language descriptions, but fairness audits have mainly examined how an individual user's list changes. This leaves a distinct platform-level question unanswered: which items receive exposure when personality cues are varied while preferences are held fixed? We conduct an inference-only, counterfactual audit of item-side exposure in personality-conditioned LLM recommendations. The study contains 79,200 recommendation queries spanning three open-weight LLM snapshots, movie and music domains, 100 base personas per domain, four semantically aligned prompt phrasings, three repeats, and high/low markers for each Big-Five trait plus a neutral baseline. Each persona's stated preferences and 120-item candidate pool remain fixed across counterfactual personality conditions. We measure relevance and user-side list change alongside raw and opportunity-adjusted exposure concentration, catalog coverage, and long-tail coverage. Personality conditioning produces measurable but heterogeneous exposure shifts. At the model level, opportunity coverage ranges from 0.257 to 0.415 for movies and 0.212 to 0.331 for music. The largest descriptive coverage shifts reach 0.060 and 0.031, respectively, while the largest absolute opportunity-Gini shifts reach 0.036 and 0.021. User-side and item-side conclusions frequently diverge: scenario classification is dominated by Independent relationships for several model-domain pairs and by Inverse relationships for one movie model. Results remain highly stable after excluding flagged responses, but exact-length filtering is less stable, especially for music. Candidate opportunity explains some concentration variation but does not eliminate the principal exposure disparities. The findings show that individual-level list similarity is not a sufficient proxy for supplier- or item-side fairness in RecLLMs.

**Keywords:** large language models; recommender systems; item-side fairness; exposure fairness; personality; counterfactual audit

## 1. Introduction

Large language models are increasingly used as conversational recommendation engines. Their ability to transform free-form descriptions into ranked suggestions makes them attractive for movies, music, products, and other domains. The same flexibility, however, creates a new fairness surface: seemingly benign descriptors can alter not only what a user sees, but also which catalog items repeatedly receive attention across a population.

Most existing fairness evaluations of LLM-based recommendation focus on the recipient of a ranked list. They ask whether protected or profile-related cues change recommendation similarity, relevance, or sentiment for otherwise comparable users. This user-side perspective is necessary, but it cannot answer a platform-level distributional question. Two systems can produce comparable amounts of individual list change while allocating aggregate exposure very differently across popular and long-tail items. Conversely, substantial list changes can redistribute positions among similarly exposed items without changing catalog-level concentration.

This study therefore audits item-side exposure under counterfactual personality conditioning. We vary only implied Big-Five trait language and prompt phrasing while holding each persona's preferences and candidate opportunity fixed. We then aggregate recommendations over the synthetic population and compare exposure distributions with a neutral baseline. The audit is inference-only; it does not train, fine-tune, or infer personality for real people.

The study addresses three questions. **RQ1** asks whether personality conditioning shifts aggregate item exposure relative to a neutral prompt. **RQ2** asks whether those shifts vary by model, domain, trait pole, and prompt phrasing. **RQ3** asks whether user-side list-change metrics agree with item-side exposure metrics. We additionally test whether results are explained by response quality or candidate opportunity.

The contribution is fourfold. First, we provide a controlled population-level design that separates preference from personality language. Second, we operationalize exposure fairness through raw and opportunity-adjusted concentration, coverage, and long-tail measures. Third, we directly compare user-side and item-side conclusions rather than treating one as a proxy for the other. Fourth, we release a reproducible, resumable audit pipeline and a frozen evidence package covering 79,200 local-model queries.

## 2. Related work

### 2.1 Fairness in LLM-based recommendation

FaiRLLM established a counterfactual framework for evaluating sensitive-attribute effects in LLM recommendation and introduced user-side comparison measures such as sensitive-to-neutral similarity and variance [1]. Subsequent work has broadened the profiles, domains, and evaluation protocols used to audit recommendation LLMs [2,3]. FairEval supplies a recent evaluation framework and metric family for recommendation fairness [3], while personality-focused work shows that personality cues can interact with both recommendation quality and fairness [4,5]. These studies motivate controlled prompt comparisons, but their main unit of analysis remains the recommendation received by an individual profile.

### 2.2 Item-side exposure fairness

Ranking systems distribute a scarce resource: attention. Equity-of-attention and fairness-of-exposure research formalizes the relationship between relevance, position, and provider or item visibility [6,7]. Surveys of recommender-system fairness likewise distinguish consumer-side objectives from supplier-, provider-, and item-side outcomes [8]. In LLM-based recommendation, Jiang et al. explicitly studied item-side fairness and demonstrated that LLM recommenders can reproduce popularity and group disparities [9]. Our work extends this direction to population-level, personality-conditioned prompting and compares exposure conclusions with established user-side metrics.

### 2.3 Personality and counterfactual controls

Personality can influence stated tastes, exploration, and decision style. An audit that changes both personality and preferences cannot isolate the effect of personality language. We therefore use paired counterfactual prompts: every base persona retains the same stated preferences, history-derived relevant items, and candidate pool across all trait and phrasing variants. Big-Five markers use restrained IPIP-style behavioral language rather than demographic proxies or invented stereotypes [10]. The design estimates sensitivity to textually implied personality; it does not claim that the synthetic labels measure a person's psychological state.

## 3. Methods

### 3.1 Study design

The full factorial audit crosses three model snapshots, two domains, 100 base personas per domain, four prompt phrasings, three stochastic repeats, and eleven personality conditions: high and low poles of openness, conscientiousness, extraversion, agreeableness, and neuroticism, plus neutral. This yields 39,600 completed queries per domain and 79,200 overall (Table 1).

For a base persona, the stated preference text is invariant across counterfactual conditions. The personality clause and surface phrasing change, but the recommendation task, output length, candidate items, and decoding settings do not. The four prompt forms are formal, casual, direct, and indirect. A semantic-equivalence gate compares their embeddings before collection and halts if a configured similarity threshold is not met.

**Table 1. Study design and response-quality views.** Exact-10 retains responses with exactly ten matched recommendations; unflagged excludes any response with a quality flag. Eligible catalog size is the union of items offered to at least one persona.

| Domain | Primary queries | Exact-10 retained | Exact-10 rate | Unflagged retained | Unflagged rate | Eligible items |
|---|---:|---:|---:|---:|---:|---:|
| Movie | 39,600 | 33,139 | 0.837 | 38,539 | 0.973 | 935 |
| Music | 39,600 | 35,653 | 0.900 | 39,556 | 0.999 | 2,516 |

### 3.2 Data, personas, and candidate opportunity

Movie personas and popularity estimates derive from MovieLens; music personas and popularity estimates derive from Last.fm interaction data [11,12]. User identifiers are excluded from prompts. Historical interactions are transformed into fixed, textual preferences and relevance sets. No claim is made that dataset users possess the personality traits assigned in the experiment.

Every persona receives a fixed pool of 120 candidate items: 60 head, 30 mid-popularity, and 30 tail items, with at least 30 items relevant to the persona. The same pool is reused across all personality and phrasing counterfactuals for that persona. Prompts instruct models to choose only from this pool. Parsed outputs are independently matched against the catalog; unmatched or off-list titles are logged as hallucinations and excluded from exposure aggregation.

Opportunity adjustment conditions exposure on eligibility. For item *i*, let eᵢ be its observed recommendation count and oᵢ the number of query opportunities in which it appeared. We define adjusted exposure as aᵢ = eᵢ / oᵢ when oᵢ > 0. Concentration and coverage measures are computed over these adjusted rates or over the eligible catalog, preventing frequently offered items from being treated as directly comparable with rarely offered items.

### 3.3 Models and prompting

We audit Qwen3 8B, Llama 3.1 8B, and Gemma 3 12B model snapshots served locally through Ollama. Snapshot digests are frozen in the repository. The context limit is 2,048 tokens, temperature is 0.7, and each condition has three repeats. If a response is under-length, the pipeline makes a deterministic retry at temperature 0. Collection is resumable, and metrics are derived after collection from an immutable query table rather than computed in the model loop. Because inference is local, no paid API calls are required.

### 3.4 Outcome measures

**Relevance and list stability.** Precision@10 and NDCG@10 compare recommendations with each persona's frozen relevance set. Jaccard@10 summarizes overlap between a personality-conditioned list and its paired neutral list. We also compute the FaiRLLM/FairEval user-side family, including sensitive-to-neutral similarity and variance, personality-aware fairness score, SERP*, and PRAG* [1,3].

**Item-side exposure.** For each model, domain, trait pole, and phrasing condition, recommendations are pooled across personas and repeats. Gini and Herfindahl-Hirschman Index (HHI) quantify exposure concentration. Catalog coverage measures the share of eligible items receiving at least one recommendation; long-tail coverage measures the corresponding share for tail items. Average recommendation popularity and group utility disparity are also retained in the complete evidence package. The primary analysis emphasizes opportunity-adjusted Gini, normalized HHI, catalog coverage, and long-tail coverage.

**Counterfactual effects.** A condition effect is the personality-conditioned metric minus the paired neutral metric under the same model, domain, and phrasing. Positive coverage deltas indicate broader exposure; positive Gini or HHI deltas indicate greater concentration.

### 3.5 Statistical analysis

Confidence intervals for aggregate exposure metrics use persona-level bootstrap resampling, preserving all repeated queries belonging to a sampled persona. This avoids treating correlated query rows as independent. The primary descriptive summaries report mean absolute deltas, maximum absolute deltas, and the number of 95% intervals excluding zero. Strongest-effect figures are explicitly exploratory maxima and are not multiplicity-adjusted discoveries. Benjamini-Hochberg adjustment is retained for the planned family of trait and phrasing comparisons.

The preregistered mixed-effects specification includes trait, phrasing, and model fixed effects with a persona random intercept. All primary fits reported optimizer convergence, but every successful fit also exhibited a singular random-effects covariance, boundary estimates, and a non-positive-definite Hessian. We therefore do not interpret those coefficients as confirmatory evidence. A transparent sensitivity model uses ordinary least squares with persona-clustered standard errors and standardized effects relative to the frozen 0.20 residual-SD smallest effect size of interest; it is treated as a robustness analysis, not a replacement outcome.

For RQ3, Spearman correlations compare rankings of personality effects under each user-side and item-side metric pair. A frozen rule classifies sufficiently positive correlations as **Concordant**, correlations near zero as **Independent**, sufficiently negative correlations as **Inverse**, and non-estimable cases as **Undefined**. This precludes a post-hoc narrative classification.

### 3.6 Robustness, validation, and reproducibility

The primary view includes all successfully parsed queries. Two response-quality views are evaluated without re-querying models: exact-10 responses and unflagged responses. A separate opportunity analysis compares raw and eligibility-adjusted deltas. The analysis package, tables, and figures are deterministically generated from hash-verified frozen inputs.

Prompt wording was also checked in a blind human audit containing 34 responses and 340 classifications. Aggregate accuracy was 86.2%, with item-level accuracy between 76.5% and 94.1%. Because no numerical threshold was fixed in advance, this result supports interpretability but is not used as a pass/fail inferential gate.

## 4. Results

### 4.1 Relevance and baseline exposure differ by model

Gemma has the highest mean relevance in both domains: Precision@10 is 0.491 for movies and 0.463 for music (Table 2). Llama produces the broadest opportunity-adjusted coverage (0.415 movie; 0.331 music) but the lowest Jaccard stability (0.205; 0.154). Qwen has the narrowest opportunity coverage (0.257; 0.212) and the greatest adjusted Gini (0.869; 0.880). Thus, model choice creates a substantial baseline relevance-exposure trade-off before personality effects are considered (Figure 1).

![Figure 1. Relevance and opportunity-adjusted catalog coverage across experimental conditions. Small points show conditions and highlighted points show model-domain means.](../outputs/manuscript_assets/version=manuscript-assets-v1/figures/figure_1_relevance_opportunity_tradeoff.png)

**Figure 1. Relevance-exposure opportunity trade-off.** Precision@10 is plotted against opportunity-adjusted catalog coverage. Higher values are desirable on both axes, but the audited models occupy different trade-off regions.

**Table 2. Model-level means in the primary view.** HHI is normalized in the opportunity-adjusted column.

| Domain | Model | Precision@10 | NDCG@10 | Jaccard@10 | Raw Gini | Raw HHI | Raw coverage | Opp. Gini | Opp. HHI | Opp. coverage | Opp. tail coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Movie | Gemma | .491 | .527 | .506 | .998 | .0169 | .00495 | .836 | .00517 | .313 | .148 |
| Movie | Llama | .333 | .360 | .205 | .998 | .0127 | .00657 | .771 | .00357 | .415 | .412 |
| Movie | Qwen | .407 | .479 | .504 | .999 | .0205 | .00407 | .869 | .00729 | .257 | .231 |
| Music | Gemma | .463 | .478 | .419 | .999 | .00945 | .00234 | .852 | .00205 | .250 | .256 |
| Music | Llama | .337 | .362 | .154 | .999 | .00683 | .00310 | .792 | .00143 | .331 | .461 |
| Music | Qwen | .344 | .381 | .359 | .999 | .0101 | .00199 | .880 | .00264 | .212 | .304 |

### 4.2 Personality cues shift item exposure

Across the 120 trait-pole-by-phrasing comparisons per domain, mean absolute opportunity-Gini deltas are 0.0092 for movies and 0.0076 for music. The corresponding maxima are 0.0363 and 0.0210. Mean absolute opportunity-coverage deltas are 0.0140 and 0.0107, with maxima of 0.0599 and 0.0306. Persona-bootstrap intervals exclude zero in 28/120 movie and 47/120 music Gini contrasts, and 30/120 movie and 44/120 music coverage contrasts. These counts are descriptive; they are not a substitute for multiplicity-adjusted inference.

The largest observed effects differ by model, domain, trait, and phrasing (Figure 2). For example, low-openness casual wording produces the largest movie coverage contraction for Llama (delta -0.0599, 95% CI -0.0675 to -0.0274) and the largest movie concentration increase (Gini delta 0.0363, 95% CI 0.0145 to 0.0447). In music, the largest coverage contraction occurs for high-conscientiousness casual wording with Llama (delta -0.0306, 95% CI -0.0383 to -0.0113), whereas the largest absolute Gini shift is a decrease for high-agreeableness direct wording (delta -0.0210, 95% CI -0.0310 to -0.0067). The direction is not uniform, which argues against a single global statement that personality cues always concentrate or always diversify exposure.

![Figure 2. Largest absolute opportunity-adjusted Gini and catalog-coverage delta for each model and domain.](../outputs/manuscript_assets/version=manuscript-assets-v1/figures/figure_2_opportunity_delta_forest.png)

**Figure 2. Strongest descriptive opportunity-adjusted effects.** Points show the largest absolute observed Gini and catalog-coverage delta for each model-domain pair; bars are persona-bootstrap 95% confidence intervals. These selected maxima are exploratory and not multiplicity-adjusted.

### 4.3 User-side change does not reliably predict item-side exposure

RQ3 scenario composition varies sharply by model (Figure 3). Movie Gemma and Llama are dominated by Independent relationships (22/27 and 18/27 metric pairs). Movie Qwen is predominantly Inverse (21/27), meaning conditions ranked as larger shifts by a user-side metric often rank oppositely under an item-side metric. Music Gemma and Qwen contain more Concordant cases (15/27 and 12/27), while music Llama remains mostly Independent (15/27). Six metric pairs in each music model are Undefined because one ranking lacks sufficient variation.

![Figure 3. Counts of Concordant, Independent, Inverse, and Undefined RQ3 relationships for each model-domain pair.](../outputs/manuscript_assets/version=manuscript-assets-v1/figures/figure_3_rq3_scenario_composition.png)

**Figure 3. User-side/item-side scenario composition.** Each model-domain panel contains 27 frozen metric-pair classifications. The heterogeneous composition shows that individual list change cannot stand in for aggregate exposure fairness.

### 4.4 Candidate opportunity does not remove the main disparity

Raw and opportunity-adjusted coverage deltas are almost identical in rank (Spearman rho approximately 1.00 in both domains), as are long-tail-coverage deltas (rho at least 0.998). Concentration measures are more sensitive: raw-versus-adjusted Gini rho is 0.754 for movies and 0.830 for music, while HHI rho is 0.456 and 0.611. Direction agreement ranges from 64.2% to 81.7% for concentration and is 100% for both coverage measures. Candidate opportunity therefore explains part of the concentration ordering, but it does not explain away coverage disparities (Figure 4).

![Figure 4. Concordance between raw and opportunity-adjusted exposure deltas for concentration and coverage measures.](../outputs/manuscript_assets/version=manuscript-assets-v1/figures/figure_4_raw_adjusted_concordance.png)

**Figure 4. Raw-adjusted concordance.** Coverage conclusions are essentially invariant to eligibility adjustment, whereas concentration conclusions change moderately because candidate opportunity is uneven across items.

### 4.5 Response-quality sensitivity

The unflagged-response view strongly reproduces primary conclusions. Across opportunity metrics, primary-versus-unflagged rank correlations are at least 0.983 for movies and 0.997 for music, with sign agreement of at least 94.2% and 98.3%. RQ3 classification agrees in 80/81 cases (98.8%) in each domain.

Exact-10 filtering is less stable. Movie rank correlations range from 0.704 to 0.836, with sign agreement from 81.7% to 90.8%. Music rank correlations range from 0.261 to 0.683, with sign agreement from 80.0% to 83.3%. RQ3 classification still agrees in 74/81 movie cases (91.4%) and 78/81 music cases (96.3%). Because exact-length filtering removes 16.3% of movie and 10.0% of music responses and may select on model behavior, the primary view remains preferable, with exact-10 treated as a stringent sensitivity analysis.

## 5. Discussion

### 5.1 Principal findings

The audit yields three main findings. First, personality-conditioned language can redistribute aggregate exposure even when preferences and candidate opportunity are fixed. The effects are not universal: their magnitude and direction depend on the model, domain, trait pole, and phrasing. Second, the models occupy different baseline relevance-exposure regimes. The most relevant model is not the broadest-exposure model, and the broadest model is also the least stable under repeated list comparison. Third, user-side fairness metrics and item-side exposure metrics often answer different questions. The predominance of Independent and, for movie Qwen, Inverse relationships makes it unsafe to infer supplier-side fairness from individual list similarity alone.

### 5.2 Implications for RecLLM evaluation

A practical RecLLM audit should report at least three layers. The first is relevance, to ensure that apparent fairness is not achieved through recommendation collapse. The second is user-side counterfactual stability, which tests whether comparable profiles receive comparable lists. The third is aggregate item exposure, preferably both raw and opportunity-adjusted. Coverage and concentration should be shown together: two conditions may expose the same fraction of the catalog while distributing recommendations very differently among those items.

The opportunity analysis also changes how concentration should be interpreted. Fixed candidate pools are essential for controlling hallucinations, but pooling persona-specific candidates creates unequal catalog eligibility. Raw Gini and HHI partially mix model selection with opportunity. Eligibility-adjusted concentration is therefore the stronger primary measure. Coverage, by contrast, is highly robust to the adjustment in this experiment.

### 5.3 Governance and design implications

The results support a multi-stakeholder review process. A platform can maintain acceptable per-user relevance while systematically narrowing exposure for a trait-conditioned population. Monitoring should therefore include exposure dashboards by prompt condition, model snapshot, domain, popularity tier, and provider group where metadata permit. Model updates and prompt-template changes should trigger a repeated paired audit because effects do not transfer uniformly across models.

Personality personalization also deserves careful product framing. Behavioral language may be volunteered by users or generated by a system, yet either route can influence catalog visibility. Systems should avoid covert psychological inference, disclose when personality cues shape recommendations, and give users a meaningful way to disable or correct personalization. Item-side monitoring should not be used to infer sensitive psychological attributes from observed behavior.

### 5.4 Limitations

This is a controlled audit of three frozen, open-weight model snapshots in two entertainment domains; it is not evidence about all LLMs, commercial systems, or recommendation tasks. The personas are synthetic counterfactuals built from deidentified interaction histories. They improve control but cannot reproduce the full language, goals, and social context of real users. The Big-Five marker clauses are linguistic interventions, not validated psychological measurements.

Candidate pools reduce hallucination and stabilize opportunity, but they are smaller than production catalogs and may alter how an LLM reasons. Relevance labels inherit assumptions from historical interactions and can encode popularity bias. Provider/studio metadata are incomplete, so the strongest reported conclusions concern item and popularity exposure rather than provider welfare.

The strongest-effect intervals select maxima and are descriptive. The planned mixed-effects models are numerically unreliable because their random-effect covariance is singular; interpreting their coefficients would overstate the evidence. Persona-clustered fixed-effect models are retained only as sensitivity analyses. Finally, a blind wording audit supports semantic interpretability, but no acceptance threshold was preregistered. Future work should preregister wording-validation thresholds, expand to additional languages and domains, include proprietary and larger models, and test whether exposure-aware prompting or reranking can improve item-side fairness without degrading relevance.

## 6. Conclusion

Personality-conditioned recommendation is not only a question of whether an individual receives a different list. It is also a question of which items accumulate attention when the same linguistic cue is repeated across a population. Across 79,200 controlled queries, item exposure shifts are measurable, heterogeneous, and only partially aligned with user-side fairness metrics. The central methodological implication is simple: RecLLM audits should measure both sides of the recommendation exchange. Holding preferences and opportunity fixed, reporting relevance controls, and aggregating exposure by condition provide a practical foundation for doing so.

## Declarations

### Ethics statement

The study uses deidentified public interaction datasets to construct fixed preference profiles and does not attempt to infer the personality of dataset users. Big-Five conditions are synthetic experimental interventions. User identifiers are not included in prompts. All model inference is local, and the reported analyses concern aggregate system behavior rather than psychological claims about individuals.

### Data and code availability

Code, frozen configurations, derived tables, figure-generation specifications, and reproducibility audits are prepared in an anonymized repository. The public repository URL and archival DOI will be supplied after peer-review anonymity permits. Original datasets remain subject to their source licenses; redistribution follows those terms. Immutable query-level outputs and checksums are documented so derived analyses can be rerun without new model calls.

### Funding

Funding information is withheld from the anonymized manuscript and must be completed before final submission.

### Competing interests

Competing-interest information is withheld from the anonymized manuscript and must be completed before final submission.

### Generative AI declaration

During manuscript preparation, the authors used OpenAI Codex to assist with manuscript organization, language editing, and document formatting. All analyses, numerical results, citations, and interpretations were checked against frozen source artifacts. The authors reviewed the resulting text and take full responsibility for the content. This declaration must be reconciled with the target journal's policy at submission.

## References

[1] Zhang, J., Bao, K., Zhang, Y., Wang, W., Feng, F., & He, X. (2023). Is ChatGPT fair for recommendation? Evaluating fairness in large language model recommendation. *Proceedings of the 17th ACM Conference on Recommender Systems*, 993–999. https://doi.org/10.1145/3604915.3608860

[2] Deldjoo, Y., & Di Noia, T. (2025). CFaiRLLM: Consumer fairness evaluation in large-language model recommender system. *ACM Transactions on Intelligent Systems and Technology*. https://doi.org/10.1145/3725853

[3] Sah, C. K., Lian, X., Xu, T., & Zhang, L. (2025). FairEval: Evaluating fairness in LLM-based recommendations with personality awareness. *arXiv preprint arXiv:2504.07801*. https://doi.org/10.48550/arXiv.2504.07801

[4] Sah, C. K., & Lian, X. (2025). PerFairX: Is there a balance between fairness and personality in recommender systems? *Proceedings of the IEEE/CVF International Conference on Computer Vision Workshops*, 2771–2780. https://doi.org/10.1109/ICCVW69036.2025.00289

[5] Sah, C. K., Lian, X., Zhang, L., Xu, T., & Shah, S. S. (2026). Uncertainty and fairness awareness in large language model-based recommender systems. *arXiv preprint arXiv:2602.02582*. https://doi.org/10.48550/arXiv.2602.02582

[6] Biega, A. J., Gummadi, K. P., & Weikum, G. (2018). Equity of attention: Amortizing individual fairness in rankings. *Proceedings of the 41st International ACM SIGIR Conference on Research & Development in Information Retrieval*, 405–414. https://doi.org/10.1145/3209978.3210063

[7] Singh, A., & Joachims, T. (2018). Fairness of exposure in rankings. *Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining*, 2219–2228. https://doi.org/10.1145/3219819.3220088

[8] Wang, Y., Ma, W., Zhang, M., Liu, Y., & Ma, S. (2023). A survey on the fairness of recommender systems. *ACM Transactions on Information Systems, 41*(3), Article 52. https://doi.org/10.1145/3547333

[9] Jiang, M., Bao, K., Zhang, J., Wang, W., Yang, Z., Feng, F., & He, X. (2024). Item-side fairness of large language model-based recommendation system. *Proceedings of the ACM Web Conference 2024*, 4717–4726. https://doi.org/10.1145/3589334.3648158

[10] Goldberg, L. R., et al. (2006). The international personality item pool and the future of public-domain personality measures. *Journal of Research in Personality, 40*(1), 84–96. https://doi.org/10.1016/j.jrp.2005.08.007

[11] Harper, F. M., & Konstan, J. A. (2015). The MovieLens datasets: History and context. *ACM Transactions on Interactive Intelligent Systems, 5*(4), Article 19. https://doi.org/10.1145/2827872

[12] Celma, Ò. (2010). *Music recommendation and discovery: The long tail, long fail, and long play in the digital music space*. Springer. https://doi.org/10.1007/978-3-642-13287-2

[13] Järvelin, K., & Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR techniques. *ACM Transactions on Information Systems, 20*(4), 422–446. https://doi.org/10.1145/582415.582418

[14] Dwork, C., Hardt, M., Pitassi, T., Reingold, O., & Zemel, R. (2012). Fairness through awareness. *Proceedings of the 3rd Innovations in Theoretical Computer Science Conference*, 214–226. https://doi.org/10.1145/2090236.2090255

[15] Rotar, M., Rampisela, T. V., & Maistro, M. (2026). Can fairness be prompted? Prompt-based debiasing strategies in high-stakes recommendations. *arXiv preprint arXiv:2603.12935*. https://doi.org/10.48550/arXiv.2603.12935

## Appendix A. Supporting robustness evidence

![Figure S1. Rank and sign concordance between the primary response view and exact-10 or unflagged sensitivity views.](../outputs/manuscript_assets/version=manuscript-assets-v1/figures/figure_s1_sensitivity_concordance.png)

**Figure S1. Response-quality sensitivity.** Primary-versus-unflagged conclusions are highly concordant. Exact-10 filtering is materially less stable for music, consistent with selective removal of non-exact responses.

The full supplementary evidence package contains all condition-level estimates, confidence intervals, corrected comparisons, optimizer diagnostics, model digests, prompt templates, blind-audit records, and deterministic asset checksums. No new model calls are required to reproduce any metric or figure reported here.
