# Confirmatory collection status log

This is a dated operational snapshot, not a live dashboard. Authoritative status is the
partition manifest plus immutable Parquet count.

## Snapshot: 2026-08-06 14:48 CEST

| Sequence | Partition | Records | Status |
|---:|---|---:|---|
| 1 | Qwen/movie | 13,200/13,200 | Completed and final verification passed |
| 2 | Qwen/music | 7,899/13,200 | In progress, attempt 2 |
| 3 | Llama/movie | 0/13,200 | Pending |
| 4 | Llama/music | 0/13,200 | Pending |
| 5 | Gemma/movie | 0/13,200 | Pending |
| 6 | Gemma/music | 0/13,200 | Pending |

Overall immutable confirmatory records at this snapshot: **21,099/79,200 (26.64%)**.

## Qwen/movie attempt history

| Attempt | Started UTC | Ended UTC | Status | Reason |
|---:|---|---|---|---|
| 1 | 2026-08-03 12:46:16 | 2026-08-03 18:02:57 | Failed/interrupted | `KeyboardInterrupt` safe pause |
| 2 | 2026-08-04 10:24:50 | 2026-08-04 19:07:36 | Failed/interrupted | `KeyboardInterrupt` safe pause |
| 3 | 2026-08-05 11:13:00 | 2026-08-05 14:23:26 | Completed | 13,200 records |

The completed resolved digest is
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
Both interruptions were expected, documented, and resumed without duplicate records.

## Qwen/music attempt history

| Attempt | Started UTC | Ended UTC | Status | Reason |
|---:|---|---|---|---|
| 1 | 2026-08-05 14:37:24 | 2026-08-05 19:07:10 | Failed/interrupted | `KeyboardInterrupt` safe pause |
| 2 | 2026-08-06 09:35:59 | Open | In progress | Resumed same partition |

Observed steady running speed after resume was approximately 17 records/minute. Startup after
resume was slower only while scanning existing files. Model placement and temperature checks were
normal.

## Recordkeeping rule

Append a dated snapshot after each material pause, resume, failure, or completed partition. Do not
edit older snapshots to make the run look uninterrupted. Interruption provenance is part of the
reproducibility record.
