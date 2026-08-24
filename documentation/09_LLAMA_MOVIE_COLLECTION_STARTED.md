# Llama/movie confirmatory collection started

**Snapshot:** 2026-08-06 20:18:53 CEST
**Design:** `persona-relevance-v2-100-a1`
**Protocol:** `closed-catalog-v2-a1-retry`
**Sequence position:** 3 of 6

## Current status

- Partition: `ollama_llama3_1_8b` / movie.
- Started: 2026-08-06 18:13:04 UTC (20:13:04 CEST).
- Records: 91/13,200 (0.69%).
- Remaining: 13,109.
- Manifest: attempt 1, `in_progress`.
- Early observed speed: approximately 15.3-16.7 records/minute.
- Early estimated uninterrupted completion: approximately 2026-08-07 10:00-10:30 CEST.
- Model: `llama3.1:8b`, frozen digest prefix `46e0c10c039e`.
- Ollama placement: 100% GPU.
- GPU snapshot: 97% utilization, 5,848/16,380 MiB, 79 C, 69.22 W.
- Latest record was written two seconds before the status snapshot.

The early completion estimate is provisional. It should be recalculated after at least 30 minutes
because response length and A1 retry frequency vary across prompts.

## Overall collection checkpoint

Both Qwen partitions are complete and passed final verification. Including this Llama/movie
snapshot, the project contains **26,491/79,200 confirmatory records (33.45%)**.

| Sequence | Partition | Status at snapshot |
|---:|---|---|
| 1 | Qwen/movie | 13,200/13,200; passed |
| 2 | Qwen/music | 13,200/13,200; passed |
| 3 | Llama/movie | 91/13,200; in progress |
| 4 | Llama/music | Pending |
| 5 | Gemma/movie | Pending |
| 6 | Gemma/music | Pending |

No confirmatory trait-level fairness outcomes have been inspected. Monitoring remains limited to
record integrity, grounding/format quality, runtime, thermals, model identity, and storage health.

## Resume command

If safely paused, resume the same partition with:

```powershell
cd "D:\LLM recommend"
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_llama3_1_8b --domain movie --stage full
```

The collector will validate the existing manifest and skip completed records.
