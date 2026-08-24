"""Verify a copied evidence tree against a frozen TSV inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify(row: dict[str, str], destination: Path) -> dict[str, object]:
    path = destination / Path(row["relative_path"])
    if not path.is_file():
        return {"relative_path": row["relative_path"], "status": "missing"}
    expected_size = int(row["size_bytes"])
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        return {
            "relative_path": row["relative_path"],
            "status": "size_mismatch",
            "expected_size": expected_size,
            "actual_size": actual_size,
        }
    actual_hash = sha256_file(path)
    if actual_hash != row["sha256"]:
        return {
            "relative_path": row["relative_path"],
            "status": "hash_mismatch",
            "expected_sha256": row["sha256"],
            "actual_sha256": actual_hash,
        }
    return {"relative_path": row["relative_path"], "status": "verified"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    inventory = args.inventory.resolve()
    destination = args.destination.resolve()
    with inventory.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    print(f"Verifying {len(rows)} evidence files under {destination}", flush=True)

    failures: list[dict[str, object]] = []
    verified = 0
    workers = max(1, min(args.workers, 32))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(verify, row, destination): row for row in rows}
        for index, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result["status"] == "verified":
                verified += 1
            else:
                failures.append(result)
            if index % 5000 == 0:
                print(f"Checked {index} of {len(rows)} files", flush=True)

    receipt = {
        "schema_version": 1,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "inventory": str(inventory),
        "inventory_sha256": sha256_file(inventory),
        "destination": str(destination),
        "expected_files": len(rows),
        "verified_files": verified,
        "failure_count": len(failures),
        "failures": failures,
        "all_verified": not failures,
    }
    receipt_path = args.receipt or destination / "preservation" / "evidence_copy_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Receipt: {receipt_path}")
    print(f"Verified: {verified}")
    print(f"Failures: {len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
