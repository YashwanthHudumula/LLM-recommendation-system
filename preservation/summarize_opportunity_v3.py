"""Build the checksummed opportunity-adjusted v3 reproducibility audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_ROOT = ROOT / "outputs" / "tables" / "analysis" / "design=persona-relevance-v2-100-a1"
MODEL_SET = "models=ollama_gemma3_12b+ollama_llama3_1_8b+ollama_qwen3_8b"
PROTOCOL = ROOT / "config" / "opportunity_sensitivity_v1.yaml"
OUTPUT = ROOT / "data" / "audits" / "opportunity_analysis_v3_reproducibility.json"
KEYS = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
METRICS = [
    "opportunity_gini",
    "opportunity_hhi",
    "opportunity_normalized_hhi",
    "opportunity_coverage",
    "opportunity_long_tail_coverage",
]
RAW_PAIRS = {
    "gini": "opportunity_gini",
    "hhi": "opportunity_hhi",
    "catalog_coverage": "opportunity_coverage",
    "long_tail_coverage": "opportunity_long_tail_coverage",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def finite_float(value: Any) -> float | None:
    number = float(value)
    return number if np.isfinite(number) else None


def concordance(left: pd.Series, right: pd.Series) -> dict[str, float | None]:
    rho = spearmanr(left.to_numpy(dtype=float), right.to_numpy(dtype=float)).statistic
    return {
        "spearman_rho": finite_float(rho),
        "sign_agreement": float((np.sign(left) == np.sign(right)).mean()),
        "rows": len(left),
    }


def package_path(domain: str, suffix: str = "") -> Path:
    name = "analysis=confirmatory-analysis-v3-opportunity"
    if suffix:
        name += f"-{suffix}"
    return ANALYSIS_ROOT / f"domain={domain}" / MODEL_SET / name


def source_v2_path(domain: str) -> Path:
    return ANALYSIS_ROOT / f"domain={domain}" / MODEL_SET / "analysis=confirmatory-analysis-v2"


def summarize_domain(domain: str) -> dict[str, Any]:
    primary = package_path(domain)
    metrics = pd.read_csv(primary / "opportunity_adjusted_metrics.csv")
    deltas = pd.read_csv(primary / "opportunity_adjusted_deltas.csv")
    intervals = pd.read_csv(primary / "opportunity_adjusted_delta_bootstrap_cis.csv")
    intervals["excludes_zero"] = (intervals["delta_ci_lower"] > 0) | (
        intervals["delta_ci_upper"] < 0
    )

    means: list[dict[str, Any]] = []
    mean_columns = [
        "opportunity_gini",
        "opportunity_normalized_hhi",
        "opportunity_coverage",
        "opportunity_long_tail_coverage",
        "eligible_item_count",
    ]
    for model, group in metrics.groupby("model"):
        means.append(
            {
                "model": model,
                **{column: finite_float(group[column].mean()) for column in mean_columns},
            }
        )

    magnitudes = {
        metric: {
            "mean_absolute_delta": finite_float(deltas[f"delta_{metric}"].abs().mean()),
            "maximum_absolute_delta": finite_float(deltas[f"delta_{metric}"].abs().max()),
        }
        for metric in METRICS
    }
    significant = [
        {
            "model": model,
            "metric": metric,
            "intervals_excluding_zero": int(group["excludes_zero"].sum()),
            "intervals_total": len(group),
        }
        for (model, metric), group in intervals.groupby(["model", "metric"])
    ]

    raw = pd.read_csv(source_v2_path(domain) / "item_side_deltas.csv")
    merged = raw.merge(deltas, on=KEYS, validate="one_to_one")
    raw_concordance = {
        raw_metric: concordance(
            merged[f"delta_{raw_metric}"], merged[f"delta_{opportunity_metric}"]
        )
        for raw_metric, opportunity_metric in RAW_PAIRS.items()
    }

    sensitivity: dict[str, dict[str, dict[str, float | None]]] = {}
    for view in ("exact10", "unflagged"):
        view_deltas = pd.read_csv(package_path(domain, view) / "opportunity_adjusted_deltas.csv")
        compared = deltas.merge(view_deltas, on=KEYS, suffixes=("_primary", "_sensitivity"))
        sensitivity[view] = {
            metric: concordance(
                compared[f"delta_{metric}_primary"],
                compared[f"delta_{metric}_sensitivity"],
            )
            for metric in METRICS
        }

    return {
        "domain": domain,
        "condition_rows": len(metrics),
        "sensitive_delta_rows": len(deltas),
        "metric_means_by_model": means,
        "delta_magnitude": magnitudes,
        "bootstrap_intervals_by_model": significant,
        "raw_vs_opportunity_delta_concordance": raw_concordance,
        "primary_vs_sensitivity_concordance": sensitivity,
    }


def main() -> None:
    packages = sorted(
        path
        for domain in ("movie", "music")
        for path in (
            package_path(domain),
            package_path(domain, "exact10"),
            package_path(domain, "unflagged"),
        )
    )
    inventory = []
    package_summaries = []
    for package in packages:
        manifest = json.loads((package / "analysis_manifest.json").read_text(encoding="utf-8"))
        files = sorted(path for path in package.iterdir() if path.is_file())
        package_summaries.append(
            {
                "path": relative(package),
                "analysis_view": manifest["analysis_view"],
                "query_records": manifest["query_records"],
                "bootstrap_resamples": manifest.get(
                    "bootstrap_resamples", manifest.get("opportunity_bootstrap_resamples")
                ),
                "files": len(files),
            }
        )
        inventory.extend(
            {
                "path": relative(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        )
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    audit = {
        "schema_version": 1,
        "analysis_family": "confirmatory-analysis-v3-opportunity",
        "classification": "post-collection protocol-aligned sensitivity",
        "base_commit": base_commit,
        "opportunity_protocol": relative(PROTOCOL),
        "opportunity_protocol_sha256": sha256_file(PROTOCOL),
        "packages": package_summaries,
        "domains": [summarize_domain(domain) for domain in ("movie", "music")],
        "inventory": inventory,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {relative(OUTPUT)} with {len(inventory)} checksummed files")


if __name__ == "__main__":
    main()
