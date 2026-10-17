#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run inside the verified devshell: fresh full IHP PDK and retained SPM flow.

This is a tool/PDK integration check, not a SoC physical acceptance result.
The caller verifies the AppImage with bootstrap_flow.py before executing it.
"""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.0.5'
PDK = 'ihp-sg13g2'
TOOLS = ('librelane', 'ciel', 'openroad', 'yosys', 'magic', 'klayout', 'netgen')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            value.update(chunk)
    return value.hexdigest()


def fresh_path(path, parent):
    path = path.absolute()
    if path.exists() or path.is_symlink():
        raise ValueError('Refusing existing output/install path: ' + str(path))
    if not path.resolve().is_relative_to(parent.resolve()) or path.resolve() == parent.resolve():
        raise ValueError('Path must be below ' + str(parent))
    return path


def pdk_pin(text):
    matches = re.findall(r'^ihp-sg13g2:\s*([0-9a-f]{40})\s*$', text, re.M)
    if len(matches) != 1:
        raise ValueError('Expected one full IHP pin in LibreLane pdk_hashes.yaml')
    return matches[0]


def run_command(command, cwd, log, timeout=2400):
    start = time.monotonic()
    with log.open('x') as stream:
        result = subprocess.run(command, cwd=cwd, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    return {'command': command, 'returncode': result.returncode,
            'elapsed_s': time.monotonic()-start, 'log_sha256': sha(log)}


def check(out, pdk_root):
    out = fresh_path(out, ROOT/'hw/soc/out')
    pdk_root = fresh_path(pdk_root, ROOT/'hw/soc/tools')
    out.mkdir(parents=True)
    result = {'status': 'FAIL', 'scope': 'LibreLane devshell / full IHP PDK / upstream SPM example only',
              'source_sha256': sha(Path(__file__)), 'commands': []}
    try:
        result['librelane_version'] = importlib.metadata.version('librelane')
        if result['librelane_version'] != VERSION:
            raise ValueError('Expected LibreLane ' + VERSION)
        package = Path(importlib.util.find_spec('librelane').origin).parent
        pins = package/'pdk_hashes.yaml'
        pin = pdk_pin(pins.read_text())
        result['pdk_pin'] = pin
        result['pdk_hashes_sha256'] = sha(pins)
        result['tools'] = {}
        for tool in TOOLS:
            executable = shutil.which(tool)
            if not executable:
                raise ValueError('Missing devshell tool: ' + tool)
            path = Path(executable).resolve()
            result['tools'][tool] = {'path': str(path), 'sha256': sha(path)}
        for name, command in (
            ('librelane-version', ['librelane', '--version']),
            ('openroad-version', ['openroad', '-version']),
            ('yosys-version', ['yosys', '-V']),
            ('pdk-install', ['ciel', 'enable', '--pdk', PDK,
                             '--pdk-root', str(pdk_root), pin]),
        ):
            row = run_command(command, ROOT, out/(name+'.log'))
            result['commands'].append(row)
            if row['returncode']:
                raise ValueError(name + ' failed; see retained log')
        enabled = (pdk_root/PDK).resolve(strict=True)
        if enabled.parent.name != pin or not enabled.is_relative_to(pdk_root.resolve()):
            raise ValueError('Enabled full PDK differs from the package pin')
        result['enabled_pdk'] = str(enabled)
        row = run_command(['librelane', '--pdk', PDK, '--pdk-root', str(pdk_root),
                           '--run-tag', 'BOOTSTRAP', '--run-example', 'spm'],
                          out, out/'spm-flow.log')
        result['commands'].append(row)
        if row['returncode']:
            raise ValueError('SPM physical flow failed; see retained log')
        final = out/'spm/runs/BOOTSTRAP/final'
        # A process exit alone is insufficient: require actual final layout
        # and netlist views from this fresh run, retaining their identities.
        views = sorted(final.rglob('*.gds')) + sorted(final.rglob('*.def')) + sorted(final.rglob('*.v'))
        if not all(any(p.suffix == suffix for p in views) for suffix in ('.gds','.def','.v')):
            raise ValueError('SPM flow returned without all required final views')
        if any(p.stat().st_size == 0 for p in views):
            raise ValueError('Empty SPM final view')
        result['views'] = {str(p.relative_to(out)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in views}
        result['status'] = 'PASS'
    except (OSError, ValueError, subprocess.SubprocessError, importlib.metadata.PackageNotFoundError) as error:
        result['error'] = str(error)
    finally:
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'hw/soc/out/physical-bootstrap')
    parser.add_argument('--pdk-root', type=Path, default=ROOT/'hw/soc/tools/pdk-bootstrap')
    args = parser.parse_args()
    try:
        result = check(args.output, args.pdk_root)
    except ValueError as error:
        parser.exit(2, str(error)+'\n')
    print(result['status'] + ': ' + result.get('error', result['scope']))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
