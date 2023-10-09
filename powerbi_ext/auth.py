"""PowerBI authentication module."""
import os
import typing as t

from azure.identity import ClientSecretCredential

SCOPE = "https://analysis.windows.net/powerbi/api/.default"


def get_credential(
    tenant_id: t.Optional[str] = None,
    client_id: t.Optional[str] = None,
    client_secret: t.Optional[str] = None,
):
    """Get Azure ClientSecretCredential using Meltano env variables"""
    if not tenant_id:
        tenant_id = os.environ["POWERBI_EXT_TENANT_ID"]
    if not client_id:
        client_id = os.environ["POWERBI_EXT_CLIENT_ID"]
    if not client_secret:
        client_secret = os.environ["POWERBI_EXT_CLIENT_SECRET"]

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    return credential


def get_token(
    tenant_id: t.Optional[str] = None,
    client_id: t.Optional[str] = None,
    client_secret: t.Optional[str] = None,
):
    """Get Azure token"""
    credential = get_credential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    access_token = credential.get_token(SCOPE)
    token = access_token.token
    return token
