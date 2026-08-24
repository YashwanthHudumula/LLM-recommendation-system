# Reproducibility and operations

## 1. Environment

- Windows 11 workstation: `C334-0021`.
- GPU: NVIDIA RTX 2000 Ada Generation, 16,380 MiB VRAM.
- Recorded driver: 595.95.
- RAM: 32 GB DDR5.
- Python: 3.12.5.
- Ollama: 0.32.5 at workstation qualification.
- Environment locked by `uv.lock`, SHA256
  `99687297f3fad09232d43cde627f589eede5eea8e879e18be50c5e94ccc22a51`.
- Confirmatory collection runs from the external SSD project at `D:\LLM recommend`.

Do not update Ollama, model tags, NVIDIA drivers, prompts, configurations, or dependencies during
the confirmatory collection unless a documented versioned correction is required.

## 2. Verification commands

From PowerShell:

```powershell
cd "D:\LLM recommend"
uv sync --frozen
uv run pytest
uv run ruff check .
uv run mypy src
ollama list
nvidia-smi
```

The A1 release gate passed 45 tests, lint, and strict typing before confirmatory collection.

## 3. Collection commands

Use only the active A1 override and frozen sequence.

```powershell
cd "D:\LLM recommend"

uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_qwen3_8b --domain movie --stage full
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_qwen3_8b --domain music --stage full
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_llama3_1_8b --domain movie --stage full
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_llama3_1_8b --domain music --stage full
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_gemma3_12b --domain movie --stage full
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_gemma3_12b --domain music --stage full
```

Never run two collectors against the same partition. Do not reorder partitions in response to
intermediate fairness results.

## 4. Safe pause and resume

1. Focus the PowerShell window running collection.
2. Press `Ctrl+C` once.
3. Wait until the normal `PS ...>` prompt returns.
4. Close programs using the external drive.
5. Use Windows **Safely Remove Hardware / Eject**.
6. Disconnect only after Windows confirms safe removal.

To resume, reconnect under the same drive letter, enter the project folder, and run the exact same
model/domain command. The collector validates the manifest and design identity, records a new
attempt, reads existing records, and skips completed identities. The interrupted attempt is
recorded as failed with `KeyboardInterrupt`; this is expected provenance, not lost data.

Startup after a large partial partition may spend several minutes scanning existing Parquet files.
During that scan, a short rolling records/minute estimate will look artificially slow.

## 5. Power and workstation safety

The active Balanced power scheme was checked with sleep and hibernate disabled on AC and DC.
Nevertheless, university policy, forced updates, logoff rules, building power, or administrative
controls may override user settings. Long runs should be monitored according to institutional
rules.

Observed sustained Qwen operation used approximately 6-6.5 GB VRAM, 98-100% GPU utilization,
roughly 69 W, and 75-80 C. Brief 0-60% instantaneous GPU readings between requests are normal when
new records continue to appear.

## 6. Drive rules

- Only one computer may mount/write the external SSD at a time.
- Never unplug while Python, Ollama, an editor, antivirus, indexing, or another process is writing.
- Do not rename or delete `outputs/queries` during collection.
- Preserve partial partitions; they are the resume source.
- For methodological consistency, use the designated RTX workstation for all confirmatory model
  inference. A hardware switch requires a documented boundary and sensitivity analysis.

## 7. Partition closeout

After each 13,200-record partition:

1. Confirm manifest status `completed`.
2. Confirm 13,200 unique Parquet records.
3. Check zero duplicate IDs and experimental identities.
4. Check design/protocol/bundle/dataset provenance and model digest.
5. Check repeat indices 0, 1, and 2 and condition balance.
6. Evaluate the frozen operational quality gates without inspecting fairness outcomes.
7. Calculate a manifest SHA256.
8. Write a derived verification report under `outputs/tables`.
9. Copy the immutable partition, manifest, and verification report to independent storage.
10. Verify the backup checksum before advancing.

The Qwen/movie verification report is
`outputs/tables/full_partition_verification_persona-relevance-v2-100-a1_ollama_qwen3_8b_movie.json`.

## 8. Backup and recovery

A backup target must be independent of the active external SSD. Preserve the directory hierarchy
and never transform source Parquet during backup. Record source and destination checksums, date,
partition identity, and operator. A failed workstation does not invalidate completed files; resume
only after verifying the partial partition and frozen environment.

## 9. Full analysis commands

Provider-free analysis is run only after the complete collection is frozen:

```powershell
uv run recllm-analyze --stage full --domain movie
uv run recllm-analyze --stage full --domain music
```

Do not run confirmatory fairness analysis on a partial collection. Mitigation remains blocked
until RQ1-RQ4 outputs are frozen.

## 10. Publication and archive checklist

- Exact model snapshots and collection timestamps.
- Frozen configuration, lockfile, code revision, and design/analysis hashes.
- Dataset versions, checksums, licensing, and data-availability restrictions.
- Candidate-pool construction and matching yield.
- Hallucination/off-list diagnostics and retry rates by partition/condition.
- Effect sizes, confidence intervals, raw and corrected p-values.
- Predeclared sensitivity analyses and convergence diagnostics.
- Ethics/privacy statement and limitations.
- De-identified records only where model/provider and dataset terms permit redistribution.
- Code and permitted artifacts archived with a persistent identifier/DOI.
