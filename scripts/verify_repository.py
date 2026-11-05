#!/usr/bin/env python3
"""Check staged/tracked publication inputs without printing matched secret values."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NOTES = {'HANDOFF.md', 'HANDOFF_ONDEVICE.md', 'NEXT_CODEX_PROMPT.txt', 'TEST_RESULTS.md'}
FORBIDDEN_SUFFIXES = {'.mobiledevicepairing', '.mobiledevicepair', '.mobileprovision', '.p12', '.p8', '.pem', '.key', '.ipa', '.log'}
PATTERNS = {
    'private key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub token': re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}'),
    'host path': re.compile(rb'/(?:Users|home)/[A-Za-z0-9_\-]+/'),
    'device identifier': re.compile(rb'(?<![a-fA-F0-9])[a-fA-F0-9]{8}-[a-fA-F0-9]{16}(?![a-fA-F0-9])'),
    'Apple account address': re.compile(rb'\b[A-Za-z0-9._%+\-]+@(?:icloud|me|mac)\.com\b', re.I),
}


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def check(tracked: bool = False) -> list[str]:
    args = ['ls-files', '-z'] if tracked else ['diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z']
    paths = [p.decode() for p in git(*args).split(b'\0') if p]
    issues = []
    for name in paths:
        p = Path(name)
        if (name in PRIVATE_NOTES or p.suffix.lower() in FORBIDDEN_SUFFIXES
                or p.name in {'pairingFile.plist', 'rp_pairing_file.plist', '.env'}
                or any(part in {'.venv', 'node_modules', '.build', 'DerivedData', 'xcuserdata'} for part in p.parts)):
            issues.append(f'{name}: forbidden publication path')
            continue
        data = git('show', ':' + name)
        if b'\0' in data[:8192]:
            if p.suffix.lower() != '.png':
                issues.append(f'{name}: unexpected binary')
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                issues.append(f'{name}: {label} pattern')
    names = set(paths)
    if tracked and 'ondevice/manifest.json' in names:
        manifest = json.loads(git('show', ':ondevice/manifest.json'))
        for item in manifest['patches']:
            name = 'ondevice/patches/' + item['patch']
            if name not in names or hashlib.sha256(git('show', ':' + name)).hexdigest() != item['sha256']:
                issues.append(f'{name}: missing or mismatched patch')
    print(f'Checked {len(paths)} publication files; {len(issues)} issue(s).')
    return issues


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tracked', action='store_true', help='Check every tracked index entry')
    issues = check(parser.parse_args().tracked)
    for issue in issues:
        print(issue)
    sys.exit(bool(issues))
