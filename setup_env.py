#!/usr/bin/env python3
"""
Full environment setup for the API Samples project.

Performs all three setup steps:
  1. Creates a Python virtual environment (.venv)
  2. Installs dependencies from requirements.txt
  3. Prompts for NCM API credentials and injects them into the venv activate scripts

Usage:
    python3 setup_env.py

After running, activate the venv to load everything:
    source .venv/bin/activate
"""
import os
import sys
import re
import subprocess
import getpass
import platform

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, '.venv')
REQUIREMENTS = os.path.join(PROJECT_DIR, 'requirements.txt')

MARKER_START = '# >>> NCM API credentials >>>'
MARKER_END = '# <<< NCM API credentials <<<'

CREDENTIALS = [
    ('X_CP_API_ID', 'Cradlepoint API ID (X-CP-API-ID)', False),
    ('X_CP_API_KEY', 'Cradlepoint API Key (X-CP-API-KEY)', True),
    ('X_ECM_API_ID', 'ECM API ID (X-ECM-API-ID)', False),
    ('X_ECM_API_KEY', 'ECM API Key (X-ECM-API-KEY)', True),
    ('NCM_API_TOKEN', 'API v3 Bearer Token (optional, press Enter to skip)', True),
]


# --- Step 1: Create virtual environment ---

def create_venv():
    """Create the .venv virtual environment if it doesn't exist."""
    if os.path.isdir(VENV_DIR):
        print(f"  ✓ Virtual environment already exists at .venv/")
        return

    print(f"  Creating virtual environment at .venv/ ...")
    python = sys.executable
    result = subprocess.run([python, '-m', 'venv', VENV_DIR], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error creating venv: {result.stderr}")
        sys.exit(1)
    print(f"  ✓ Virtual environment created")


# --- Step 2: Install dependencies ---

def install_dependencies():
    """Install requirements.txt into the venv."""
    if not os.path.exists(REQUIREMENTS):
        print(f"  Warning: requirements.txt not found, skipping dependency install.")
        return

    if platform.system() == 'Windows':
        pip = os.path.join(VENV_DIR, 'Scripts', 'pip')
        python = os.path.join(VENV_DIR, 'Scripts', 'python')
    else:
        pip = os.path.join(VENV_DIR, 'bin', 'pip')
        python = os.path.join(VENV_DIR, 'bin', 'python')

    print(f"  Installing dependencies from requirements.txt ...")
    # Use python -m pip to avoid bad interpreter issues
    result = subprocess.run(
        [python, '-m', 'pip', 'install', '-r', REQUIREMENTS, '--quiet'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Warning: Some packages may have failed to install:")
        print(f"  {result.stderr[:500]}")
    else:
        print(f"  ✓ Dependencies installed")


# --- Step 3: Configure API credentials ---

def prompt_for_credentials():
    """Prompt user for each credential. Returns dict of var->value."""
    print()
    print("  Enter your API credentials below.")
    print("  Keys/tokens are hidden as you type.")
    print("  Press Enter to skip optional fields.")
    print()

    creds = {}
    for var, label, is_secret in CREDENTIALS:
        while True:
            if is_secret:
                value = getpass.getpass(f"    {label}: ")
            else:
                value = input(f"    {label}: ").strip()

            is_optional = 'optional' in label.lower()
            if not value and is_optional:
                break
            if not value:
                print(f"      Required. Please enter a value.")
                continue
            creds[var] = value
            break

    return creds


def _remove_existing_block(content):
    """Remove any previously injected credential block."""
    pattern = re.compile(
        re.escape(MARKER_START) + r'.*?' + re.escape(MARKER_END),
        re.DOTALL
    )
    return pattern.sub('', content).rstrip('\n') + '\n'


def _build_bash_block(creds):
    lines = [MARKER_START]
    for var, value in creds.items():
        lines.append(f'export {var}="{value}"')
    lines.append(MARKER_END)
    return '\n'.join(lines) + '\n'


def _build_bash_deactivate_block(creds):
    return '\n'.join(f'    unset {var}' for var in creds)


def _build_fish_block(creds):
    lines = [MARKER_START]
    for var, value in creds.items():
        lines.append(f'set -gx {var} "{value}"')
    lines.append(MARKER_END)
    return '\n'.join(lines) + '\n'


def _build_csh_block(creds):
    lines = [MARKER_START]
    for var, value in creds.items():
        lines.append(f'setenv {var} "{value}"')
    lines.append(MARKER_END)
    return '\n'.join(lines) + '\n'


def update_bash_activate(creds):
    """Update .venv/bin/activate (bash/zsh)."""
    path = os.path.join(VENV_DIR, 'bin', 'activate')
    if not os.path.exists(path):
        # Windows
        path = os.path.join(VENV_DIR, 'Scripts', 'activate')
        if not os.path.exists(path):
            return

    with open(path, 'r') as f:
        content = f.read()

    content = _remove_existing_block(content)

    # Remove old unsets from deactivate
    for var in creds:
        content = content.replace(f'    unset {var}\n', '')

    # Add unsets to deactivate function
    deactivate_unsets = _build_bash_deactivate_block(creds)
    if '    unset VIRTUAL_ENV\n    unset VIRTUAL_ENV_PROMPT' in content:
        content = content.replace(
            '    unset VIRTUAL_ENV\n    unset VIRTUAL_ENV_PROMPT',
            f'    unset VIRTUAL_ENV\n    unset VIRTUAL_ENV_PROMPT\n{deactivate_unsets}'
        )

    content += '\n' + _build_bash_block(creds)

    with open(path, 'w') as f:
        f.write(content)
    print(f"    Updated: {path}")


def update_fish_activate(creds):
    """Update .venv/bin/activate.fish."""
    path = os.path.join(VENV_DIR, 'bin', 'activate.fish')
    if not os.path.exists(path):
        return

    with open(path, 'r') as f:
        content = f.read()

    content = _remove_existing_block(content)
    for var in creds:
        content = content.replace(f'    set -e {var}\n', '')

    if 'set -e VIRTUAL_ENV' in content:
        deactivate_unsets = '\n'.join(f'    set -e {var}' for var in creds)
        content = content.replace('set -e VIRTUAL_ENV', f'set -e VIRTUAL_ENV\n{deactivate_unsets}', 1)

    content += '\n' + _build_fish_block(creds)

    with open(path, 'w') as f:
        f.write(content)
    print(f"    Updated: {path}")


def update_csh_activate(creds):
    """Update .venv/bin/activate.csh."""
    path = os.path.join(VENV_DIR, 'bin', 'activate.csh')
    if not os.path.exists(path):
        return

    with open(path, 'r') as f:
        content = f.read()

    content = _remove_existing_block(content)
    for var in creds:
        content = content.replace(f'    unsetenv {var}\n', '')

    content += '\n' + _build_csh_block(creds)

    with open(path, 'w') as f:
        f.write(content)
    print(f"    Updated: {path}")


def configure_credentials():
    """Prompt for credentials and inject into activate scripts."""
    creds = prompt_for_credentials()
    if not creds:
        print("\n  No credentials entered. You can configure them later via")
        print("  the Settings panel in dashboard apps, or re-run this script.")
        return

    print()
    print("  Updating activate scripts...")
    update_bash_activate(creds)
    update_fish_activate(creds)
    update_csh_activate(creds)

    # Show what was set (masked)
    print()
    print("  Configured:")
    for var, value in creds.items():
        masked = value[:4] + '***' if len(value) > 4 else '****'
        print(f"    {var} = {masked}")


# --- Main ---

def main():
    print()
    print("=" * 60)
    print("  NCM API Samples — Environment Setup")
    print("=" * 60)

    # Step 1
    print()
    print("Step 1/3: Virtual Environment")
    create_venv()

    # Step 2
    print()
    print("Step 2/3: Install Dependencies")
    install_dependencies()

    # Step 3
    print()
    print("Step 3/3: API Credentials")
    configure_credentials()

    # Done
    print()
    print("=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("  To get started:")
    print()
    if platform.system() == 'Windows':
        print("    .venv\\Scripts\\activate")
    else:
        print("    source .venv/bin/activate")
    print()
    print("  Then run a dashboard:")
    print()
    print("    python web_apps/inventory_dashboard/serve.py")
    print("    python web_apps/cellular_health_dashboard/serve.py")
    print()


if __name__ == '__main__':
    main()
