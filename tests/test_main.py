from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from powerbi_extension.main import PowerBIExtension, app

runner = CliRunner()


def test_main():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "describe" in result.stdout
    assert "refresh" in result.stdout
    assert "status" in result.stdout
    assert "history" in result.stdout


@patch.object(PowerBIExtension, "__new__")
def test_refresh_wait_completed(mock_ext_class: MagicMock):
    mock_ext = MagicMock()
    mock_ext.refresh.return_value = "request_id"
    mock_ext.wait_for_refresh.return_value = {"status": "Completed"}
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["refresh"])

    mock_ext.refresh.assert_called_once_with(notify_option="NoNotification")
    mock_ext.wait_for_refresh.assert_called_once_with(
        "request_id", poll_interval=30, timeout=3600
    )
    assert result.exit_code == 0


@patch.object(PowerBIExtension, "__new__")
def test_refresh_no_wait(mock_ext_class: MagicMock):
    mock_ext = MagicMock()
    mock_ext.refresh.return_value = "request_id"
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["refresh", "--no-wait"])

    mock_ext.refresh.assert_called_once_with(notify_option="NoNotification")
    mock_ext.wait_for_refresh.assert_not_called()
    assert result.exit_code == 0
    assert "request_id" in result.stdout


@patch.object(PowerBIExtension, "__new__")
def test_status_with_request_id(mock_ext_class: MagicMock):
    mock_ext = MagicMock()
    mock_ext.get_refresh_status.return_value = {
        "requestId": "abc",
        "status": "Completed",
    }
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["status", "--request-id", "abc"])

    mock_ext.get_refresh_status.assert_called_once_with("abc")
    mock_ext.list_refresh_history.assert_not_called()
    assert result.exit_code == 0
    assert "abc" in result.stdout


@patch.object(PowerBIExtension, "__new__")
def test_status_most_recent(mock_ext_class: MagicMock):
    mock_ext = MagicMock()
    mock_ext.list_refresh_history.return_value = [
        {"requestId": "latest", "status": "Failed"}
    ]
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["status"])

    mock_ext.list_refresh_history.assert_called_once_with(top=1)
    mock_ext.get_refresh_status.assert_not_called()
    assert result.exit_code == 1  # Failed status → EXIT_FAILED
    assert "latest" in result.stdout


@patch.object(PowerBIExtension, "__new__")
def test_history(mock_ext_class: MagicMock):
    mock_ext = MagicMock()
    mock_ext.list_refresh_history.return_value = [
        {"requestId": "a", "status": "Completed"},
        {"requestId": "b", "status": "Failed"},
    ]
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["history", "--top", "5"])

    mock_ext.list_refresh_history.assert_called_once_with(top=5)
    assert result.exit_code == 0
    assert "a" in result.stdout
    assert "b" in result.stdout


@patch.object(PowerBIExtension, "__new__")
def test_describe(mock_ext: MagicMock):
    result = runner.invoke(app, ["describe"])
    assert result.exit_code == 0
    mock_ext.assert_called_once()
