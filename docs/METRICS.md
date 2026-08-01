# Metric specification

This file is the operational contract used by the code and manuscript. Any change to a
formula after collection must be versioned and disclosed; raw query records remain unchanged.

## User-side similarities

Let `R0` be a neutral top-K list and `Ra` its personality-conditioned counterfactual.

- **Jaccard@K** is `|R0 ∩ Ra| / |R0 ∪ Ra|` after set conversion.
- **SERP\*@K** follows the FaiRLLM authors' released notebook exactly: it sums
  `(K-rank_Ra(i)+2)` for overlapping items and divides by `2K(K+1)`. It rewards
  overlap near the top of `Ra`. This historical scale is not normalized to one; do not
  rescale it when comparing against the published FaiRLLM tables.
- **PRAG\*@K** counts order-agreeing pairs in `Ra`, treating an item absent from `R0`
  as ranked after present items, and divides by the number of item pairs in `Ra`.
- **SNSR** is the range of mean sensitive-to-neutral similarities across trait levels.
- **SNSV** is their population standard deviation (`ddof=0`). Although called a
  “variance” historically, the published formula takes the square root.
- **PAFS** is `1 - mean(|sim(p)-mean(sim)|)` across personality-conditioned prompts.

Higher Jaccard/SERP\*/PRAG\*/PAFS means more stability; higher SNSR/SNSV means more
disparity. RQ3 converts similarities to harm with `1-similarity` before correlation.

Primary sources: Zhang et al. (2023), DOI `10.1145/3604915.3608860`; Sah et al.
(2025), arXiv `2504.07801`.

## Item-side metrics

Let `x_i` be aggregate exposure for catalog item `i`, including `x_i=0` for items never
recommended, and `s_i=x_i/sum(x)`.

- **Gini** uses the standard sorted-sample formula over the complete catalog. Excluding
  zeros would answer a different and artificially optimistic question.
- **HHI** is `sum(s_i²)`. The raw HHI is primary; normalized HHI is available for
  sensitivity analysis.
- **ARP@K** is the exposure-weighted mean interaction count. If a catalog lacks raw counts,
  the code falls back to reciprocal popularity rank and this fallback must be disclosed.
- **Catalog coverage** is the fraction of all catalog items exposed at least once.
- **Long-tail coverage** is the fraction of tail-tier items exposed at least once.

For group `G`, recommendation proportion `GP(G)` and reference proportion `GR(G)` yield
`GU(G)=GP(G)-GR(G)`. Then `MGU=mean(|GU(G)|)` and
`DGU=max(GU(G))-min(GU(G))`.

Jiang et al. (2024), DOI `10.1145/3589334.3648158`, use historical liked-item share as
the reference in a fine-tuned sequential recommender. This zero-shot study has no training
history inside the model, so the primary adaptation uses availability in the fixed candidate
pool. If independently constructed persona histories exist, report that historical reference
as a sensitivity analysis. The exported group-exposure table exposes every `GP`, `GR`, and
`GU` value.

## Utility controls

Precision@K and NDCG@K require independently fixed `relevant_item_ids` for each base
persona. They are never inferred from the LLM response. If labels are absent, the pipeline
returns missing values plus `relevance_labels_available=false`; it does not manufacture a
ground truth from title keywords.

## Statistical contract

- Aggregate-metric intervals resample persona clusters, retaining every repeat/phrasing row.
- Sensitive-minus-neutral intervals use paired persona resampling.
- Mixed-effects models use trait, trait level, phrasing, and model (where varying) as fixed
  effects and persona as a random intercept.
- Benjamini-Hochberg controls FDR across each emitted family of tests.
- RQ3 uses Spearman rank correlation after aligning directions so higher always means more
  harm. `|rho| < 0.20` or `p >= .05` is **Independent**; significant positive effects are
  **Concordant**; significant negative effects are **Inverse**. Thresholds are configured
  before analysis.
