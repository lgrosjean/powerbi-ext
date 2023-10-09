import os
from unittest.mock import MagicMock, patch

import pytest
from azure.identity import ClientSecretCredential

from powerbi_ext.auth import SCOPE, get_credential, get_token

TOKEN = "token"
TENANT_ID, CLIENT_ID, CLIENT_SECRET = "tenant_id", "client_id", "client_secret"


def test_get_credential_with_args():
    with patch.object(ClientSecretCredential, "__new__") as mock_ClientSecretCredential:
        get_credential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )

        mock_ClientSecretCredential.assert_called_once_with(
            ClientSecretCredential,
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )


def test_get_credential_without_args_missing_envvar_tenant_id():
    if os.getenv("POWERBI_EXT_TENANT_ID"):
        del os.environ["POWERBI_EXT_TENANT_ID"]
    os.environ["POWERBI_EXT_CLIENT_ID"] = CLIENT_ID
    os.environ["POWERBI_EXT_CLIENT_SECRET"] = CLIENT_SECRET

    with pytest.raises(KeyError, match="POWERBI_EXT_TENANT_ID"):
        get_credential()


def test_get_credential_without_args_missing_envvar_client_id():
    os.environ["POWERBI_EXT_TENANT_ID"] = TENANT_ID
    if os.getenv("POWERBI_EXT_CLIENT_ID"):
        del os.environ["POWERBI_EXT_CLIENT_ID"]
    os.environ["POWERBI_EXT_CLIENT_SECRET"] = CLIENT_SECRET

    with pytest.raises(KeyError, match="POWERBI_EXT_CLIENT_ID"):
        get_credential()


def test_get_credential_without_args_missing_envvar_client_secret():
    os.environ["POWERBI_EXT_TENANT_ID"] = TENANT_ID
    os.environ["POWERBI_EXT_CLIENT_ID"] = CLIENT_ID
    if os.getenv("POWERBI_EXT_CLIENT_SECRET"):
        del os.environ["POWERBI_EXT_CLIENT_SECRET"]

    with pytest.raises(KeyError, match="POWERBI_EXT_CLIENT_SECRET"):
        get_credential()


def test_get_token():
    mock_access_token = MagicMock(token=TOKEN)
    mock_get_token = MagicMock(return_value=mock_access_token)
    mock_credential = MagicMock(get_token=mock_get_token)
    with patch(
        "powerbi_ext.auth.get_credential", return_value=mock_credential
    ) as mock_get_credential:
        result = get_token(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )

        mock_get_credential.assert_called_once_with(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        mock_get_token.assert_called_once_with(SCOPE)

        assert result == TOKEN
