#!/usr/bin/env python3
"""
Interactive setup script for NCM API credentials.
Prompts for all API keys and the v3 token, then injects them into
the .venv activate scripts so they're loaded automatically on activation.

Usage:
    python setup_env.py
    # or
    .venv/bin/python setup_env.py

After running, activate the venv to load the keys:
    source .venv/bin/activate
"""
import os
import sys
import re
import getpass

VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv')

MARKER_START = '# >>> NCM API credentials >>>'
MARKER_END = '# <<< NCM API credentials <<<'

CREDENTIALS = [
    ('CP_API_ID', 'Cradlepoint API ID (X-CP-API-ID)', False),
    ('CP_API_KEY', 'Cradlepoint API Key (X-CP-API-KEY)', True),
    ('ECM_API_ID', 'ECM API ID (X-ECM-API-ID)', False),
    ('ECM_API_KEY', 'ECM API Key (X-ECM-API-KEY)', True),
    ('CP_API_TOKEN', 'API v3 Bearer Token (optional, press Enter to skip)', True),
]


def prompt_for_credentials():
    """Prompt user for each credential. Returns dict of var->value."""
    print()
    print("=" * 60)
    print("  NCM API Credential Setup")
    print("=" * 60)
    print()
    print("Enter your API credentials below.")
    print("Keys/tokens are hidden as you type.")
    print("For v3 token: press Enter to skip if you only use v2.")
    print()

    creds = {}
    for var, label, is_secret in CREDENTIALS:
        while True:
            if is_secret:
                value = getpass.getpass(f"  {label}: ")
            else:
                value = input(f"  {label}: ").strip()

            is_optional = 'optional' in label.lower()
            if not value and is_optional:
                break
            if not value:
                print(f"    Required. Please enter a value.")
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
    """Build the bash/zsh export block."""
    lines = [MARKER_START]
    for var, value in creds.items():
        lines.append(f'export {var}="{value}"')
    lines.append(MARKER_END)
    return '\n'.join(lines) + '\n'


def _build_bash_deactivate_block(creds):
    """Build unset commands to add to the deactivate function."""
    lines = [f'    unset {var}' for var in creds]
    return '\n'.join(lines)


def _build_fish_block(creds):
    """Build the fish shell set -gx block."""
    lines = [MARKER_START]
    for var, value in creds.items():
        lines.append(f'set -gx {var} "{value}"')
    lines.append(MARKER_END)
    return '\n'.join(lines) + '\n'


def _build_fish_deactivate_block(creds):
    """Build fish erase commands."""
    lines = [f'    set -e {var}' for var in creds]
    return '\n'.join(lines)


def _build_csh_block(creds):
    """Build the csh/tcsh setenv block."""
    lines = [MARKER_START]
    for var, value in creds.items():
        lines.append(f'setenv {var} "{value}"')
    lines.append(MARKER_END)
    return '\n'.join(lines) + '\n'


def _build_csh_deactivate_block(creds):
    """Build csh unsetenv commands."""
    lines = [f'    unsetenv {var}' for var in creds]
    return '\n'.join(lines)


def update_bash_activate(creds):
    """Update .venv/bin/activate (bash/zsh)."""
    path = os.path.join(VENV_DIR, 'bin', 'activate')
    if not os.path.exists(path):
        print(f"  Warning: {path} not found, skipping.")
        return

    with open(path, 'r') as f:
        content = f.read()

    content = _remove_existing_block(content)

    for var in creds:
        content = content.replace(f'    unset {var}\n', '')

    deactivate_unsets = _build_bash_deactivate_block(creds)
    content = content.replace(
        '    unset VIRTUAL_ENV\n    unset VIRTUAL_ENV_PROMPT',
        f'    unset VIRTUAL_ENV\n    unset VIRTUAL_ENV_PROMPT\n{deactivate_unsets}'
    )

    content += '\n' + _build_bash_block(creds)

    with open(path, 'w') as f:
        f.write(content)
    print(f"  Updated: {path}")


def update_fish_activate(creds):
    """Update .venv/bin/activate.fish."""
    path = os.path.join(VENV_DIR, 'bin', 'activate.fish')
    if not os.path.exists(path):
        print(f"  Warning: {path} not found, skipping.")
        return

    with open(path, 'r') as f:
        content = f.read()

    content = _remove_existing_block(content)

    for var in creds:
        content = content.replace(f'    set -e {var}\n', '')

    deactivate_unsets = _build_fish_deactivate_block(creds)
    if 'function deactivate' in content:
        content = content.replace(
            'set -e VIRTUAL_ENV',
            f'set -e VIRTUAL_ENV\n{deactivate_unsets}',
            1
        )

    content += '\n' + _build_fish_block(creds)

    with open(path, 'w') as f:
        f.write(content)
    print(f"  Updated: {path}")


def update_csh_activate(creds):
    """Update .venv/bin/activate.csh."""
    path = os.path.join(VENV_DIR, 'bin', 'activate.csh')
    if not os.path.exists(path):
        print(f"  Warning: {path} not found, skipping.")
        return

    with open(path, 'r') as f:
        content = f.read()

    content = _remove_existing_block(content)

    for var in creds:
        content = content.replace(f'    unsetenv {var}\n', '')

    content += '\n' + _build_csh_block(creds)

    with open(path, 'w') as f:
        f.write(content)
    print(f"  Updated: {path}")


def main():
    if not os.path.isdir(VENV_DIR):
        print(f"Error: Virtual environment not found at {VENV_DIR}")
        print("Create it first: python3 -m venv .venv")
        sys.exit(1)

    creds = prompt_for_credentials()

    if not creds:
        print("\nNo credentials entered. Nothing to do.")
        sys.exit(0)

    print()
    print("Updating activate scripts...")
    update_bash_activate(creds)
    update_fish_activate(creds)
    update_csh_activate(creds)

    print()
    print("=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("To load your credentials, run:")
    print()
    print("  source .venv/bin/activate")
    print()
    print("Your API keys will be set as environment variables")
    print("automatically every time you activate the venv.")
    print()
    print("To update credentials later, just run this script again.")
    print()

    # Show what was set (masked)
    print("Configured variables:")
    for var, value in creds.items():
        masked = value[:4] + '***' + value[-4:] if len(value) > 8 else '****'
        print(f"  {var} = {masked}")
    print()


if __name__ == '__main__':
    main()
