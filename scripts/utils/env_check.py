"""
Environment variable checker for NCM API scripts.
Call check_env() at the start of any script to validate required
environment variables are set. Prints OS-appropriate setup instructions
and exits if any are missing.
"""
import os
import sys
import platform


REQUIRED_V2_VARS = [
    ("CP_API_ID", "Cradlepoint API ID"),
    ("CP_API_KEY", "Cradlepoint API Key"),
    ("ECM_API_ID", "ECM API ID"),
    ("ECM_API_KEY", "ECM API Key"),
]

OPTIONAL_V3_VARS = [
    ("CP_API_TOKEN", "Bearer token for API v3"),
]


def _get_os_instructions(missing_vars):
    """Return OS-appropriate instructions for setting env vars."""
    system = platform.system()

    lines = [
        "",
        "Missing required environment variables:",
        "",
    ]
    for var, desc in missing_vars:
        lines.append(f"  {var}  ({desc})")
    lines.append("")

    if system == "Darwin":  # macOS
        lines.append("Set them in your terminal (macOS):")
        lines.append("")
        for var, _ in missing_vars:
            lines.append(f'  export {var}="your_value_here"')
        lines.append("")
        lines.append("To persist, add the export lines to ~/.zshrc and run: source ~/.zshrc")

    elif system == "Linux":
        lines.append("Set them in your terminal (Linux):")
        lines.append("")
        for var, _ in missing_vars:
            lines.append(f'  export {var}="your_value_here"')
        lines.append("")
        lines.append("To persist, add the export lines to ~/.bashrc and run: source ~/.bashrc")

    elif system == "Windows":
        lines.append("Set them in PowerShell:")
        lines.append("")
        for var, _ in missing_vars:
            lines.append(f'  $env:{var} = "your_value_here"')
        lines.append("")
        lines.append("Or in Command Prompt:")
        lines.append("")
        for var, _ in missing_vars:
            lines.append(f"  set {var}=your_value_here")
        lines.append("")
        lines.append("To persist, add them via System Properties > Environment Variables.")

    else:
        lines.append("Set them in your shell:")
        lines.append("")
        for var, _ in missing_vars:
            lines.append(f'  export {var}="your_value_here"')

    lines.append("")
    lines.append("Or run the setup script to configure all credentials at once:")
    lines.append("")
    lines.append("  .venv/bin/python setup_env.py")
    lines.append("")
    return "\n".join(lines)


def check_env(require_v3=False):
    """
    Check that required environment variables are set.
    Prints OS-specific setup instructions and exits if any are missing.

    :param require_v3: If True, also require v3 token. Default False.
    """
    missing = []
    for var, desc in REQUIRED_V2_VARS:
        if not os.environ.get(var):
            missing.append((var, desc))

    if require_v3:
        for var, desc in OPTIONAL_V3_VARS:
            if not os.environ.get(var):
                missing.append((var, desc))

    if missing:
        print(_get_os_instructions(missing), file=sys.stderr)
        sys.exit(1)


def get_api_keys_from_env():
    """
    Build an API keys dict from environment variables.
    Compatible with the NCM SDK's expected format.
    Returns a dict for v2, and optionally includes 'token' for v3.
    """
    keys = {
        'X-CP-API-ID': os.environ.get('CP_API_ID', ''),
        'X-CP-API-KEY': os.environ.get('CP_API_KEY', ''),
        'X-ECM-API-ID': os.environ.get('ECM_API_ID', ''),
        'X-ECM-API-KEY': os.environ.get('ECM_API_KEY', ''),
    }
    token = os.environ.get('CP_API_TOKEN')
    if token:
        keys['token'] = token
    return keys
