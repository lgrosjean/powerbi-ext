import os
from unittest.mock import MagicMock, patch

import pytest
from meltano.edk.models import Describe, ExtensionCommand
from requests import RequestException

from powerbi_extension.extension import BASE_URL, TIMEOUT, PowerBIExtension

TOKEN = "token"
WORKSPACE_ID = "workspace_id"
DATASET_ID = "dataset_id"

# Meltano-populated env vars must be present for PowerBIExtension to construct.
os.environ.setdefault("POWERBI_WORKSPACE_ID", WORKSPACE_ID)
os.environ.setdefault("POWERBI_DATASET_ID", DATASET_ID)


@patch("powerbi_extension.extension.get_token", return_value=TOKEN)
def test_init_not_token(mock_get_token: MagicMock):
    ext = PowerBIExtension()
    mock_get_token.assert_called_once()
    assert ext.log
    assert ext.headers == {"Authorization": f"Bearer {TOKEN}"}
    assert ext.workspace_id == WORKSPACE_ID
    assert ext.dataset_id == DATASET_ID
    assert ext.api_url == BASE_URL


class TestExtension:
    ext = PowerBIExtension(token=TOKEN)

    def test_invoke(self):
        with pytest.raises(NotImplementedError):
            self.ext.invoke()

    @patch("requests.post")
    def test_refresh_ok(self, mock_post: MagicMock):
        request_id = "abcd-1234"
        mock_res = MagicMock(
            status_code=202,
            headers={
                "Location": (
                    f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"
                    f"/datasets/{DATASET_ID}/refreshes/{request_id}"
                ),
                "x-ms-request-id": request_id,
            },
        )
        url = f"{BASE_URL}/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes"
        body = {
            "notifyOption": "MailOnCompletion",
        }
        mock_post.return_value = mock_res
        res = self.ext.refresh()
        mock_post.assert_called_once_with(
            url, json=body, headers=self.ext.headers, timeout=TIMEOUT
        )
        assert res == request_id

    @patch("requests.post")
    def test_refresh_not_ok(self, mock_post: MagicMock):
        mock_res = MagicMock(status_code=400)
        url = f"{BASE_URL}/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes"
        body = {
            "notifyOption": "MailOnCompletion",
        }
        mock_post.return_value = mock_res
        with pytest.raises(RequestException):
            self.ext.refresh()

        mock_post.assert_called_once_with(
            url, json=body, headers=self.ext.headers, timeout=TIMEOUT
        )

    @patch.object(ExtensionCommand, "__new__")
    @patch.object(Describe, "__new__")
    def test_describe(
        self,
        mock_describe_class: MagicMock,
        mock_command_class: MagicMock,
    ):
        name, description = "powerbi_extension", "extension commands"
        mock_command = MagicMock(name=name, description=description)
        mock_command_class.return_value = mock_command

        self.ext.describe()

        mock_command_class.assert_called_once_with(
            ExtensionCommand, name=name, description=description
        )

        mock_describe_class.assert_called_once_with(Describe, commands=[mock_command])
