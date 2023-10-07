"""Passthrough shim for PowerBI extension."""
import sys

import structlog
from meltano.edk.logging import pass_through_logging_config
from powerbi_ext.extension import PowerBI


def pass_through_cli() -> None:
    """Pass through CLI entry point."""
    pass_through_logging_config()
    ext = PowerBI()
    ext.pass_through_invoker(
        structlog.getLogger("powerbi_invoker"),
        *sys.argv[1:] if len(sys.argv) > 1 else []
    )
