"""Build a parallel SHA-256 inventory without importing project dependencies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


TARGETS = (
    "AGENTS.md",
    "README.md",
    "CITATION.cff",
    "LICENSE",
    "pyproject.toml",
    "uv.lock",
    "research_proposal_recllm_item_side_fairness (1).md",
    "progress.md",
    "progress_2026-08-06.md",
    "progress_2026-08-07.md",
    "progress_2026-08-10.md",
    "progress_2026-08-13.md",
    "progress_2026-08-15.md",
    "Blind Wording Audit — Form Content (Responses) (1).xlsx",
    "config",
    "data/raw",
    "data/processed",
    "data/audits",
    "data/relevance_labels",
    "docs",
    "documentation",
    "src",
    "tests",
    "outputs/queries",
    "outputs/tables",
    "outputs/manuscript_assets",
    "_report_work/assets",
    "_report_work/build_final_report.py",
    "_report_work/report_v6.pdf",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_class(relative: str) -> str:
    if relative.startswith(("data/raw/", "data/processed/")) or relative == (
        "Blind Wording Audit — Form Content (Responses) (1).xlsx"
    ):
        return "restricted"
    if relative.startswith(("outputs/queries/", "data/relevance_labels/")):
        return "controlled"
    return "public_candidate"


def category(relative: str) -> str:
    prefixes = (
        ("outputs/queries/", "query_records"),
        ("outputs/tables/", "analysis_and_verification"),
        ("data/raw/", "raw_datasets"),
        ("data/processed/", "processed_datasets"),
        ("data/audits/", "audit_records"),
        ("data/relevance_labels/", "persona_and_relevance_artifacts"),
        ("config/", "configuration"),
        ("src/", "source_code"),
        ("tests/", "tests"),
        ("docs/", "documentation"),
        ("documentation/", "documentation"),
        ("_report_work/", "report_assets"),
        ("outputs/manuscript_assets/", "report_assets"),
    )
    for prefix, name in prefixes:
        if relative.startswith(prefix):
            return name
    return "project_metadata"


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return (completed.stdout + completed.stderr).strip()


def summarize(rows: list[dict[str, object]], key: str) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for row in rows:
        name = str(row[key])
        group = result.setdefault(name, {"file_count": 0, "total_bytes": 0})
        group["file_count"] += 1
        group["total_bytes"] += int(row["size_bytes"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-id", default="confirmatory-study-v1")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    generated_root = project_root / "preservation" / "generated" / args.study_id
    generated_root.mkdir(parents=True, exist_ok=True)

    unique: dict[Path, None] = {}
    for target_name in TARGETS:
        target = project_root / target_name
        if not target.exists():
            continue
        if target.is_file():
            unique[target] = None
        else:
            for base, _, names in os.walk(target):
                for name in names:
                    unique[Path(base) / name] = None
    files = list(unique)
    print(f"Discovered {len(files)} evidence files", flush=True)

    rows: list[dict[str, object]] = []
    workers = max(1, min(args.workers, 32))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(sha256_file, path): path for path in files}
        for index, future in enumerate(as_completed(futures), 1):
            path = futures[future]
            stat = path.stat()
            relative = path.relative_to(project_root).as_posix()
            rows.append(
                {
                    "relative_path": relative,
                    "size_bytes": stat.st_size,
                    "last_write_utc": datetime.fromtimestamp(
                        stat.st_mtime, timezone.utc
                    ).isoformat(),
                    "sha256": future.result(),
                    "evidence_class": evidence_class(relative),
                    "category": category(relative),
                }
            )
            if index % 5000 == 0:
                print(f"Hashed {index} of {len(files)} files", flush=True)

    rows.sort(key=lambda row: str(row["relative_path"]))
    inventory_path = generated_root / "evidence_inventory.tsv"
    with inventory_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    inventory_hash = sha256_file(inventory_path)

    summary = {
        "schema_version": 1,
        "study_id": args.study_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "inventory_file": inventory_path.name,
        "inventory_sha256": inventory_hash,
        "total_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "evidence_classes": summarize(rows, "evidence_class"),
        "categories": summarize(rows, "category"),
        "git": {
            "head": git_output(project_root, "rev-parse", "HEAD"),
            "status": git_output(project_root, "status", "--short", "--branch"),
            "remotes": git_output(project_root, "remote", "-v"),
        },
        "known_missing_analysis_archive": (
            "C:\\Users\\yahu25\\.codex\\visualizations\\2026\\08\\03\\"
            "019fc76d-e4b9-72c2-97b1-00da6f09b6c0"
        ),
    }
    summary_path = generated_root / "preservation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Inventory: {inventory_path}")
    print(f"Inventory SHA256: {inventory_hash}")
    print(f"Summary: {summary_path}")
    print(f"Files: {len(rows)}")
    print(f"Bytes: {summary['total_bytes']}")


if __name__ == "__main__":
    main()
