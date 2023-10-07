import os

from azure.identity import ClientSecretCredential

SCOPE = "https://analysis.windows.net/powerbi/api/.default"


def get_token(
    tenant_id: str = None,
    client_id: str = None,
    client_secret: str = None,
):
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

    return credential.get_token(SCOPE).token
