"""CLI for deterministic, no-LLM relevance-label construction."""

from __future__ import annotations

import re
from pathlib import Path

import typer

from recllm_fairness.personas.relevance_labels import (
    build_audit_bundle,
    build_movie_labels,
    build_music_labels,
    load_design,
    read_lastfm_listener_pairs,
    sha256_file,
    write_label_file,
)
from recllm_fairness.personas.traits import audit_marker_length_parity
from recllm_fairness.pipeline.services import load_configured_catalog
from recllm_fairness.utils.config import load_config

app = typer.Typer(add_completion=False)


def _artifact_tag(design_version: str) -> str:
    prefix = "persona-relevance-"
    value = design_version[len(prefix) :] if design_version.startswith(prefix) else design_version
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value).replace("-", "_")


@app.command()
def main(
    config_dir: Path = Path("config"),
    design: Path = Path("config/persona_relevance_design_v1.yaml"),
    stage: str = typer.Option("pilot", help="pilot or full"),
    output_dir: Path = Path("data/relevance_labels"),
) -> None:
    if stage not in {"pilot", "full"}:
        raise typer.BadParameter("stage must be pilot or full")
    config = load_config(config_dir)
    specification = load_design(design)
    audit_marker_length_parity(
        int(specification["trait_framings"]["max_pole_word_count_difference"])
    )
    parameters = specification["relevance_parameters"]
    design_version = str(specification["design_version"])
    artifact_tag = _artifact_tag(design_version)

    movie_source = config["movielens"][stage]
    movie_catalog = load_configured_catalog(config, domain="movie", stage=stage)
    movie_labels = build_movie_labels(
        movie_catalog,
        specification["movie_preferences"],
        min_ratings=int(parameters["movie"]["min_ratings"]),
        dataset_version=str(movie_source["version"]),
        design_version=design_version,
    )
    movie_path = output_dir / f"relevance_labels_movies_{stage}_{artifact_tag}.json"
    write_label_file(movie_path, movie_labels)

    music_source = config["lastfm"][stage]
    pairs = read_lastfm_listener_pairs(music_source["root"], str(music_source["version"]))
    music_parameters = parameters["music"]
    size = tuple(int(value) for value in music_parameters["acceptable_relevant_set_size"])
    if len(size) != 2:
        raise ValueError("acceptable_relevant_set_size must contain lower and upper bounds")
    music_labels = build_music_labels(
        pairs,
        specification["music_preferences"],
        min_seed_listeners=int(music_parameters["min_seed_listeners"]),
        min_candidate_listeners=int(music_parameters["min_candidate_listeners"]),
        cosine_threshold=float(music_parameters["cosine_threshold"]),
        acceptable_size=(size[0], size[1]),
        dataset_version=str(music_source["version"]),
        design_version=design_version,
    )
    music_path = output_dir / f"relevance_labels_music_{stage}_{artifact_tag}.json"
    write_label_file(music_path, music_labels)
    bundle = build_audit_bundle(specification, movie_labels, music_labels)
    status_suffix = "frozen" if specification.get("status") == "frozen" else "draft"
    bundle_path = (
        output_dir / f"persona_relevance_bundle_{stage}_{artifact_tag}_{status_suffix}.json"
    )
    write_label_file(bundle_path, bundle)
    bundle_sha256 = sha256_file(bundle_path)

    typer.echo(f"Movie labels: {movie_path}")
    typer.echo(f"Music labels: {music_path}")
    typer.echo(f"Audit bundle: {bundle_path}")
    typer.echo(f"Bundle SHA256: {bundle_sha256}")
    typer.echo(
        "Movie set sizes: "
        + ", ".join(
            f"{entry['id']}={entry['relevant_count']}" for entry in movie_labels["preferences"]
        )
    )
    typer.echo(
        "Music set sizes: "
        + ", ".join(
            f"{entry['id']}={entry['relevant_count']}" for entry in music_labels["preferences"]
        )
    )


if __name__ == "__main__":
    app()
