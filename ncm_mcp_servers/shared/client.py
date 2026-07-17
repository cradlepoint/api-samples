"""NCM client factory for MCP Servers.

Provides get_ncm_client() that instantiates the correct NcmClient
based on available credentials.
"""

from typing import Optional, Union

from ncm_mcp_servers.shared.ncm import NcmClientv2, NcmClientv3, NcmClientv2v3
from ncm_mcp_servers.shared.credentials import ApiCredentials, load_credentials


def get_ncm_client(
    credentials: Optional[ApiCredentials] = None,
) -> Union[NcmClientv2, NcmClientv3, NcmClientv2v3]:
    """Instantiates the correct NcmClient based on available credentials.

    Returns:
        NcmClientv2 when only v2 keys are present.
        NcmClientv3 when only a v3 token is present.
        NcmClientv2v3 when both are present.

    Raises:
        ValueError: If credentials are missing or incomplete.
    """
    if credentials is None:
        credentials = load_credentials()

    credentials.validate()

    if credentials.has_v2 and credentials.has_v3:
        return NcmClientv2v3(
            api_keys=credentials.to_v2_dict(),
            api_key=credentials.ncm_api_token,
        )
    elif credentials.has_v2:
        return NcmClientv2(api_keys=credentials.to_v2_dict())
    else:
        return NcmClientv3(api_key=credentials.ncm_api_token)
