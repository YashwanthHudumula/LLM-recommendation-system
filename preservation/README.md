# Confirmatory-study preservation

This directory contains the reproducible procedure for freezing the evidence behind the
`persona-relevance-v2-100-a1` confirmatory study. Generated inventories and archives are written
under `preservation/generated/` and are intentionally excluded from Git because they include
large files and controlled research evidence.

The preservation workflow has three evidence classes:

- `public_candidate`: code, configuration, documentation, audit summaries, and derived tables
  that may be suitable for a public repository after final review.
- `controlled`: de-identified raw model responses, candidate pools, and derived persona artifacts.
  These require a privacy, dataset-license, and model-output-license review before release.
- `restricted`: downloaded or processed MovieLens/LastFM source data and the original wording
  survey workbook. These are preserved privately and are not public-release candidates.

Run `build_evidence_inventory.ps1` from PowerShell to generate byte counts, SHA-256 hashes,
Git-state metadata, and a machine-readable preservation summary. The generated inventory is an
integrity record; it does not modify any source evidence.

The six confirmatory query partitions should subsequently be packaged as one archive per
model/domain. Archive hashes must be recorded and independently verified after copying to a
second storage device or institutional repository.
