import os
from unittest.mock import MagicMock, patch

import pytest
from meltano.edk.models import Describe, ExtensionCommand
from requests import RequestException

from powerbi_extension.extension import (
    BASE_URL,
    TIMEOUT,
    PowerBIExtension,
    PowerBIRefreshTimeout,
)

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
            "notifyOption": "NoNotification",
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
            "notifyOption": "NoNotification",
        }
        mock_post.return_value = mock_res
        with pytest.raises(RequestException):
            self.ext.refresh()

        mock_post.assert_called_once_with(
            url, json=body, headers=self.ext.headers, timeout=TIMEOUT
        )

    @patch("requests.get")
    def test_get_refresh_status(self, mock_get: MagicMock):
        request_id = "abcd-1234"
        mock_res = MagicMock(status_code=200)
        mock_res.json.return_value = {"requestId": request_id, "status": "Completed"}
        mock_get.return_value = mock_res

        result = self.ext.get_refresh_status(request_id)

        url = (
            f"{BASE_URL}/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}"
            f"/refreshes/{request_id}"
        )
        mock_get.assert_called_once_with(
            url, headers=self.ext.headers, timeout=TIMEOUT
        )
        assert result["requestId"] == request_id
        assert result["status"] == "Completed"

    @patch("requests.get")
    def test_list_refresh_history(self, mock_get: MagicMock):
        mock_res = MagicMock(status_code=200)
        mock_res.json.return_value = {
            "value": [
                {"requestId": "a", "status": "Completed"},
                {"requestId": "b", "status": "Failed"},
            ]
        }
        mock_get.return_value = mock_res

        result = self.ext.list_refresh_history(top=2)

        url = f"{BASE_URL}/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/refreshes"
        mock_get.assert_called_once_with(
            url, headers=self.ext.headers, params={"$top": 2}, timeout=TIMEOUT
        )
        assert len(result) == 2
        assert result[0]["requestId"] == "a"

    @patch("powerbi_extension.extension.time.sleep")
    @patch.object(PowerBIExtension, "get_refresh_status")
    def test_wait_for_refresh_completed(
        self, mock_status: MagicMock, mock_sleep: MagicMock
    ):
        mock_status.side_effect = [
            {"status": "Unknown"},
            {"status": "Unknown"},
            {"status": "Completed", "requestId": "abc"},
        ]
        result = self.ext.wait_for_refresh("abc", poll_interval=1, timeout=60)
        assert result["status"] == "Completed"
        assert mock_status.call_count == 3
        assert mock_sleep.call_count == 2  # slept between the two Unknown polls

    @patch("powerbi_extension.extension.time.sleep")
    @patch.object(PowerBIExtension, "get_refresh_status")
    def test_wait_for_refresh_failed(
        self, mock_status: MagicMock, _mock_sleep: MagicMock
    ):
        mock_status.return_value = {
            "status": "Failed",
            "serviceExceptionJson": "{...}",
        }
        result = self.ext.wait_for_refresh("abc", poll_interval=1, timeout=60)
        assert result["status"] == "Failed"

    @patch("powerbi_extension.extension.time.sleep")
    @patch("powerbi_extension.extension.time.monotonic")
    @patch.object(PowerBIExtension, "get_refresh_status")
    def test_wait_for_refresh_timeout(
        self,
        mock_status: MagicMock,
        mock_monotonic: MagicMock,
        _mock_sleep: MagicMock,
    ):
        # First call sets the deadline, subsequent calls exceed it.
        mock_monotonic.side_effect = [0, 1, 1000]
        mock_status.return_value = {"status": "Unknown"}
        with pytest.raises(PowerBIRefreshTimeout) as exc_info:
            self.ext.wait_for_refresh("abc", poll_interval=1, timeout=60)
        assert exc_info.value.request_id == "abc"
        assert exc_info.value.last_status == "Unknown"

    def test_describe(self):
        result = self.ext.describe()
        assert isinstance(result, Describe)
        command_names = {cmd.name for cmd in result.commands}
        assert command_names == {"refresh", "status", "history"}
        for cmd in result.commands:
            assert isinstance(cmd, ExtensionCommand)
            assert cmd.description  # non-empty
