# Design amendment A1: deterministic underlength retry

**Parent design:** `persona-relevance-v2-100`
**Amended design:** `persona-relevance-v2-100-a1`
**Date:** 2026-08-03
**Timing:** after operational Phase E preflight and before confirmatory collection

The parent design remains immutable. Its balanced preflight passed five of six model/domain
partitions but Llama/music produced at least 10 grounded items for 11 of 14 queries (78.6%),
below the frozen 90% operational gate. No fairness comparisons were computed or inspected.

## Amendment

Every query first uses the unchanged frozen prompt and temperature 0.7. If provider-free
grounding yields fewer than 10 items, issue exactly one retry with the same system prompt,
persona, trait wording, candidate pool, and item order. Append only the frozen format correction
stored in `config/full_run_v2_100_a1.yaml` and use retry temperature 0.0. Never retry for taste,
relevance, fairness, or item identity. Accept the second attempt even if it remains underlength.

The immutable record preserves both raw responses, both temperatures, the retry prompt, selected
attempt index, and combined token/time accounting. Retry status is an operational diagnostic and
must be reported by model/domain/condition. Primary and sensitivity list-handling rules remain
unchanged. Query identities include the new design and collection-protocol versions, preventing
resume from parent-design records.

## Preflight evidence

The seed-fixed Llama/music amendment preflight reached 13/14 top-10 lists (92.9%) and passed the
unchanged 90% gate. Two initial responses triggered retry; one reached 10 and one remained at 9.
The complete attempts are in `data/audits/preflight_v2_100_a1_llama_music.json`.

No population, relevance label, candidate pool, trait wording, phrasing, model snapshot, SESOI,
outcome, analysis model, correction family, or exclusion rule changed. Full collection remains
blocked until the amended bundle is frozen, verified, and the full-stage permission is explicitly
opened.
