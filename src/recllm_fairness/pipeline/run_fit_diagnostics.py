"""Generate transparent alternatives when preregistered mixed models are singular."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from recllm_fairness.stats.robust_effects import cluster_robust_effects_tables
from recllm_fairness.storage.manifest import sha256_file

app = typer.Typer(add_completion=False)


@app.command()
def main(
    table_dir: Path,
    alpha: float = 0.05,
    standardized_sesoi: float = 0.20,
) -> None:
    paired_path = table_dir / "user_side_similarities.csv"
    item_path = table_dir / "per_query_item_outcomes.csv"
    destination = table_dir / "cluster_robust_effects.csv"
    manifest_path = table_dir / "fit_diagnostics_manifest.json"
    if destination.exists() or manifest_path.exists():
        raise typer.BadParameter(f"Fit diagnostics already exist under {table_dir}")
    missing = [path for path in (paired_path, item_path) if not path.is_file()]
    if missing:
        raise typer.BadParameter(f"Analysis tables are missing: {missing}")

    table = cluster_robust_effects_tables(
        pd.read_csv(paired_path),
        pd.read_csv(item_path),
        alpha=alpha,
        standardized_sesoi=standardized_sesoi,
    )
    table.to_csv(destination, index=False)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "method": "ols_persona_cluster_robust",
                "alpha": alpha,
                "standardized_sesoi": standardized_sesoi,
                "inputs": {
                    paired_path.name: sha256_file(paired_path),
                    item_path.name: sha256_file(item_path),
                },
                "output": {
                    destination.name: sha256_file(destination),
                },
                "rows": len(table),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Fit diagnostics complete: {destination}")


if __name__ == "__main__":
    app()
