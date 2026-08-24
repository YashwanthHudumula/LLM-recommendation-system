"""Hash confirmatory analysis packages and quantify sensitivity concordance."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_float(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def compare_metrics(
    primary: pd.DataFrame,
    sensitivity: pd.DataFrame,
    *,
    keys: list[str],
    metrics: list[str],
) -> dict[str, dict[str, float | int | None]]:
    merged = primary[keys + metrics].merge(
        sensitivity[keys + metrics],
        on=keys,
        how="inner",
        suffixes=("_primary", "_sensitivity"),
        validate="one_to_one",
    )
    result: dict[str, dict[str, float | int | None]] = {}
    for metric in metrics:
        left = merged[f"{metric}_primary"].to_numpy(dtype=float)
        right = merged[f"{metric}_sensitivity"].to_numpy(dtype=float)
        constant = len(left) < 2 or np.ptp(left) == 0 or np.ptp(right) == 0
        rho = np.nan if constant else spearmanr(left, right).statistic
        result[metric] = {
            "matched_rows": len(merged),
            "spearman_rho": finite_float(float(rho)),
            "sign_agreement": finite_float(float(np.mean(np.sign(left) == np.sign(right)))),
            "mean_absolute_difference": finite_float(float(np.mean(np.abs(left - right)))),
            "maximum_absolute_difference": finite_float(float(np.max(np.abs(left - right)))),
        }
    return result


def rq3_concordance(primary: pd.DataFrame, sensitivity: pd.DataFrame) -> dict[str, Any]:
    keys = ["model", "domain", "user_metric", "item_metric"]
    merged = primary[[*keys, "scenario"]].merge(
        sensitivity[[*keys, "scenario"]],
        on=keys,
        how="inner",
        suffixes=("_primary", "_sensitivity"),
        validate="one_to_one",
    )
    changed = merged.loc[merged["scenario_primary"] != merged["scenario_sensitivity"]]
    return {
        "matched_rows": len(merged),
        "scenario_agreement": float(
            np.mean(merged["scenario_primary"] == merged["scenario_sensitivity"])
        ),
        "changed_rows": len(changed),
        "changes": changed.to_dict(orient="records"),
    }


def fit_summary(package: Path) -> dict[str, Any]:
    mixed = pd.read_csv(package / "mixed_effects.csv")
    robust = pd.read_csv(package / "cluster_robust_effects.csv")
    return {
        "mixed_effects_rows": len(mixed),
        "mixed_effects_failures": int((mixed["term"] == "__model_failure__").sum()),
        "mixed_effects_warning_outcomes": sorted(
            mixed.loc[mixed.get("warnings", pd.Series(dtype=str)).fillna("").ne(""), "outcome"]
            .dropna()
            .unique()
            .tolist()
        ),
        "cluster_robust_rows": len(robust),
        "cluster_robust_failures": int((robust["term"] == "__model_failure__").sum()),
        "cluster_robust_sesoi_terms": int(
            robust.get("meets_standardized_sesoi", pd.Series(dtype=bool)).fillna(False).sum()
        ),
    }


def file_record(path: Path, project_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(project_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/audits/confirmatory_analysis_v2_reproducibility.json"),
    )
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    analysis_root = project_root / "outputs/tables/analysis/design=persona-relevance-v2-100-a1"
    packages = sorted(
        path
        for path in analysis_root.glob("domain=*/models=*/analysis=confirmatory-analysis-v2*")
        if (path / "analysis_manifest.json").is_file()
        and (path / "cluster_robust_effects.csv").is_file()
    )
    if len(packages) != 6:
        raise RuntimeError(f"Expected six completed analysis packages, found {len(packages)}")

    all_files = [
        path for package in packages for path in sorted(package.iterdir()) if path.is_file()
    ]
    with ThreadPoolExecutor() as executor:
        inventory = list(executor.map(lambda path: file_record(path, project_root), all_files))

    package_records: list[dict[str, Any]] = []
    frames: dict[tuple[str, str], dict[str, pd.DataFrame]] = {}
    for package in packages:
        manifest = json.loads((package / "analysis_manifest.json").read_text(encoding="utf-8"))
        domain = str(manifest["domain"])
        view = str(manifest.get("analysis_view", "primary"))
        query_records = int(manifest["query_records"])
        source_records = int(manifest.get("source_query_records", query_records))
        package_records.append(
            {
                "domain": domain,
                "analysis_version": manifest["analysis_version"],
                "analysis_view": view,
                "source_query_records": source_records,
                "query_records": query_records,
                "retention_rate": query_records / source_records,
                "fit_summary": fit_summary(package),
                "package_path": package.relative_to(project_root).as_posix(),
            }
        )
        frames[(domain, view)] = {
            "item": pd.read_csv(package / "item_side_deltas.csv"),
            "user": pd.read_csv(package / "user_side_metrics.csv"),
            "rq3": pd.read_csv(package / "rq3_correlations.csv"),
        }

    concordance: list[dict[str, Any]] = []
    item_metrics = [
        "delta_gini",
        "delta_hhi",
        "delta_arp",
        "delta_catalog_coverage",
        "delta_long_tail_coverage",
        "delta_popularity_mgu",
        "delta_popularity_dgu",
        "delta_genre_mgu",
        "delta_genre_dgu",
    ]
    condition_keys = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    for domain in ("movie", "music"):
        primary = frames[(domain, "primary")]
        for view in ("exact-10-grounded", "exclude-flagged-records"):
            sensitivity = frames[(domain, view)]
            concordance.append(
                {
                    "domain": domain,
                    "analysis_view": view,
                    "item_side": compare_metrics(
                        primary["item"],
                        sensitivity["item"],
                        keys=condition_keys,
                        metrics=item_metrics,
                    ),
                    "user_side": compare_metrics(
                        primary["user"],
                        sensitivity["user"],
                        keys=condition_keys,
                        metrics=["jaccard", "serp", "prag"],
                    ),
                    "rq3": rq3_concordance(primary["rq3"], sensitivity["rq3"]),
                }
            )

    output = (project_root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "base_git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
        ).strip(),
        "environment_lock_sha256": sha256_file(project_root / "uv.lock"),
        "packages": package_records,
        "concordance": concordance,
        "inventory": inventory,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(inventory)} hashed files")


if __name__ == "__main__":
    main()
