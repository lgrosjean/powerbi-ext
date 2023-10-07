"""PowerBI cli entrypoint."""

import sys

import structlog
import typer
from meltano.edk.extension import DescribeFormat
from meltano.edk.logging import default_logging_config, parse_log_level

from powerbi_ext.extension import PowerBIExtension

APP_NAME = "PowerBI"

log = structlog.get_logger(APP_NAME)

ext = PowerBIExtension()

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
    try:
        typer.echo(ext.describe_formatted(output_format))
    except Exception:
        log.exception(
            "describe failed with uncaught exception, please report to maintainer"
        )
        sys.exit(1)


@app.command()
def refresh(
    workspace_id: str = typer.Option(
        None,
        "-w",
        "--workspace",
        envvar="POWERBI_EXT_WORKSPACE_ID",
        show_envvar=True,
        help="Workspace ID. If not provided, will look for Dataset in 'My Workspace'",
    ),
    dataset_id: str = typer.Argument(..., help="Dataset ID"),
) -> None:
    """Refresh the given dataset in the given workspace"""

    typer.echo(ext.refresh(workspace_id, dataset_id))


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
