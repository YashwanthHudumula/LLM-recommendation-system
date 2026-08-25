"""Build immutable manuscript tables and publication figures from frozen analyses."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Annotated, Any

import matplotlib
import numpy as np
import pandas as pd
import typer
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = typer.Typer(add_completion=False)

MODELS = ["ollama_gemma3_12b", "ollama_llama3_1_8b", "ollama_qwen3_8b"]
MODEL_LABELS = {
    "ollama_gemma3_12b": "Gemma 3 12B",
    "ollama_llama3_1_8b": "Llama 3.1 8B",
    "ollama_qwen3_8b": "Qwen3 8B",
}
COLORS = {
    "ollama_gemma3_12b": "#0072B2",
    "ollama_llama3_1_8b": "#E69F00",
    "ollama_qwen3_8b": "#009E73",
}
DOMAINS = ["movie", "music"]
KEYS = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
OPP_METRICS = [
    "opportunity_gini",
    "opportunity_hhi",
    "opportunity_normalized_hhi",
    "opportunity_coverage",
    "opportunity_long_tail_coverage",
]
METRIC_LABELS = {
    "opportunity_gini": "Opportunity Gini",
    "opportunity_hhi": "Opportunity HHI",
    "opportunity_normalized_hhi": "Normalized opportunity HHI",
    "opportunity_coverage": "Opportunity coverage",
    "opportunity_long_tail_coverage": "Opportunity tail coverage",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_spec(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Manuscript asset specification must be a mapping")
    return loaded


def _verify_sources(spec: dict[str, Any]) -> None:
    for label, source in spec["source_audits"].items():
        path = Path(str(source["path"]))
        observed = _sha256(path)
        expected = str(source["sha256"])
        if observed != expected:
            raise ValueError(f"Frozen {label} audit hash mismatch: {observed} != {expected}")


def _analysis_dir(domain: str, version: str) -> Path:
    root = Path("outputs/tables/analysis/design=persona-relevance-v2-100-a1") / f"domain={domain}"
    matches = list(root.glob(f"models=*/analysis={version}"))
    if len(matches) != 1:
        raise ValueError(f"Expected one {domain}/{version} package, found {len(matches)}")
    return matches[0]


def _read_both(version: str, filename: str) -> pd.DataFrame:
    frames = [pd.read_csv(_analysis_dir(domain, version) / filename) for domain in DOMAINS]
    return pd.concat(frames, ignore_index=True)


def _style(base_font: float) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": base_font,
            "axes.titlesize": base_font + 1,
            "axes.labelsize": base_font,
            "legend.fontsize": base_font - 1,
            "xtick.labelsize": base_font - 1,
            "ytick.labelsize": base_font - 1,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "grid.linewidth": 0.6,
            "figure.dpi": 120,
            "savefig.bbox": "tight",
            "svg.hashsalt": "manuscript-assets-v1",
        }
    )


def _save_figure(fig: Any, base: Path, dpi: int) -> list[Path]:
    outputs: list[Path] = []
    for suffix in ("pdf", "svg", "png"):
        path = base.with_suffix(f".{suffix}")
        metadata: dict[str, Any]
        if suffix == "pdf":
            metadata = {"Creator": "recllm-item-fairness", "CreationDate": None, "ModDate": None}
        elif suffix == "svg":
            metadata = {"Creator": "recllm-item-fairness", "Date": None}
        else:
            metadata = {"Software": "recllm-item-fairness"}
        fig.savefig(path, dpi=dpi if suffix == "png" else None, metadata=metadata)
        outputs.append(path)
    plt.close(fig)
    return outputs


def _write_table(frame: pd.DataFrame, base: Path) -> list[Path]:
    csv_path = base.with_suffix(".csv")
    tex_path = base.with_suffix(".tex")
    frame.to_csv(csv_path, index=False, float_format="%.6g", lineterminator="\n")
    tex_path.write_text(
        frame.to_latex(index=False, escape=True, float_format=lambda value: f"{value:.4g}"),
        encoding="utf-8",
        newline="\n",
    )
    return [csv_path, tex_path]


def _primary_frames() -> dict[str, pd.DataFrame]:
    v2 = "confirmatory-analysis-v2"
    v3 = "confirmatory-analysis-v3-opportunity"
    return {
        "relevance": _read_both(v2, "relevance_metrics.csv"),
        "user": _read_both(v2, "user_side_metrics.csv"),
        "item": _read_both(v2, "item_side_metrics.csv"),
        "item_delta": _read_both(v2, "item_side_deltas.csv"),
        "rq3": _read_both(v2, "rq3_correlations.csv"),
        "opp": _read_both(v3, "opportunity_adjusted_metrics.csv"),
        "opp_delta": _read_both(v3, "opportunity_adjusted_deltas.csv"),
        "opp_ci": _read_both(v3, "opportunity_adjusted_delta_bootstrap_cis.csv"),
    }


def _figure_1(frames: dict[str, pd.DataFrame]) -> Any:
    rel = frames["relevance"].groupby(KEYS, as_index=False)["precision_at_k"].mean()
    data = rel.merge(frames["opp"], on=KEYS, validate="one_to_one")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.05), sharey=True)
    for ax, domain in zip(axes, DOMAINS, strict=True):
        subset = data[data["domain"] == domain]
        for model in MODELS:
            points = subset[subset["model"] == model]
            ax.scatter(
                points["precision_at_k"],
                points["opportunity_coverage"],
                s=16,
                alpha=0.38,
                color=COLORS[model],
                linewidths=0,
                label=MODEL_LABELS[model],
            )
            ax.scatter(
                points["precision_at_k"].mean(),
                points["opportunity_coverage"].mean(),
                s=54,
                color=COLORS[model],
                edgecolor="white",
                linewidth=0.8,
                marker="D",
                zorder=4,
            )
        ax.set_title(domain.title())
        ax.set_xlabel("Precision@10")
    axes[0].set_ylabel("Opportunity-adjusted catalog coverage")
    axes[1].legend(frameon=False, loc="best")
    fig.suptitle("Relevance-exposure opportunity trade-off", fontweight="bold")
    fig.text(0.5, -0.01, "Small points: conditions; diamonds: model means", ha="center", fontsize=8)
    fig.tight_layout()
    return fig


def _strongest_effects(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    deltas = frames["opp_delta"].copy()
    selected: list[tuple[str, pd.Series[Any]]] = []
    for domain in DOMAINS:
        for model in MODELS:
            group = deltas[(deltas["domain"] == domain) & (deltas["model"] == model)]
            for metric in ("opportunity_gini", "opportunity_coverage"):
                column = f"delta_{metric}"
                position = int(np.argmax(group[column].abs().to_numpy()))
                selected.append((metric, group.iloc[position]))
    long_rows: list[dict[str, Any]] = []
    ci = frames["opp_ci"]
    for metric, row in selected:
        match = ci[
            (ci["domain"] == row["domain"])
            & (ci["model"] == row["model"])
            & (ci["trait"] == row["trait"])
            & (ci["trait_level"] == row["trait_level"])
            & (ci["phrasing_variant"] == row["phrasing_variant"])
            & (ci["metric"] == metric)
        ]
        if len(match) != 1:
            raise ValueError("Could not uniquely match strongest effect to bootstrap interval")
        interval = match.iloc[0]
        long_rows.append(
            {
                "domain": row["domain"],
                "model": row["model"],
                "metric": metric,
                "trait": row["trait"],
                "trait_level": row["trait_level"],
                "phrasing_variant": row["phrasing_variant"],
                "delta": row[f"delta_{metric}"],
                "ci_lower": interval["delta_ci_lower"],
                "ci_upper": interval["delta_ci_upper"],
            }
        )
    result = pd.DataFrame(long_rows).drop_duplicates([*KEYS, "metric"])
    return result.sort_values(["metric", "domain", "model"]).reset_index(drop=True)


def _figure_2(effects: pd.DataFrame) -> Any:
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 4.5))
    for ax, metric in zip(axes, ("opportunity_gini", "opportunity_coverage"), strict=True):
        data = effects[effects["metric"] == metric].reset_index(drop=True)
        labels = [
            f"{str(row.domain).title()} · {MODEL_LABELS[str(row.model)]}\n"
            f"{row.trait} {row.trait_level}, {row.phrasing_variant}"
            for row in data.itertuples()
        ]
        y = np.arange(len(data))
        for position, (_, row) in enumerate(data.iterrows()):
            ax.errorbar(
                row["delta"],
                y[position],
                xerr=[[row["delta"] - row["ci_lower"]], [row["ci_upper"] - row["delta"]]],
                fmt="o",
                color=COLORS[str(row["model"])],
                capsize=2.5,
                markersize=5,
                linewidth=1.2,
            )
        ax.axvline(0, color="#444444", linewidth=0.8)
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlabel("Condition delta vs neutral")
        ax.set_title(METRIC_LABELS[metric])
    fig.suptitle(
        "Largest observed opportunity-adjusted effects (95% bootstrap CI)",
        fontweight="bold",
    )
    fig.text(
        0.5,
        -0.01,
        "Descriptive maximum per domain/model/metric; selection is not multiplicity-adjusted.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout()
    return fig


def _scenario_table(rq3: pd.DataFrame) -> pd.DataFrame:
    scenarios = rq3["scenario"].fillna("undefined").astype(str).str.lower()
    data = rq3.assign(scenario=scenarios)
    pivot = (
        data.groupby(["domain", "model", "scenario"]).size().unstack(fill_value=0).reset_index()
    )
    for name in ("concordant", "independent", "inverse", "undefined"):
        if name not in pivot:
            pivot[name] = 0
    pivot["total"] = pivot[["concordant", "independent", "inverse", "undefined"]].sum(axis=1)
    return pivot[["domain", "model", "concordant", "independent", "inverse", "undefined", "total"]]


def _figure_3(table: pd.DataFrame) -> Any:
    labels = [
        f"{str(row.domain).title()} · {MODEL_LABELS[str(row.model)]}"
        for row in table.itertuples()
    ]
    y = np.arange(len(table))
    fig, ax = plt.subplots(figsize=(7.1, 3.7))
    left = np.zeros(len(table))
    palette = {
        "concordant": "#0072B2",
        "independent": "#999999",
        "inverse": "#D55E00",
        "undefined": "#F0E442",
    }
    for scenario in ("concordant", "independent", "inverse", "undefined"):
        values = table[scenario].to_numpy(dtype=float)
        ax.barh(y, values, left=left, color=palette[scenario], label=scenario.title())
        left += values
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Number of user-side x item-side metric pairs")
    fig.suptitle("RQ3 relationship scenarios by model and domain", fontweight="bold", y=0.98)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    fig.subplots_adjust(top=0.79, left=0.22, right=0.98, bottom=0.17)
    return fig


def _figure_4(frames: dict[str, pd.DataFrame], audit: dict[str, Any]) -> Any:
    raw = frames["item_delta"]
    opp = frames["opp_delta"]
    data = raw.merge(opp, on=KEYS, validate="one_to_one", suffixes=("_raw", "_opp"))
    pairs = [
        ("delta_gini", "delta_opportunity_gini", "Gini"),
        ("delta_hhi", "delta_opportunity_hhi", "HHI"),
        ("delta_catalog_coverage", "delta_opportunity_coverage", "Catalog coverage"),
        (
            "delta_long_tail_coverage",
            "delta_opportunity_long_tail_coverage",
            "Long-tail coverage",
        ),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.7))
    audit_domains = {str(item["domain"]): item for item in audit["domains"]}
    for ax, (x_col, y_col, title) in zip(axes.flat, pairs, strict=True):
        notes = []
        for domain, marker in (("movie", "o"), ("music", "^")):
            subset = data[data["domain"] == domain]
            ax.scatter(
                subset[x_col], subset[y_col], s=18, alpha=0.55, marker=marker, label=domain.title()
            )
            key = title.lower().replace("-", "_").replace(" ", "_")
            record = audit_domains[domain]["raw_vs_opportunity_delta_concordance"][key]
            notes.append(f"{domain.title()}: rho={record['spearman_rho']:.2f}")
        ax.axhline(0, color="#555555", linewidth=0.7)
        ax.axvline(0, color="#555555", linewidth=0.7)
        ax.set_xlabel("Raw exposure delta")
        ax.set_ylabel("Opportunity-adjusted delta")
        ax.set_title(f"{title}\n" + "; ".join(notes))
        ax.ticklabel_format(axis="x", style="sci", scilimits=(-2, 2), useMathText=True)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
    axes[0, 0].legend(frameon=False)
    fig.suptitle("Raw and opportunity-adjusted condition effects", fontweight="bold")
    fig.tight_layout()
    return fig


def _figure_s1(audit: dict[str, Any]) -> Any:
    metrics = OPP_METRICS
    rows: list[list[float]] = []
    annotations: list[list[str]] = []
    labels: list[str] = []
    for domain in audit["domains"]:
        for view in ("exact10", "unflagged"):
            records = domain["primary_vs_sensitivity_concordance"][view]
            rows.append([float(records[metric]["spearman_rho"]) for metric in metrics])
            annotations.append(
                [
                    f"rho {records[metric]['spearman_rho']:.2f}\n"
                    f"{records[metric]['sign_agreement']:.0%}"
                    for metric in metrics
                ]
            )
            labels.append(f"{str(domain['domain']).title()} · {view}")
    values = np.asarray(rows)
    fig, ax = plt.subplots(figsize=(7.1, 3.0))
    image = ax.imshow(values, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            color = "white" if values[i, j] < 0.65 else "black"
            ax.text(j, i, annotations[i][j], ha="center", va="center", color=color, fontsize=7)
    short_labels = ["Gini", "HHI", "Normalized HHI", "Coverage", "Tail coverage"]
    ax.set_xticks(np.arange(len(metrics)), short_labels)
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.tick_params(axis="x", rotation=28)
    ax.grid(False)
    ax.set_title(
        "Primary-sensitivity concordance: rank rho and sign agreement", fontweight="bold"
    )
    fig.colorbar(image, ax=ax, label="Spearman rho", fraction=0.03, pad=0.02)
    fig.tight_layout()
    return fig


def _table_1(audit: dict[str, Any]) -> pd.DataFrame:
    packages = audit["packages"]
    rows = []
    for domain in DOMAINS:
        by_view = {p["analysis_view"]: p for p in packages if domain in p["path"]}
        primary_n = int(by_view["primary"]["query_records"])
        exact_n = int(by_view["exact-10-grounded"]["query_records"])
        clean_n = int(by_view["exclude-flagged-records"]["query_records"])
        domain_audit = next(item for item in audit["domains"] if item["domain"] == domain)
        eligible = int(domain_audit["metric_means_by_model"][0]["eligible_item_count"])
        rows.append(
            {
                "domain": domain,
                "models": 3,
                "personas": 100,
                "traits": 5,
                "levels": 2,
                "phrasings": 4,
                "repeats": 3,
                "primary_queries": primary_n,
                "exact10_queries": exact_n,
                "exact10_retention": exact_n / primary_n,
                "unflagged_queries": clean_n,
                "unflagged_retention": clean_n / primary_n,
                "eligible_items": eligible,
            }
        )
    return pd.DataFrame(rows)


def _table_2(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rel = frames["relevance"].groupby(["domain", "model"], as_index=False)[
        ["precision_at_k", "ndcg_at_k"]
    ].mean()
    user = frames["user"].groupby(["domain", "model"], as_index=False)["jaccard"].mean()
    item = frames["item"].groupby(["domain", "model"], as_index=False)[
        ["gini", "hhi", "catalog_coverage"]
    ].mean()
    opp = frames["opp"].groupby(["domain", "model"], as_index=False)[
        [
            "opportunity_gini",
            "opportunity_normalized_hhi",
            "opportunity_coverage",
            "opportunity_long_tail_coverage",
        ]
    ].mean()
    return rel.merge(user).merge(item).merge(opp).sort_values(["domain", "model"])


def _table_3(audit: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for domain in audit["domains"]:
        for metric in OPP_METRICS:
            magnitude = domain["delta_magnitude"][metric]
            exact = domain["primary_vs_sensitivity_concordance"]["exact10"][metric]
            clean = domain["primary_vs_sensitivity_concordance"]["unflagged"][metric]
            intervals = [
                item
                for item in domain["bootstrap_intervals_by_model"]
                if item["metric"] == metric
            ]
            rows.append(
                {
                    "domain": domain["domain"],
                    "metric": metric,
                    "mean_absolute_delta": magnitude["mean_absolute_delta"],
                    "maximum_absolute_delta": magnitude["maximum_absolute_delta"],
                    "ci_excluding_zero": sum(
                        item["intervals_excluding_zero"] for item in intervals
                    ),
                    "ci_total": sum(item["intervals_total"] for item in intervals),
                    "exact10_rho": exact["spearman_rho"],
                    "exact10_sign_agreement": exact["sign_agreement"],
                    "unflagged_rho": clean["spearman_rho"],
                    "unflagged_sign_agreement": clean["sign_agreement"],
                }
            )
    return pd.DataFrame(rows)


def _manifest(paths: list[Path], spec_path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    inventory = [
        {"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(paths)
    ]
    return {
        "schema_version": 1,
        "asset_version": spec["version"],
        "generated_on": str(spec["frozen_on"]),
        "generator": "recllm_fairness.pipeline.build_manuscript_assets",
        "spec_path": spec_path.as_posix(),
        "spec_sha256": _sha256(spec_path),
        "source_audits": spec["source_audits"],
        "file_count": len(inventory),
        "inventory": inventory,
    }


@app.command()
def main(
    spec_path: Path = Path("config/manuscript_assets_v1.yaml"),
    output_root: Annotated[
        Path | None,
        typer.Option(help="Validation-only destination override; never changes the frozen spec."),
    ] = None,
) -> None:
    """Render all frozen assets, refusing to overwrite an existing version."""
    os.environ["SOURCE_DATE_EPOCH"] = "0"
    spec = _load_spec(spec_path)
    _verify_sources(spec)
    output = output_root if output_root is not None else Path(str(spec["output_root"]))
    if output.exists() and any(output.iterdir()):
        raise typer.BadParameter(f"Write-once asset directory already contains files: {output}")
    figure_dir = output / "figures"
    table_dir = output / "tables"
    figure_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    _style(float(spec["style"]["base_font_pt"]))
    frames = _primary_frames()
    audit_path = Path(spec["source_audits"]["opportunity_v3"]["path"])
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    effects = _strongest_effects(frames)
    scenarios = _scenario_table(frames["rq3"])
    figures = {
        "figure_1_relevance_opportunity_tradeoff": _figure_1(frames),
        "figure_2_opportunity_delta_forest": _figure_2(effects),
        "figure_3_rq3_scenario_composition": _figure_3(scenarios),
        "figure_4_raw_adjusted_concordance": _figure_4(frames, audit),
        "figure_s1_sensitivity_concordance": _figure_s1(audit),
    }
    tables = {
        "table_1_study_design": _table_1(audit),
        "table_2_primary_model_summary": _table_2(frames),
        "table_3_opportunity_delta_summary": _table_3(audit),
        "table_4_rq3_scenarios": scenarios,
        "table_5_strongest_opportunity_effects": effects,
    }
    expected_figures = list(spec["figures"])
    expected_tables = list(spec["tables"])
    if list(figures) != expected_figures or list(tables) != expected_tables:
        raise ValueError("Generator assets do not exactly match the frozen specification")
    paths: list[Path] = []
    for name, figure in figures.items():
        paths.extend(_save_figure(figure, figure_dir / name, int(spec["formats"]["raster_dpi"])))
    for name, table in tables.items():
        paths.extend(_write_table(table, table_dir / name))
    notes = table_dir / "TABLE_NOTES.md"
    notes.write_text(
        "# Frozen manuscript table notes\n\n"
        "All values are generated from the hash-verified v2/v3 analysis packages. "
        "Table 5 reports the largest absolute observed condition effect for each "
        "domain/model in two focal metrics; it is descriptive and not a multiplicity-adjusted "
        "discovery table. Opportunity metrics condition exposure on catalog eligibility.\n",
        encoding="utf-8",
        newline="\n",
    )
    paths.append(notes)
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(_manifest(paths, spec_path, spec), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    typer.echo(f"Built {len(paths)} frozen assets plus manifest at {output}")


if __name__ == "__main__":
    app()
