"""Meltano PowerBI extension."""
from __future__ import annotations

import os
import typing as t

import requests
import structlog
from meltano.edk import models
from meltano.edk.extension import ExtensionBase

from powerbi_extension.auth import get_token

BASE_URL = "https://api.powerbi.com/v1.0/myorg"
TIMEOUT = 30


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
        ] = "MailOnCompletion",
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

    def describe(self) -> models.Describe:
        """Describe the extension.

        Returns:
            The extension description
        """
        # TODO: could we auto-generate all or portions of this from typer instead?
        return models.Describe(
            commands=[
                models.ExtensionCommand(
                    name="powerbi_extension", description="extension commands"
                )
            ]
        )
