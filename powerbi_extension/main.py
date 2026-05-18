"""PowerBI cli entrypoint."""

import sys

import requests
import structlog
import typer
from azure.core.exceptions import ClientAuthenticationError
from meltano.edk.extension import DescribeFormat
from meltano.edk.logging import default_logging_config, parse_log_level

from powerbi_extension.extension import PowerBIExtension, PowerBIRefreshTimeout

# Exit codes used by `refresh` so Meltano can stop a pipeline on failure.
EXIT_COMPLETED = 0
EXIT_FAILED = 1
EXIT_TIMEOUT = 2
EXIT_ERROR = 3

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
def refresh(
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Poll until the refresh reaches a terminal status. Default: wait.",
    ),
    poll_interval: int = typer.Option(
        30, "--poll-interval", help="Seconds between status polls when --wait."
    ),
    timeout: int = typer.Option(
        3600, "--timeout", help="Max seconds to wait for the refresh to terminate."
    ),
    notify: str = typer.Option(
        "NoNotification",
        "--notify",
        help="Power BI notifyOption: NoNotification | MailOnCompletion | MailOnFailure.",
    ),
) -> None:
    """Trigger a refresh of the configured Power BI dataset.

    Workspace and dataset IDs are read from Meltano-populated environment
    variables (POWERBI_WORKSPACE_ID, POWERBI_DATASET_ID).

    Exit codes:
      0 Completed   1 Failed/Disabled   2 Timeout   3 Auth or HTTP error
    """
    try:
        ext = PowerBIExtension()
        request_id = ext.refresh(notify_option=notify)
        log.info("refresh triggered", request_id=request_id)
        typer.echo(request_id)
        if not wait:
            raise typer.Exit(code=EXIT_COMPLETED)
        result = ext.wait_for_refresh(
            request_id, poll_interval=poll_interval, timeout=timeout
        )
        status = result.get("status", "Unknown")
        if status == "Completed":
            log.info("refresh completed", request_id=request_id)
            raise typer.Exit(code=EXIT_COMPLETED)
        log.error(
            "refresh ended in non-success terminal state",
            request_id=request_id,
            status=status,
            error=result.get("serviceExceptionJson"),
        )
        raise typer.Exit(code=EXIT_FAILED)
    except PowerBIRefreshTimeout as err:
        log.error(
            "refresh did not complete in time",
            request_id=err.request_id,
            last_status=err.last_status,
        )
        raise typer.Exit(code=EXIT_TIMEOUT) from err
    except (requests.RequestException, ClientAuthenticationError) as err:
        log.error("refresh failed with auth or HTTP error", error=str(err))
        raise typer.Exit(code=EXIT_ERROR) from err


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
