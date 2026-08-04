#!/usr/bin/env python3
"""
One-shot environment setup for the API Samples project.

Works on macOS, Linux and Windows. Steps:

  1. Check the Python version is supported
  2. Create the .venv virtual environment (repairs a broken one)
  3. Upgrade pip and install requirements.txt into the venv
  4. Prompt for NCM API credentials and store them in .env plus every
     venv activate script (bash/zsh, fish, csh, PowerShell, cmd)
  5. Verify the venv can import the packages the project needs

Usage:
    python3 setup_env.py                  # macOS / Linux  (full setup)
    python setup_env.py                   # Windows         (full setup)

    python3 setup_env.py --skip-credentials   # venv + deps only, no prompts
    python3 setup_env.py --credentials-only   # re-enter credentials only
    python3 setup_env.py --check              # report status, change nothing

The credential prompt is skipped automatically when stdin is not a terminal,
so this script is safe to run from automation and from Kiro hooks.

Afterwards, activate the venv:
    source .venv/bin/activate              # macOS / Linux
    .venv\\Scripts\\Activate.ps1            # Windows PowerShell
    .venv\\Scripts\\activate.bat            # Windows cmd
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS = PROJECT_DIR / "requirements.txt"
ENV_FILE = PROJECT_DIR / ".env"
GITIGNORE = PROJECT_DIR / ".gitignore"

MIN_PYTHON = (3, 9)
IS_WINDOWS = os.name == "nt"

MARKER_START = "# >>> NCM API credentials >>>"
MARKER_END = "# <<< NCM API credentials <<<"
BAT_MARKER_START = "REM >>> NCM API credentials >>>"
BAT_MARKER_END = "REM <<< NCM API credentials <<<"

# (env var, prompt label, is_secret, is_required)
CREDENTIALS = [
    ("X_CP_API_ID", "Cradlepoint API ID (X-CP-API-ID)", False, True),
    ("X_CP_API_KEY", "Cradlepoint API Key (X-CP-API-KEY)", True, True),
    ("X_ECM_API_ID", "ECM API ID (X-ECM-API-ID)", False, True),
    ("X_ECM_API_KEY", "ECM API Key (X-ECM-API-KEY)", True, True),
    ("NCM_API_TOKEN", "API v3 Bearer Token", True, False),
]
CREDENTIAL_VARS = [var for var, _, _, _ in CREDENTIALS]
REQUIRED_VARS = [var for var, _, _, required in CREDENTIALS if required]

# import name -> pip package name, used by the verification step
VERIFY_IMPORTS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "httpx": "httpx",
    "requests": "requests",
    "dateutil": "python-dateutil",
    "jinja2": "jinja2",
    "dotenv": "python-dotenv",
    "multipart": "python-multipart",
    "itsdangerous": "itsdangerous",
    "ncm": "ncm",
}


# --------------------------------------------------------------------------
# small output helpers
# --------------------------------------------------------------------------

def header(text: str) -> None:
    print()
    print("=" * 62)
    print(f"  {text}")
    print("=" * 62)


def step(text: str) -> None:
    print()
    print(text)


def ok(text: str) -> None:
    print(f"  [ok]   {text}")


def warn(text: str) -> None:
    print(f"  [warn] {text}")


def fail(text: str) -> None:
    print(f"  [FAIL] {text}", file=sys.stderr)


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-2:]}"


# --------------------------------------------------------------------------
# venv paths
# --------------------------------------------------------------------------

def venv_scripts_dir() -> Path:
    """bin/ on POSIX, Scripts/ on Windows."""
    return VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")


def venv_python() -> Path | None:
    """Return the venv interpreter path, or None if the venv looks broken."""
    scripts = venv_scripts_dir()
    for name in ("python.exe", "python3.exe", "python", "python3"):
        candidate = scripts / name
        if candidate.exists():
            return candidate
    return None


def activation_command() -> str:
    if IS_WINDOWS:
        return r".venv\Scripts\Activate.ps1      (PowerShell)"
    return "source .venv/bin/activate"


def run_python_command() -> str:
    """The command Kiro or the user should use to run project code."""
    if IS_WINDOWS:
        return r".venv\Scripts\python.exe"
    return ".venv/bin/python"


# --------------------------------------------------------------------------
# Step 1: Python version
# --------------------------------------------------------------------------

def check_python_version() -> None:
    current = sys.version_info[:3]
    if sys.version_info[:2] < MIN_PYTHON:
        fail(
            f"Python {'.'.join(map(str, MIN_PYTHON))}+ is required, "
            f"but this is Python {'.'.join(map(str, current))}."
        )
        print()
        if IS_WINDOWS:
            print("  See WINDOWS_PYTHON_SETUP.md for install instructions.")
        else:
            print("  Install a newer Python from https://www.python.org/downloads/")
            print("  or via Homebrew:  brew install python@3.12")
        print()
        sys.exit(1)
    ok(f"Python {'.'.join(map(str, current))} at {sys.executable}")


# --------------------------------------------------------------------------
# Step 2: virtual environment
# --------------------------------------------------------------------------

def _venv_creation_help() -> None:
    print()
    if IS_WINDOWS:
        print("  Troubleshooting (Windows):")
        print("    - Reinstall Python with 'Add python.exe to PATH' checked.")
        print("    - See WINDOWS_PYTHON_SETUP.md for a step-by-step guide.")
    elif platform.system() == "Linux":
        print("  Troubleshooting (Linux):")
        print("    The venv module may be packaged separately. Try:")
        print("      sudo apt install python3-venv     # Debian / Ubuntu")
    else:
        print("  Troubleshooting (macOS):")
        print("    Try reinstalling Python:  brew install python@3.12")
    print()


def create_venv() -> Path:
    """Create .venv if needed. Returns the venv interpreter path."""
    existing = venv_python()

    if VENV_DIR.is_dir() and existing is None:
        warn("Found .venv/ but no interpreter inside it. Recreating.")
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    elif existing is not None:
        ok(f"Virtual environment already exists ({existing})")
        return existing

    print("  Creating virtual environment at .venv/ ...")
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail("Could not create the virtual environment.")
        if result.stderr:
            print(result.stderr.strip()[:1000], file=sys.stderr)
        _venv_creation_help()
        sys.exit(1)

    interpreter = venv_python()
    if interpreter is None:
        fail("Virtual environment was created but no interpreter was found in it.")
        _venv_creation_help()
        sys.exit(1)

    ok("Virtual environment created")
    return interpreter


# --------------------------------------------------------------------------
# Step 3: dependencies
# --------------------------------------------------------------------------

def install_dependencies(interpreter: Path) -> bool:
    """Upgrade pip then install requirements.txt. Returns True on success."""
    if not REQUIREMENTS.exists():
        warn("requirements.txt not found, skipping dependency install.")
        return False

    print("  Upgrading pip ...")
    upgrade = subprocess.run(
        [str(interpreter), "-m", "pip", "install", "--upgrade",
         "pip", "setuptools", "wheel", "--quiet"],
        capture_output=True,
        text=True,
    )
    if upgrade.returncode != 0:
        warn("Could not upgrade pip. Continuing with the bundled version.")
    else:
        ok("pip up to date")

    print("  Installing dependencies from requirements.txt ...")
    # Output is streamed, not captured, so slow installs show progress and
    # failures are visible in full.
    install = subprocess.run(
        [str(interpreter), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        text=True,
    )
    if install.returncode != 0:
        fail("Dependency install failed. See the pip output above.")
        print()
        print("  Common causes:")
        print("    - No network access or a proxy blocking PyPI")
        print("    - A package needs a compiler; install build tools and retry")
        print(f"    - Retry manually:  {run_python_command()} -m pip install -r requirements.txt")
        print()
        return False

    ok("Dependencies installed")
    return True


# --------------------------------------------------------------------------
# Step 4: credentials
# --------------------------------------------------------------------------

def read_env_file() -> dict[str, str]:
    """Parse the existing .env file, if any. Returns {var: value}."""
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values

    try:
        content = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return values

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            quote = value[0]
            value = value[1:-1]
            if quote == '"':
                value = _unescape_env_value(value)
        values[key] = value
    return values


def prompt_for_credentials(existing: dict[str, str]) -> dict[str, str]:
    """Prompt for each credential, offering any existing value as the default."""
    print()
    print("  Enter your API credentials.")
    print("  Secrets are hidden as you type.")
    if existing:
        print("  Press Enter to keep the current value shown in [brackets].")
    print("  Optional fields can be left blank.")
    print()

    creds: dict[str, str] = {}
    for var, label, is_secret, is_required in CREDENTIALS:
        current = existing.get(var, "")
        suffix = ""
        if current:
            suffix = f" [{mask(current) if is_secret else current}]"
        elif not is_required:
            suffix = " [optional]"

        while True:
            prompt = f"    {label}{suffix}: "
            try:
                value = getpass.getpass(prompt) if is_secret else input(prompt)
            except EOFError:
                print()
                warn("Input stream closed. Keeping existing credentials.")
                return {k: v for k, v in existing.items() if k in CREDENTIAL_VARS}

            value = value.strip()

            if not value and current:
                creds[var] = current
                break
            if not value:
                if is_required:
                    print("      This field is required.")
                    continue
                break
            creds[var] = value
            break

    return creds


def write_env_file(creds: dict[str, str]) -> None:
    """Write .env as the cross-platform source of truth for credentials."""
    lines = [
        "# NCM API credentials.",
        "# Generated by setup_env.py. Never commit this file.",
        "",
    ]
    for var in CREDENTIAL_VARS:
        value = creds.get(var)
        if value:
            lines.append(f'{var}="{_escape_env_value(value)}"')
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Best effort: restrict to the owner on POSIX. No-op on Windows.
    if not IS_WINDOWS:
        try:
            ENV_FILE.chmod(0o600)
        except OSError:
            pass

    ok(f"Credentials written to .env ({ENV_FILE})")


def _escape_env_value(value: str) -> str:
    """
    Escape a value for a double-quoted .env entry.

    A .env file is data, not a shell script, so it needs different escaping
    from the activate scripts. Only the backslash and the closing quote are
    escaped, which is the exact inverse of the reader in read_env_file() and
    in scripts/utils/env_check.py.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _unescape_env_value(value: str) -> str:
    """Inverse of _escape_env_value."""
    out = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value) and value[index + 1] in ('\\', '"'):
            out.append(value[index + 1])
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def _escape_double_quoted(value: str) -> str:
    """
    Escape a value for a POSIX shell (bash/zsh/sh) double-quoted string.

    Inside double quotes these four characters keep their special meaning,
    so each needs a backslash.
    """
    for char in ("\\", '"', "`", "$"):
        value = value.replace(char, "\\" + char)
    return value


def _escape_fish(value: str) -> str:
    """
    Escape a value for a fish double-quoted string.

    fish only honours a backslash before \\, " and $. Escaping anything else
    would leave the backslash in the value, so the set must be exactly these.
    """
    for char in ("\\", '"', "$"):
        value = value.replace(char, "\\" + char)
    return value


def _escape_csh(value: str) -> str:
    """
    Escape a value for a csh/tcsh double-quoted string.

    csh performs history expansion on '!' even inside double quotes, so it
    needs escaping too.
    """
    for char in ("\\", '"', "`", "$", "!"):
        value = value.replace(char, "\\" + char)
    return value


def _escape_powershell(value: str) -> str:
    """Escape a value for a PowerShell single-quoted string."""
    return value.replace("'", "''")


def _escape_bat(value: str) -> str | None:
    """
    Escape a value for a cmd batch `set "VAR=value"` statement.

    Returns None when the value cannot be represented safely. cmd has no
    escape for a double quote inside a quoted set statement: an embedded '"'
    ends the quoted string early and silently truncates the value, so such a
    value is skipped rather than written incorrectly. The caller warns and the
    true value remains available in .env and in the PowerShell block.
    """
    if '"' in value:
        return None
    return value.replace("%", "%%")


def _strip_block(content: str, start: str, end: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub("", content).rstrip("\n") + "\n"


def _write_activate_block(filename: str, body_lines: list[str],
                          start: str = MARKER_START,
                          end: str = MARKER_END) -> bool:
    """Replace the credential block in one activate script. True if written."""
    path = venv_scripts_dir() / filename
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        warn(f"Could not read {path.name}, skipping.")
        return False

    content = _strip_block(content, start, end)
    block = "\n".join([start, *body_lines, end])
    content = content.rstrip("\n") + "\n\n" + block + "\n"

    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        warn(f"Could not write {path.name}: {exc}")
        return False

    print(f"         {path.name}")
    return True


def _clear_old_unsets(content: str, patterns: list[str]) -> str:
    """Remove unset lines injected by earlier versions of this script."""
    for var in CREDENTIAL_VARS:
        for template in patterns:
            content = content.replace(template.format(var=var), "")
    return content


def update_posix_activate(creds: dict[str, str]) -> bool:
    """bash / zsh: .venv/bin/activate (also present on Windows for Git Bash)."""
    path = venv_scripts_dir() / "activate"
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    content = _strip_block(content, MARKER_START, MARKER_END)
    content = _clear_old_unsets(content, ["    unset {var}\n"])

    # Clear the credentials on `deactivate` when the expected anchor is present.
    anchor = "    unset VIRTUAL_ENV\n    unset VIRTUAL_ENV_PROMPT"
    if anchor in content:
        unsets = "\n".join(f"    unset {var}" for var in creds)
        content = content.replace(anchor, f"{anchor}\n{unsets}", 1)

    exports = [f'export {var}="{_escape_double_quoted(value)}"'
               for var, value in creds.items()]
    block = "\n".join([MARKER_START, *exports, MARKER_END])
    content = content.rstrip("\n") + "\n\n" + block + "\n"

    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        warn(f"Could not write {path.name}: {exc}")
        return False

    print(f"         {path.name}")
    return True


def update_activate_scripts(creds: dict[str, str]) -> None:
    """Inject credentials into every activate script the venv provides."""
    print()
    print("  Updating activate scripts:")

    written = update_posix_activate(creds)

    # fish
    written |= _write_activate_block(
        "activate.fish",
        [f'set -gx {var} "{_escape_fish(value)}"'
         for var, value in creds.items()],
    )

    # csh / tcsh
    written |= _write_activate_block(
        "activate.csh",
        [f'setenv {var} "{_escape_csh(value)}"'
         for var, value in creds.items()],
    )

    # Windows PowerShell. Also present in POSIX venvs for pwsh users.
    written |= _write_activate_block(
        "Activate.ps1",
        [f"$env:{var} = '{_escape_powershell(value)}'"
         for var, value in creds.items()],
    )

    # Windows cmd. Batch files use REM for comments, not #.
    bat_lines = []
    unrepresentable = []
    for var, value in creds.items():
        escaped = _escape_bat(value)
        if escaped is None:
            unrepresentable.append(var)
            bat_lines.append(f"REM {var} omitted: value contains a double quote, "
                             "which cmd cannot represent. See .env.")
            continue
        bat_lines.append(f'set "{var}={escaped}"')

    written |= _write_activate_block(
        "activate.bat",
        bat_lines,
        start=BAT_MARKER_START,
        end=BAT_MARKER_END,
    )

    if unrepresentable:
        warn(f"activate.bat could not represent: {', '.join(unrepresentable)}")
        print("         Those values contain a double quote. They are still in .env,")
        print("         which scripts read directly. Use PowerShell instead of cmd,")
        print("         or regenerate the key without a double quote.")

    if not written:
        warn("No activate scripts found to update. .env still holds your credentials.")


def configure_credentials(interactive: bool) -> dict[str, str]:
    """Collect credentials and persist them. Returns the credentials in use."""
    existing = {k: v for k, v in read_env_file().items() if k in CREDENTIAL_VARS}

    # Fall back to anything already exported in the environment.
    for var in CREDENTIAL_VARS:
        if var not in existing and os.environ.get(var):
            existing[var] = os.environ[var]

    if not interactive:
        if existing:
            ok("Reusing existing credentials (non-interactive mode)")
            creds = existing
        else:
            warn("Skipping credentials (non-interactive mode)")
            print()
            print("      Run this in your own terminal to enter them:")
            launcher = "python" if IS_WINDOWS else "python3"
            print(f"        {launcher} setup_env.py --credentials-only")
            print()
            return {}
    else:
        creds = prompt_for_credentials(existing)

    if not creds:
        warn("No credentials entered.")
        print("      You can add them later with:  python3 setup_env.py --credentials-only")
        print("      Dashboard apps also accept credentials in their Settings panel.")
        return {}

    write_env_file(creds)
    update_activate_scripts(creds)

    print()
    print("  Configured:")
    for var in CREDENTIAL_VARS:
        if var in creds:
            print(f"         {var} = {mask(creds[var])}")

    missing = [var for var in REQUIRED_VARS if not creds.get(var)]
    if missing:
        warn(f"Still missing required: {', '.join(missing)}")

    return creds


# --------------------------------------------------------------------------
# .gitignore
# --------------------------------------------------------------------------

def ensure_gitignore() -> None:
    """Make sure the credential file and caches are never committed."""
    needed = [".env", "__pycache__/", "*.pyc"]

    if GITIGNORE.exists():
        try:
            content = GITIGNORE.read_text(encoding="utf-8")
        except OSError:
            return
    else:
        content = ""

    existing = {line.strip() for line in content.splitlines()}
    missing = [entry for entry in needed if entry not in existing]
    if not missing:
        return

    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n# Added by setup_env.py\n" + "\n".join(missing) + "\n"

    try:
        GITIGNORE.write_text(content, encoding="utf-8")
        ok(f".gitignore updated ({', '.join(missing)})")
    except OSError:
        warn("Could not update .gitignore. Make sure .env is never committed.")


# --------------------------------------------------------------------------
# Step 5: verification
# --------------------------------------------------------------------------

def verify_environment(interpreter: Path) -> bool:
    """Import every required package inside the venv and report what's missing."""
    probe = (
        "import importlib, json, sys\n"
        f"names = {sorted(VERIFY_IMPORTS)!r}\n"
        "missing = []\n"
        "for name in names:\n"
        "    try:\n"
        "        importlib.import_module(name)\n"
        "    except Exception:\n"
        "        missing.append(name)\n"
        "print(json.dumps(missing))\n"
    )
    result = subprocess.run(
        [str(interpreter), "-c", probe],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        fail("Could not run the verification check inside the venv.")
        if result.stderr:
            print(result.stderr.strip()[:500], file=sys.stderr)
        return False

    try:
        missing = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        warn("Verification output could not be parsed.")
        return False

    if missing:
        packages = sorted({VERIFY_IMPORTS[name] for name in missing})
        fail(f"Missing packages in the venv: {', '.join(packages)}")
        print(f"         Retry:  {run_python_command()} -m pip install {' '.join(packages)}")
        return False

    ok(f"All {len(VERIFY_IMPORTS)} required packages import correctly")
    return True


# --------------------------------------------------------------------------
# --check mode
# --------------------------------------------------------------------------

def report_status() -> int:
    """Print environment status without changing anything."""
    header("NCM API Samples - Environment Status")
    print()

    problems = 0

    interpreter = venv_python()
    if interpreter:
        ok(f"venv: {interpreter}")
    else:
        fail("venv: not found at .venv/")
        problems += 1

    if interpreter and not verify_environment(interpreter):
        problems += 1

    creds = read_env_file()
    have = [var for var in REQUIRED_VARS if creds.get(var) or os.environ.get(var)]
    if len(have) == len(REQUIRED_VARS):
        ok(f"credentials: all {len(REQUIRED_VARS)} required values present")
    else:
        missing = [v for v in REQUIRED_VARS if v not in have]
        fail(f"credentials: missing {', '.join(missing)}")
        problems += 1

    print()
    if problems:
        print(f"  {problems} problem(s) found. Run:  python3 setup_env.py")
    else:
        print("  Environment is ready.")
    print()
    return 1 if problems else 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def print_next_steps(creds: dict[str, str]) -> None:
    header("Setup complete")
    print()
    print("  Activate the virtual environment:")
    print()
    print(f"    {activation_command()}")
    if IS_WINDOWS:
        print(r"    .venv\Scripts\activate.bat          (cmd)")
    print()
    print("  Then run a dashboard:")
    print()
    print(f"    {run_python_command()} web_apps/inventory_dashboard/serve.py        # http://localhost:8060")
    print(f"    {run_python_command()} web_apps/cellular_health_dashboard/serve.py  # http://localhost:8055")
    print()
    print("  Or just ask Kiro in chat, for example:")
    print()
    print('    "Build me a dashboard showing routers with poor signal"')
    print('    "Export all my routers to CSV"')
    print()

    missing = [var for var in REQUIRED_VARS if not creds.get(var)]
    if missing:
        print("  Note: credentials are incomplete, so API calls will fail until")
        print("        you run:  python3 setup_env.py --credentials-only")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set up the API Samples environment (venv, dependencies, credentials)."
    )
    parser.add_argument(
        "--skip-credentials", action="store_true",
        help="Create the venv and install dependencies without prompting for credentials.",
    )
    parser.add_argument(
        "--credentials-only", action="store_true",
        help="Only re-enter credentials. Skips venv creation and dependency install.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report environment status and exit without changing anything.",
    )
    args = parser.parse_args()

    if args.check:
        return report_status()

    # Prompting requires a real terminal. Hooks and CI do not have one.
    interactive = sys.stdin is not None and sys.stdin.isatty() and not args.skip_credentials

    if args.credentials_only:
        header("NCM API Samples - Credentials")
        if not interactive:
            fail("--credentials-only needs an interactive terminal.")
            print("  Run it directly in your terminal, not through automation.")
            return 1
        ensure_gitignore()
        creds = configure_credentials(interactive=True)
        print()
        return 0 if all(creds.get(v) for v in REQUIRED_VARS) else 1

    header("NCM API Samples - Environment Setup")

    step("Step 1/5: Python version")
    check_python_version()

    step("Step 2/5: Virtual environment")
    interpreter = create_venv()

    step("Step 3/5: Dependencies")
    deps_ok = install_dependencies(interpreter)

    step("Step 4/5: API credentials")
    ensure_gitignore()
    creds = configure_credentials(interactive=interactive)

    step("Step 5/5: Verification")
    verify_ok = verify_environment(interpreter)

    print_next_steps(creds)

    return 0 if (deps_ok and verify_ok) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(130)
