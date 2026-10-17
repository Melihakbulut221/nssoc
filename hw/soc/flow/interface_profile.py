#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resolve a verified interface bundle; LGPL cores require the explicit full profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

from prepare_interfaces import SOC, selected_pins, project_sources


def check_netlist(path, profile):
    """Guard this flow's preserved hierarchy names, not logical equivalence."""
    selected_pins(profile)
    text = path.read_text()
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    if not re.search(r'\bmodule\s+soc_top\s*\(', text):
        raise ValueError('Expected a mapped soc_top netlist')
    found = {name for name in ('u_can', 'u_spw')
             if re.search(r'\\' + name + r'\.[^\s]+\s', text)}
    expected = {'u_can', 'u_spw'} if profile == 'full' else set()
    if found != expected:
        raise ValueError(f'Mapped interface hierarchy {sorted(found)} does not match {profile}')


def resolve(profile='base', soc=SOC):
    pins = selected_pins(profile)
    bundle = soc/('gen/interfaces-full.bundle.vh' if profile == 'full'
                  else 'gen/interfaces.bundle.vh')
    manifest = json.loads(bundle.with_suffix('.json').read_text())
    if manifest.get('profile') != profile or manifest.get('pins') != pins:
        raise ValueError('Interface profile or pinned dependencies do not match')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(bundle) != manifest.get('bundle_sha256'):
        raise ValueError('Interface bundle was modified')
    projects = project_sources(profile)
    recorded_projects = manifest.get('project_inputs', {})
    if not isinstance(recorded_projects, dict) or set(recorded_projects) != set(projects):
        raise ValueError('Unexpected or missing project transformation inputs')
    for name, path in projects.items():
        if digest(path) != recorded_projects[name]:
            raise ValueError('Interface project transformation changed: ' + name)
    inputs = manifest.get('inputs', {})
    if not inputs:
        raise ValueError('Empty interface source inventory')
    seen = set()
    for name, expected in inputs.items():
        path = (soc/name).resolve()
        parts = Path(name).parts
        if len(parts) < 3 or parts[0] != 'ext' or parts[1] not in pins:
            raise ValueError('Unexpected dependency in interface bundle: '+name)
        if not path.is_relative_to((soc/'ext'/parts[1]).resolve()):
            raise ValueError('Dependency path escapes its checkout')
        if digest(path) != expected:
            raise ValueError('Interface source changed: '+name)
        seen.add(parts[1])
    if seen != set(pins):
        raise ValueError('Incomplete interface source inventory')
    return bundle.resolve(), ('-DSOC_LGPL_INTERFACES' if profile == 'full' else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('base','full'),
                        default=os.environ.get('SOC_INTERFACE_PROFILE', 'base'))
    parser.add_argument('--bundle-only', action='store_true')
    parser.add_argument('--netlist', type=Path,
                        help='also reject a mapped hierarchy from the other profile')
    args = parser.parse_args()
    try:
        bundle, define = resolve(args.profile)
        if args.netlist:
            check_netlist(args.netlist, args.profile)
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}; run make soc-interfaces-prepare SOC_INTERFACE_PROFILE={args.profile}\n')
    if args.bundle_only:
        print(bundle)
    else:
        print('IF_BUNDLE='+shlex.quote(str(bundle)))
        print('IF_DEFINE='+shlex.quote(define))


if __name__ == '__main__':
    main()
