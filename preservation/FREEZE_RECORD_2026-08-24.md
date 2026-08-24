# Evidence freeze record — 2026-08-24

## Status

The local integrity freeze for the `persona-relevance-v2-100-a1` confirmatory collection is
complete. An independent copy to a second device or institutional repository is still pending.

No source query record, dataset file, or existing analysis output was modified by this process.

## Complete evidence inventory

- Inventory files: 81,549
- Inventory bytes: 10,761,205,078
- Inventory SHA-256:
  `489389317bd7daabde9d6e525c2868c77e301ef691c770f526c500e95c73f6bb`
- Generated inventory:
  `preservation/generated/confirmatory-study-v1/evidence_inventory.tsv`

Evidence classification at freeze time:

| Class | Files | Bytes | Release status |
|---|---:|---:|---|
| Public candidate | 331 | 8,365,014 | Review before public release |
| Controlled | 81,193 | 3,864,549,653 | Privacy and license review required |
| Restricted | 25 | 6,888,290,411 | Private preservation only |

## Confirmatory query archives

Each archive contains exactly 13,201 files: 13,200 immutable query records and one run manifest.
Each archive was listed after compression, its internal file count was compared with the source,
and its SHA-256 was recalculated independently after the archive script completed.

| Model | Domain | Archive MiB | SHA-256 |
|---|---|---:|---|
| Gemma3 12B | movie | 35.03 | `ed439af5e512d82ba53b1eed119b03bda29b68c04608dae724364c1b5416a3e6` |
| Gemma3 12B | music | 44.68 | `e4e88c33492723118c6b21c168cdba465279ae35be31d7836cf2f8fbfbe940f0` |
| Llama 3.1 8B | movie | 36.82 | `c3e556e334e2fedc2d3bece9fc64c04a40e6dfdd348fb0557801a86452f39cff` |
| Llama 3.1 8B | music | 46.86 | `987a89f595e93cc668ea92f6a88848b9a550e3145b3e3c64534698c76710da1b` |
| Qwen3 8B | movie | 36.52 | `d6a952bc516717136db2d1c7ed70a65d5ead5ea9ab4287adcc187edcae932718` |
| Qwen3 8B | music | 45.78 | `5336eb02e30bf4e7672005896a83ab13bbebe868205f5e2821c1d3219cb1ab1d` |

- Combined archive size: 257,619,839 bytes (245.69 MiB)
- Archive manifest SHA-256:
  `33e9574820c18cd5bf6a141b308afb05bfe00980369bac7c56417d3bd44ee218`
- Archive manifest:
  `preservation/generated/confirmatory-study-v1/partition_archive_manifest.tsv`

## Supporting evidence archives

The independently downloadable dataset archives are preserved instead of duplicating every
extracted source file. The full inventory still records hashes for all extracted files, while the
download archives reproduce them under the documented loaders and checksums.

| Evidence class | Contents | Archive MiB | SHA-256 |
|---|---|---:|---|
| Restricted | Four original MovieLens/LastFM downloads and original wording-audit workbook | 1,439.94 | `7b4c2941cea52313100a2b6a20e415c23570e1e3dd4cca9852d9257c063ac439` |
| Controlled | Code, frozen designs, audits, derived tables, documentation, and report assets | 2.10 | `6050bb10048e848961d41ae119784099c47f4f22583ea1dd3dcb9d417ceb98ef` |

- Supporting archive manifest SHA-256:
  `4de13f5c27c440a5457c3cefce05e05ded98414e23a5e52e4a377f5e70bf6ce5`
- Total generated backup package: approximately 1.673 GiB.

## Known gap

The 26 domain-prefixed `confirmatory-analysis-v1` tables documented under the former account path
`C:\Users\yahu25\.codex\visualizations\2026\08\03\019fc76d-e4b9-72c2-97b1-00da6f09b6c0`
were not available on the current workstation. They are recorded as missing derived evidence in
`preservation/KNOWN_GAPS.md`. The 79,200 immutable query records needed to regenerate them remain
present and verified.

## Pending completion conditions

1. Copy the entire `preservation/generated/confirmatory-study-v1` directory to independent
   storage and recompute all three manifest hashes and all eight archive hashes at the destination.
2. Curate and commit the scientific code, frozen configurations, audits, and documentation without
   committing controlled or restricted evidence.
3. Add a durable Git remote and release tag after the clean-environment test gate passes.
