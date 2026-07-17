"""Credential loading for NCM MCP Servers.

Reads API credentials from a JSON file or environment variables.

Credential resolution order:
1. JSON file at the path specified by NCM_CREDENTIALS_FILE env var
2. JSON file at the default path: /app/credentials.json (Docker) or ./credentials.json
3. Environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY, NCM_API_TOKEN)
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiCredentials:
    """Holds NCM API credentials read from environment variables."""

    x_cp_api_id: Optional[str] = None
    x_cp_api_key: Optional[str] = None
    x_ecm_api_id: Optional[str] = None
    x_ecm_api_key: Optional[str] = None
    ncm_api_token: Optional[str] = None

    @property
    def has_v2(self) -> bool:
        """True when all four v2 credentials are present."""
        return all([
            self.x_cp_api_id,
            self.x_cp_api_key,
            self.x_ecm_api_id,
            self.x_ecm_api_key,
        ])

    @property
    def has_v3(self) -> bool:
        """True when the v3 bearer token is present."""
        return self.ncm_api_token is not None and self.ncm_api_token != ""

    def to_v2_dict(self) -> dict:
        """Returns v2 credentials as the dict format expected by NcmClientv2."""
        return {
            "X-CP-API-ID": self.x_cp_api_id,
            "X-CP-API-KEY": self.x_cp_api_key,
            "X-ECM-API-ID": self.x_ecm_api_id,
            "X-ECM-API-KEY": self.x_ecm_api_key,
        }

    @property
    def _v2_fields(self) -> dict:
        """Maps env var names to their current values for validation."""
        return {
            "X_CP_API_ID": self.x_cp_api_id,
            "X_CP_API_KEY": self.x_cp_api_key,
            "X_ECM_API_ID": self.x_ecm_api_id,
            "X_ECM_API_KEY": self.x_ecm_api_key,
        }

    def validate(self, require_v2=False, require_v3=False) -> None:
        """Validates that required credential sets are provided.

        Args:
            require_v2: If True, v2 credentials must be present.
            require_v3: If True, v3 credentials must be present.

        Raises ValueError with descriptive message when:
        - No credentials of any type are provided
        - v2 credentials are partially provided (1-3 of 4 keys)
        - Required credentials are missing
        """
        v2_fields = self._v2_fields
        v2_present = {k: v for k, v in v2_fields.items() if v}
        v2_missing = {k for k, v in v2_fields.items() if not v}

        # Check for partial v2 credentials (some but not all)
        if 0 < len(v2_present) < 4:
            missing_names = ", ".join(sorted(v2_missing))
            raise ValueError(
                f"Incomplete v2 API credentials. Missing: {missing_names}"
            )

        if require_v2 and not self.has_v2:
            raise ValueError(
                "v2 API credentials required. Provide: "
                "X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY"
            )

        if require_v3 and not self.has_v3:
            raise ValueError(
                "v3 API token required. Provide: NCM_API_TOKEN"
            )

        if not self.has_v2 and not self.has_v3:
            raise ValueError(
                "No API credentials found. Provide v2 credentials "
                "(X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY) "
                "or a v3 token (NCM_API_TOKEN), or both."
            )


# Default paths to look for a credentials JSON file
DEFAULT_CREDENTIALS_PATHS = [
    "/app/credentials.json",   # Docker container default
    "./credentials.json",      # Local development
]


def _load_credentials_from_file() -> Optional[ApiCredentials]:
    """Attempt to load credentials from a JSON file.

    Checks NCM_CREDENTIALS_FILE env var first, then default paths.
    Returns None if no file is found.

    Expected JSON format::

        {
            "X_CP_API_ID": "...",
            "X_CP_API_KEY": "...",
            "X_ECM_API_ID": "...",
            "X_ECM_API_KEY": "...",
            "NCM_API_TOKEN": "..."
        }
    """
    paths_to_try = []
    custom_path = os.environ.get("NCM_CREDENTIALS_FILE")
    if custom_path:
        paths_to_try.append(custom_path)
    paths_to_try.extend(DEFAULT_CREDENTIALS_PATHS)

    for path in paths_to_try:
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                return ApiCredentials(
                    x_cp_api_id=data.get("X_CP_API_ID") or None,
                    x_cp_api_key=data.get("X_CP_API_KEY") or None,
                    x_ecm_api_id=data.get("X_ECM_API_ID") or None,
                    x_ecm_api_key=data.get("X_ECM_API_KEY") or None,
                    ncm_api_token=data.get("NCM_API_TOKEN") or None,
                )
            except (json.JSONDecodeError, OSError) as exc:
                print(
                    f"Warning: Failed to read credentials from {path}: {exc}",
                    file=sys.stderr,
                )
    return None


def _load_credentials_from_env() -> ApiCredentials:
    """Reads API credentials from environment variables."""
    return ApiCredentials(
        x_cp_api_id=os.environ.get("X_CP_API_ID") or None,
        x_cp_api_key=os.environ.get("X_CP_API_KEY") or None,
        x_ecm_api_id=os.environ.get("X_ECM_API_ID") or None,
        x_ecm_api_key=os.environ.get("X_ECM_API_KEY") or None,
        ncm_api_token=os.environ.get("NCM_API_TOKEN") or None,
    )


def load_credentials() -> ApiCredentials:
    """Load API credentials from file first, then fall back to env vars.

    Resolution order:
    1. JSON file (NCM_CREDENTIALS_FILE env var or default paths)
    2. Environment variables
    """
    file_creds = _load_credentials_from_file()
    if file_creds is not None:
        return file_creds
    return _load_credentials_from_env()
