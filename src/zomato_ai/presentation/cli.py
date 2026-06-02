"""Command-line entrypoint for local development and smoke checks."""

from __future__ import annotations

import json

import typer

from zomato_ai.config import ConfigError, load_settings
from zomato_ai.config.logging import configure_logging
from zomato_ai.data_ingestion import DatasetLoadError, refresh_restaurant_cache

app = typer.Typer(help="Zomato AI recommendation tools.")


@app.command()
def health(
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Check whether the application shell can load configuration."""

    try:
        settings = load_settings()
    except ConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    configure_logging(settings)

    payload = {
        "status": "ok",
        "dataset_loaded": False,
        "llm_enabled": settings.llm_enabled,
        "max_candidates": settings.max_candidates,
        "top_k_output": settings.top_k_output,
    }

    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo("status: ok")
    typer.echo("dataset_loaded: false")
    typer.echo(f"llm_enabled: {str(settings.llm_enabled).lower()}")


@app.command()
def ingest() -> None:
    """Load the source dataset, normalize rows, and write the local cache."""

    try:
        settings = load_settings()
    except ConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    configure_logging(settings)

    try:
        result = refresh_restaurant_cache(settings)
    except DatasetLoadError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"total_rows: {result.report.total_rows}")
    typer.echo(f"normalized_rows: {result.report.normalized_rows}")
    typer.echo(f"skipped_rows: {len(result.report.skipped_rows)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
