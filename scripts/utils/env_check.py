"""
Environment variable checker for NCM API scripts.
Call check_env() at the start of any script to validate required
environment variables are set. Prints OS-appropriate setup instructions
and exits if any are missing.

Importing this module also loads the project's .env file (written by
setup_env.py) into os.environ, so credentials work the same on macOS,
Linux and Windows whether or not the venv is activated. Real environment
variables always win over .env values.
"""
import os
import sys
import platform

# Project root: scripts/utils/env_check.py -> up two levels
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(PROJECT_DIR, '.env')


def _unescape(value):
    """Undo the \\\\ and \\" escaping that setup_env.py writes into .env."""
    out = []
    i = 0
    while i < len(value):
        if value[i] == '\\' and i + 1 < len(value) and value[i + 1] in ('\\', '"'):
            out.append(value[i + 1])
            i += 2
        else:
            out.append(value[i])
            i += 1
    return ''.join(out)


def load_env_file(path=None, override=False):
    """
    Load KEY=value pairs from a .env file into os.environ.

    Uses only the standard library so it works before dependencies are
    installed. Existing environment variables are preserved unless
    override=True.

    :param path: .env path. Defaults to the project root .env.
    :param override: If True, .env values replace existing env vars.
    :return: dict of the values that were loaded.
    """
    path = path or ENV_FILE
    loaded = {}

    if not os.path.isfile(path):
        return loaded

    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except OSError:
        return loaded

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, _, value = line.partition('=')
        key = key.strip()
        if key.startswith('export '):
            key = key[len('export '):].strip()
        if not key:
            continue

        value = value.strip()
        # Strip one layer of matching quotes. Double-quoted values may contain
        # \\ and \" escapes written by setup_env.py; single-quoted are literal.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            quote = value[0]
            value = value[1:-1]
            if quote == '"':
                value = _unescape(value)

        if override or not os.environ.get(key):
            os.environ[key] = value
            loaded[key] = value

    return loaded


# Load on import so scripts get credentials without any extra call.
load_env_file()


REQUIRED_V2_VARS = [
    ("X_CP_API_ID", "Cradlepoint API ID"),
    ("X_CP_API_KEY", "Cradlepoint API Key"),
    ("X_ECM_API_ID", "ECM API ID"),
    ("X_ECM_API_KEY", "ECM API Key"),
]

OPTIONAL_V3_VARS = [
    ("NCM_API_TOKEN", "Bearer token for API v3"),
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
    lines.append("Easiest fix - run the setup script to configure everything at once:")
    lines.append("")
    if system == "Windows":
        lines.append("  python setup_env.py --credentials-only")
    else:
        lines.append("  python3 setup_env.py --credentials-only")
    lines.append("")
    lines.append(f"That writes {ENV_FILE}, which this script loads automatically.")
    lines.append("")
    lines.append("To check your environment at any time:")
    lines.append("")
    lines.append("  python3 setup_env.py --check" if system != "Windows"
                 else "  python setup_env.py --check")
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
        'X-CP-API-ID': os.environ.get('X_CP_API_ID', ''),
        'X-CP-API-KEY': os.environ.get('X_CP_API_KEY', ''),
        'X-ECM-API-ID': os.environ.get('X_ECM_API_ID', ''),
        'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY', ''),
    }
    token = os.environ.get('NCM_API_TOKEN')
    if token:
        keys['token'] = token
    return keys
