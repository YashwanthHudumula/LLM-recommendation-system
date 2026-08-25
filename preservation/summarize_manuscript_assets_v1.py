"""Build an independently verified audit of the frozen manuscript assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "outputs" / "manuscript_assets" / "version=manuscript-assets-v1"
MANIFEST = ASSET_ROOT / "manifest.json"
OUTPUT = ROOT / "data" / "audits" / "manuscript_assets_v1_reproducibility.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> None:
    manifest: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = sorted(path for path in ASSET_ROOT.rglob("*") if path.is_file() and path != MANIFEST)
    declared = {str(record["path"]): record for record in manifest["inventory"]}
    failures: list[str] = []
    inventory: list[dict[str, Any]] = []
    for path in files:
        rel = relative(path)
        digest = sha256_file(path)
        record = declared.get(rel)
        if record is None:
            failures.append(f"undeclared:{rel}")
        elif int(record["bytes"]) != path.stat().st_size or str(record["sha256"]) != digest:
            failures.append(f"mismatch:{rel}")
        inventory.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": digest})
    if len(declared) != len(files):
        failures.append(f"manifest_count:{len(declared)}!=filesystem_count:{len(files)}")
    if failures:
        raise ValueError("Manuscript asset verification failed: " + ", ".join(failures))
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    audit = {
        "schema_version": 1,
        "asset_version": manifest["asset_version"],
        "classification": "frozen manuscript figures and tables",
        "base_commit": base_commit,
        "asset_root": relative(ASSET_ROOT),
        "manifest_path": relative(MANIFEST),
        "manifest_sha256": sha256_file(MANIFEST),
        "spec_path": manifest["spec_path"],
        "spec_sha256": manifest["spec_sha256"],
        "source_audits": manifest["source_audits"],
        "figure_sets": 5,
        "figure_files": sum(path.suffix in {".pdf", ".png", ".svg"} for path in files),
        "table_sets": 5,
        "table_files": sum(path.suffix in {".csv", ".tex"} for path in files),
        "inventory": inventory,
    }
    OUTPUT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {relative(OUTPUT)} with {len(inventory)} independently verified files")


if __name__ == "__main__":
    main()
