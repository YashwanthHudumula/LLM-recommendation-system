# Confirmatory design and collection record

## 1. Frozen population

The confirmatory design uses 100 independent personas per domain. These are not renamed or
paraphrased copies of the six pilot preferences.

### Movies

- Source: MovieLens 25M.
- Eligible users: 59,812 under the frozen feasibility rules.
- Positive-rating threshold: 4.0.
- Minimum positive activity: 60.
- Construction fraction: 0.5.
- Preference text uses only construction-split top genres and decades.
- Relevance uses only held-out positive ratings.

### Music

- Source: LastFM-360K.
- Eligible users: 29,555 under the frozen feasibility rules.
- Minimum distinct artists: 60.
- Construction fraction: 0.5.
- Preference text uses only the construction-split top five artists by plays.
- Relevance uses only held-out artists.

Both domains passed: 100 profiles, 100 unique IDs, zero construction/evaluation leakage, zero
duplicate profile records, and no profile with insufficient held-out relevant opportunity. All
200 statements passed human wording review with no personality leakage, hidden controls, or raw
user fields. Dataset-native Unicode artist names were retained.

## 2. Counterfactual matrix

Each persona is crossed with ten Big-Five poles, one shared no-personality neutral framing, four
semantically validated phrasings, and three stochastic repeats.

| Unit | Count |
|---|---:|
| Framings per persona | 11 |
| Phrasing variants | 4 |
| Repeats | 3 |
| Records per persona/model/domain | 132 |
| Personas per domain | 100 |
| Records per model/domain | 13,200 |
| Records per domain across models | 39,600 |
| Complete collection | 79,200 |

Repeats estimate decoding variability and are not independent personas.

## 3. Candidate opportunity

Every persona has one deterministic 120-item pool held fixed across all counterfactual framings:

- 60 head items;
- 30 mid-popularity items;
- 30 tail items; and
- at least 30 held-out relevant candidates.

Candidate IDs are unique, display order is deterministic, and coded entries are grounded against
the full catalog. The v2 semantic phrasing gate used `all-MiniLM-L6-v2` at threshold 0.82; the
minimum cosine was 0.8834 for movies and 0.9033 for music.

## 4. Power and precision

The smallest effect of scientific interest is an absolute standardized within-persona
trait-pole-versus-neutral effect of 0.20 residual SD. A pre-results simulation used 200 datasets,
100 personas, four phrasings, three repeats, random-intercept SD 0.50, residual SD 1.0, and alpha
0.05.

| Simulation result | Value |
|---|---:|
| Power | 1.00 |
| Mean 95% CI width | 0.1601 |
| Median standard error | 0.0409 |
| Convergence rate | 1.00 |
| Failure rate | 0.00 |

## 5. Frozen model snapshots

| Key | Ollama model | Frozen digest prefix |
|---|---|---|
| `ollama_qwen3_8b` | `qwen3:8b` | `500a1f067a9f` |
| `ollama_llama3_1_8b` | `llama3.1:8b` | `46e0c10c039e` |
| `ollama_gemma3_12b` | `gemma3:12b` | `f4031aab637d` |

All use concurrency 1, context length 2,048, `think: false`, temperature 0.7 for the first
attempt, and local inference cost USD 0.

## 6. A1 retry contract

If the first provider-free grounded result contains fewer than 10 items, exactly one format-only
retry is issued at temperature 0.0. The candidate pool, ordering, persona, trait, and wording do
not change. The retry cannot be triggered by relevance, fairness, taste, or item identity.

Both attempts, temperatures, selected attempt, retry prompt, token counts, and timing remain in
the immutable record. The second attempt is final even if still short.

## 7. Frozen collection order

The order was selected before confirmatory results and cannot be changed in response to fairness
outcomes:

1. Qwen/movie
2. Qwen/music
3. Llama/movie
4. Llama/music
5. Gemma/movie
6. Gemma/music

Operational failures pause and resume the same partition.

## 8. Operational quality gates

Pause and diagnose when any of the following occurs:

- model digest differs from the configured snapshot;
- unique count, repeats, prompt hash, design hash, or resume identity fails;
- fewer than 95% of records contain at least one grounded item;
- fewer than 90% contain exactly 10 grounded positions;
- hallucination plus off-list incidence exceeds 2% of parsed titles; or
- writing, manifest, resume, temperature, or storage integrity fails.

These are operational gates only. Trait-level fairness outcomes are not inspected during
collection.

## 9. Confirmatory collection status

### Qwen/movie

- 13,200/13,200 immutable records.
- Manifest status `completed` after three resumable attempts.
- Resolved digest:
  `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
- 100% with at least one grounded item.
- 95.4394% with exactly 10 grounded items.
- Combined hallucination/off-list incidence 0.6101% of parsed titles.
- 1,303 retry records (9.8712%).
- Zero duplicate IDs, duplicate experimental identities, provenance mismatches, candidate-list
  duplicates, selected-attempt errors, or matches outside candidate pools.
- All 11 trait/level cells contain exactly 1,200 records.
- Final decision: passed.
- Manifest SHA256:
  `9ff1a20a9139d5e2938818e4a86f4eac369fb72d2f763675b7355adb4543e957`.

### Qwen/music

Collection is in progress and resumable. The authoritative count must be read from the partition
at the time of reporting. Operational checks during collection showed stable writing, the correct
model digest, full GPU placement, and approximately 17 records/minute. Music was faster than
movie because observed responses were shorter and retries less frequent.

### Remaining partitions

Llama/movie, Llama/music, Gemma/movie, and Gemma/music are pending. Final validation and backup
must occur after each partition before advancing in the frozen sequence.

## 10. Analysis embargo during collection

Only record integrity, format yield, bad-title incidence, tokens, runtime, hardware, and relevance
controls may be inspected. Trait-level user-side or item-side fairness comparisons must remain
unexamined until the complete collection is frozen and checksummed.
