from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from powerbi_ext.main import PowerBIExtension, app

runner = CliRunner()

WORKSPACE_ID = "workspace_id"
DATASET_ID = "dataset_id"


def test_main():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "describe" in result.stdout
    assert "refresh" in result.stdout


@patch.object(PowerBIExtension, "__new__")
def test_refresh_workspace_dataset_ok(mock_ext_class: MagicMock):
    mock_ext_refresh = MagicMock()
    mock_ext = MagicMock(refresh=mock_ext_refresh)
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["refresh", "-w", WORKSPACE_ID, DATASET_ID])

    mock_ext_class.assert_called_once()
    mock_ext_refresh.assert_called_once_with(WORKSPACE_ID, DATASET_ID)
    assert result.exit_code == 0


@patch.object(PowerBIExtension, "__new__")
def test_refresh_dataset_ok(mock_ext_class: MagicMock):
    mock_ext_refresh = MagicMock()
    mock_ext = MagicMock(refresh=mock_ext_refresh)
    mock_ext_class.return_value = mock_ext

    result = runner.invoke(app, ["refresh", DATASET_ID])

    mock_ext_class.assert_called_once()
    mock_ext_refresh.assert_called_once_with(None, DATASET_ID)
    assert result.exit_code == 0


@patch.object(PowerBIExtension, "__new__")
def test_refresh_error(mock_ext: MagicMock):
    result = runner.invoke(app, ["refresh"])
    mock_ext.assert_not_called()
    assert result.exit_code == 2


@patch.object(PowerBIExtension, "__new__")
def test_describe(mock_ext: MagicMock):
    result = runner.invoke(app, ["describe"])
    assert result.exit_code == 0
    mock_ext.assert_called_once()
