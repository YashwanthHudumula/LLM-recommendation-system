"""Verify copied analysis packages against the v2 reproducibility inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(record: dict[str, Any], destination: Path) -> dict[str, Any]:
    path = destination / Path(str(record["path"]))
    if not path.is_file():
        return {"path": record["path"], "status": "missing"}
    if path.stat().st_size != int(record["size_bytes"]):
        return {
            "path": record["path"],
            "status": "size_mismatch",
            "expected": record["size_bytes"],
            "observed": path.stat().st_size,
        }
    observed = sha256_file(path)
    if observed != record["sha256"]:
        return {
            "path": record["path"],
            "status": "hash_mismatch",
            "expected": record["sha256"],
            "observed": observed,
        }
    return {"path": record["path"], "status": "verified"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    audit = args.audit.resolve()
    destination = args.destination.resolve()
    records = json.loads(audit.read_text(encoding="utf-8"))["inventory"]
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda row: verify(row, destination), records))
    failures = [result for result in results if result["status"] != "verified"]
    receipt = {
        "schema_version": 1,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "audit": str(audit),
        "audit_sha256": sha256_file(audit),
        "destination": str(destination),
        "files_expected": len(records),
        "files_verified": len(records) - len(failures),
        "failures": failures,
    }
    output = args.receipt.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Verified {len(records) - len(failures)}/{len(records)} analysis files")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
