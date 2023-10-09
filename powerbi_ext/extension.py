"""Meltano PowerBI extension."""
from __future__ import annotations

import typing as t

import requests
import structlog
from meltano.edk import models
from meltano.edk.extension import ExtensionBase

from powerbi_ext.auth import get_token

BASE_URL = "https://api.powerbi.com/v1.0/myorg"
TIMEOUT = 30


class PowerBIExtension(ExtensionBase):
    """Extension implementing the ExtensionBase interface."""

    def __init__(self, token: t.Optional[str] = None) -> None:
        """Initialize the extension."""
        self.log = structlog.get_logger(name=self.__class__.__name__)
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

    # TODO: add the ability to use workspace name or dataset name instead of id
    # TODO: add the other options to the settings
    def refresh(
        self,
        workspace_id: str,
        dataset_id: str,
        notify_option: t.Literal[
            "MailOnCompletion", "MailOnFailure", "NoNotification"
        ] = "MailOnCompletion",
        type: str | None = None,
    ):
        """Trigger a refresh of the dataset."""
        body = {
            "notifyOption": notify_option,
            # "type": type,
        }

        url = BASE_URL + f"/groups/{workspace_id}/datasets/{dataset_id}" + "/refreshes"
        res = requests.post(url, json=body, headers=self.headers, timeout=TIMEOUT)
        self.log.info(res.status_code)
        if res.status_code != 200:
            self.log.error(res.reason, res.headers)
            raise requests.RequestException(res.status_code, res.reason, res.headers)
        return res.headers["RequestId"]

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
