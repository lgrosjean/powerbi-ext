from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from powerbi_extension.main import PowerBIExtension, app

runner = CliRunner()


def test_main():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "describe" in result.stdout
    assert "refresh" in result.stdout


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
def test_describe(mock_ext: MagicMock):
    result = runner.invoke(app, ["describe"])
    assert result.exit_code == 0
    mock_ext.assert_called_once()
