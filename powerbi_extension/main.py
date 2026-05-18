"""PowerBI cli entrypoint."""

import structlog
import typer
from meltano.edk.extension import DescribeFormat
from meltano.edk.logging import default_logging_config, parse_log_level

from powerbi_extension.extension import PowerBIExtension

APP_NAME = "PowerBI"

log = structlog.get_logger(APP_NAME)

app = typer.Typer(
    name=APP_NAME,
    pretty_exceptions_enable=False,
)


@app.command()
def describe(
    output_format: DescribeFormat = typer.Option(
        DescribeFormat.text, "--format", help="Output format"
    )
) -> None:
    """Describe the available commands of this extension."""
    ext = PowerBIExtension()
    typer.echo(ext.describe_formatted(output_format))


@app.command()
def refresh() -> None:
    """Trigger a refresh of the configured Power BI dataset.

    Workspace and dataset IDs are read from Meltano-populated environment
    variables (POWERBI_WORKSPACE_ID, POWERBI_DATASET_ID).
    """
    ext = PowerBIExtension()
    typer.echo(ext.refresh())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    log_level: str = typer.Option("INFO", envvar="LOG_LEVEL"),
    log_timestamps: bool = typer.Option(
        False, envvar="LOG_TIMESTAMPS", help="Show timestamp in logs"
    ),
    log_levels: bool = typer.Option(
        False, "--log-levels", envvar="LOG_LEVELS", help="Show log levels"
    ),
    meltano_log_json: bool = typer.Option(
        False,
        "--meltano-log-json",
        envvar="MELTANO_LOG_JSON",
        help="Log in the meltano JSON log format",
    ),
) -> None:
    """Meltano utility extension that provides PowerBI API commands."""
    default_logging_config(
        level=parse_log_level(log_level),
        timestamps=log_timestamps,
        levels=log_levels,
        json_format=meltano_log_json,
    )
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
