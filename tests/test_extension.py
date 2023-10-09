from unittest.mock import MagicMock, patch

import pytest
from meltano.edk.models import Describe, ExtensionCommand
from requests import RequestException

from powerbi_ext.extension import BASE_URL, TIMEOUT, PowerBIExtension

TOKEN = "token"
WORKSPACE_ID = "workspace_id"
DATASET_ID = "dataset_id"


@patch("powerbi_ext.extension.get_token", return_value=TOKEN)
def test_init_not_token(mock_get_token: MagicMock):
    ext = PowerBIExtension()
    mock_get_token.assert_called_once()
    assert ext.log
    assert ext.headers == {"Authorization": f"Bearer {TOKEN}"}


class TestExtension:
    ext = PowerBIExtension(token=TOKEN)

    def test_invoke(self):
        with pytest.raises(NotImplementedError):
            self.ext.invoke()

    @patch("requests.post")
    def test_refresh_ok(self, mock_post: MagicMock):
        mock_res = MagicMock(status_code=200, headers={"RequestId": "RequestId"})
        url = BASE_URL + f"/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}" + "/refreshes"
        body = {
            "notifyOption": "MailOnCompletion",
        }
        mock_post.return_value = mock_res
        res = self.ext.refresh(workspace_id=WORKSPACE_ID, dataset_id=DATASET_ID)
        mock_post.assert_called_once_with(
            url, json=body, headers=self.ext.headers, timeout=TIMEOUT
        )
        assert res == "RequestId"

    @patch("requests.post")
    def test_refresh_not_ok(self, mock_post: MagicMock):
        mock_res = MagicMock(status_code=202)
        url = BASE_URL + f"/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}" + "/refreshes"
        body = {
            "notifyOption": "MailOnCompletion",
        }
        mock_post.return_value = mock_res
        with pytest.raises(RequestException):
            self.ext.refresh(workspace_id=WORKSPACE_ID, dataset_id=DATASET_ID)

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
