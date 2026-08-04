#!/usr/bin/env python3
"""
Fast, dependency-free environment status report.

Designed for the SessionStart Kiro hook: it uses only the standard library,
does no network or subprocess work, and prints a few compact lines so Kiro
knows up front whether the workspace is ready.

Never prints credential values - only whether each one is present.

Usage:
    python3 scripts/utils/env_status.py
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_DIR = os.path.join(PROJECT_DIR, '.venv')
IS_WINDOWS = os.name == 'nt'

REQUIRED_VARS = ['X_CP_API_ID', 'X_CP_API_KEY', 'X_ECM_API_ID', 'X_ECM_API_KEY']
OPTIONAL_VARS = ['NCM_API_TOKEN']

# Packages that must be importable, checked by looking for them on disk rather
# than importing, which keeps this fast and avoids side effects.
EXPECTED_PACKAGES = ['fastapi', 'uvicorn', 'httpx', 'requests', 'dateutil', 'ncm']

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def venv_python():
    """Path to the venv interpreter, or None if the venv is missing/broken."""
    scripts = os.path.join(VENV_DIR, 'Scripts' if IS_WINDOWS else 'bin')
    for name in ('python.exe', 'python3.exe', 'python', 'python3'):
        candidate = os.path.join(scripts, name)
        if os.path.exists(candidate):
            return candidate
    return None


def site_packages_dirs():
    """Candidate site-packages directories inside the venv."""
    dirs = []
    if IS_WINDOWS:
        dirs.append(os.path.join(VENV_DIR, 'Lib', 'site-packages'))
    else:
        lib = os.path.join(VENV_DIR, 'lib')
        if os.path.isdir(lib):
            for entry in sorted(os.listdir(lib)):
                dirs.append(os.path.join(lib, entry, 'site-packages'))
    return [d for d in dirs if os.path.isdir(d)]


def missing_packages():
    """Names from EXPECTED_PACKAGES with no matching dir/module in site-packages."""
    found = set()
    for directory in site_packages_dirs():
        try:
            entries = os.listdir(directory)
        except OSError:
            continue
        for entry in entries:
            found.add(entry.lower())
            if entry.lower().endswith('.py'):
                found.add(entry[:-3].lower())

    return [pkg for pkg in EXPECTED_PACKAGES if pkg.lower() not in found]


def main():
    # Load .env into os.environ using the shared stdlib parser.
    try:
        from env_check import load_env_file
        load_env_file()
    except Exception:
        pass

    lines = []
    ready = True

    interpreter = venv_python()
    if interpreter is None:
        ready = False
        lines.append('venv: MISSING (.venv not found)')
    else:
        rel = os.path.relpath(interpreter, PROJECT_DIR)
        missing = missing_packages()
        if missing:
            ready = False
            lines.append(f'venv: present ({rel}) but missing packages: {", ".join(missing)}')
        else:
            lines.append(f'venv: ready ({rel})')

    missing_creds = [var for var in REQUIRED_VARS if not os.environ.get(var)]
    if missing_creds:
        ready = False
        lines.append(f'credentials: missing {", ".join(missing_creds)}')
    else:
        has_v3 = any(os.environ.get(var) for var in OPTIONAL_VARS)
        lines.append(
            'credentials: all required present'
            + (' (plus v3 token)' if has_v3 else ' (no v3 token, v3 endpoints unavailable)')
        )

    print('[NCM API Samples environment]')
    for line in lines:
        print(f'  {line}')

    if ready:
        print('  status: READY - use .venv for all Python commands.')
    else:
        launcher = 'python' if IS_WINDOWS else 'python3'
        print('  status: NOT READY')
        print(f'  fix: tell the user to run "{launcher} setup_env.py", '
              'or pull in #setup-environment and Kiro will handle it.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
