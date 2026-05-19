"""Meltano PowerBI extension."""
from __future__ import annotations

import os
import time
import typing as t

import requests
import structlog
from meltano.edk import models
from meltano.edk.extension import ExtensionBase

from powerbi_extension.auth import get_token

BASE_URL = "https://api.powerbi.com/v1.0/myorg"
TIMEOUT = 30
TERMINAL_STATUSES = frozenset({"Completed", "Failed", "Disabled"})


class PowerBIRefreshTimeout(Exception):
    """Raised when wait_for_refresh exceeds its timeout before reaching a terminal state."""

    def __init__(self, request_id: str, last_status: str):
        super().__init__(
            f"refresh {request_id} did not reach a terminal state in time "
            f"(last status: {last_status})"
        )
        self.request_id = request_id
        self.last_status = last_status


class PowerBIExtension(ExtensionBase):
    """Extension implementing the ExtensionBase interface."""

    def __init__(self, token: t.Optional[str] = None) -> None:
        """Initialize the extension.

        Workspace, dataset, and API URL are sourced from Meltano-populated
        env vars (POWERBI_WORKSPACE_ID, POWERBI_DATASET_ID, POWERBI_API_URL).
        """
        self.log = structlog.get_logger(name=self.__class__.__name__)
        self.workspace_id = os.environ["POWERBI_WORKSPACE_ID"]
        self.dataset_id = os.environ["POWERBI_DATASET_ID"]
        self.api_url = os.environ.get("POWERBI_API_URL", BASE_URL)
        if not token:
            token = get_token()
        self.log.info("Bearer token accessed.")
        self.headers = {"Authorization": f"Bearer {token}"}

    def invoke(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Invoke the underlying CLI that is being wrapped by this extension.

        Args:
            args: Ignored positional arguments.
            kwargs: Ignored keyword arguments.

        Raises:
            NotImplementedError: There is no underlying CLI for this extension.
        """
        raise NotImplementedError

    def refresh(
        self,
        notify_option: t.Literal[
            "MailOnCompletion", "MailOnFailure", "NoNotification"
        ] = "NoNotification",
        type: str | None = None,
    ):
        """Trigger a refresh of the configured dataset."""
        body = {
            "notifyOption": notify_option,
            # "type": type,
        }

        url = (
            f"{self.api_url}/groups/{self.workspace_id}"
            f"/datasets/{self.dataset_id}/refreshes"
        )
        res = requests.post(url, json=body, headers=self.headers, timeout=TIMEOUT)
        self.log.info("refresh trigger response", status_code=res.status_code)
        # Power BI's enhanced refresh API returns 202 Accepted on success, not 200.
        if res.status_code != 202:
            self.log.error(res.reason, status_code=res.status_code)
            raise requests.RequestException(res.status_code, res.reason, res.headers)
        # The requestId is exposed in the Location header (path tail) and mirrored
        # in x-ms-request-id; the upstream `RequestId` header is not a real header.
        location = res.headers.get("Location", "")
        return location.rsplit("/", 1)[-1] or res.headers["x-ms-request-id"]

    def get_refresh_status(self, request_id: str) -> dict:
        """Fetch the status of a single refresh by requestId.

        Returns the full refresh record (requestId, status, startTime, endTime,
        refreshType, serviceExceptionJson, ...). Status is one of Unknown,
        Completed, Failed, or Disabled.
        """
        url = (
            f"{self.api_url}/groups/{self.workspace_id}"
            f"/datasets/{self.dataset_id}/refreshes/{request_id}"
        )
        res = requests.get(url, headers=self.headers, timeout=TIMEOUT)
        res.raise_for_status()
        return res.json()

    def list_refresh_history(self, top: int = 10) -> list[dict]:
        """List the most recent refreshes for the configured dataset.

        `top` caps the result count (Power BI accepts $top up to 200).
        """
        url = (
            f"{self.api_url}/groups/{self.workspace_id}"
            f"/datasets/{self.dataset_id}/refreshes"
        )
        res = requests.get(
            url, headers=self.headers, params={"$top": top}, timeout=TIMEOUT
        )
        res.raise_for_status()
        return res.json().get("value", [])

    def wait_for_refresh(
        self,
        request_id: str,
        poll_interval: int = 30,
        timeout: int = 3600,
    ) -> dict:
        """Poll a refresh until it reaches a terminal status or timeout elapses.

        Returns the final refresh record. Raises PowerBIRefreshTimeout if the
        refresh has not reached a terminal status within `timeout` seconds.
        """
        deadline = time.monotonic() + timeout
        result: dict = {"status": "Unknown"}
        while time.monotonic() < deadline:
            result = self.get_refresh_status(request_id)
            status = result.get("status", "Unknown")
            self.log.info(
                "polled refresh status", request_id=request_id, status=status
            )
            if status in TERMINAL_STATUSES:
                return result
            time.sleep(poll_interval)
        raise PowerBIRefreshTimeout(request_id, result.get("status", "Unknown"))

    def describe(self) -> models.Describe:
        """Describe the extension's available commands."""
        return models.Describe(
            commands=[
                models.ExtensionCommand(
                    name="refresh",
                    description="Trigger a Power BI dataset refresh and (by default) wait for completion.",
                ),
                models.ExtensionCommand(
                    name="status",
                    description="Get the status of the most recent (or a specific) refresh.",
                ),
                models.ExtensionCommand(
                    name="history",
                    description="List recent refresh history for the configured dataset.",
                ),
            ]
        )
