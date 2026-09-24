#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove retained ECO equations plus explicitly checked combinational duplication.

Run in the pinned LibreLane tool environment. All inputs and generated JSON are
hashed; Yosys only elaborates connectivity with the actual Liberty interfaces.
See eco_logic_clones.py and eco_logic.py for the limited equivalence scope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from eco_logic import standard_models
from eco_logic_clones import compare


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def quote(path):
    return '"' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--top', default='soc_top')
    parser.add_argument('--liberty', required=True, type=Path)
    parser.add_argument('--macro-liberty', action='append', type=Path, default=[])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z_]\w*', args.top):
        parser.error('Unsupported top identifier')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources = [args.before, args.after, args.liberty, *args.macro_liberty,
               Path(__file__), Path(__file__).with_name('eco_logic.py'),
               Path(__file__).with_name('eco_logic_clones.py')]
    expected = {str(p.resolve()): digest(p) for p in sources}
    version = subprocess.run(['yosys', '-V'], capture_output=True, text=True, check=True).stdout.strip()
    models = standard_models(args.liberty.read_text())
    modules = []
    for name, netlist in [('before', args.before), ('after', args.after)]:
        script = '\n'.join('read_liberty -lib ' + quote(p.resolve())
                           for p in [args.liberty, *args.macro_liberty])
        script += f'\nwrite_json {quote(output / (name + "-libraries.json"))}\n'
        script += f'read_verilog {quote(netlist.resolve())}\nhierarchy -check -top {args.top}\n'
        script += f'write_json {quote(output / (name + ".json"))}\n'
        (output / (name + '.ys')).write_text(script)
        with (output / (name + '.log')).open('w') as stream:
            subprocess.run(['yosys', '-s', str(output / (name + '.ys'))],
                           stdout=stream, stderr=subprocess.STDOUT, check=True)
        modules.append(json.loads((output / (name + '.json')).read_text())['modules'][args.top])
    libraries = json.loads((output / 'before-libraries.json').read_text())['modules']
    if libraries != json.loads((output / 'after-libraries.json').read_text())['modules']:
        raise ValueError('Elaborated library interfaces changed')
    result = compare(*modules, libraries, models)
    if any(digest(p) != sha for p, sha in expected.items()):
        raise ValueError('Input changed during proof')
    result.update(status='PASS within scope', yosys_version=version, sources=expected,
                  scope=('Combinational duplicate output equations, retained cell inputs and state '
                         'definitions; positive buffer contraction and Boolean pin permutations. '
                         'Added state and opaque macro duplicates are forbidden. Unchanged opaque masters require '
                         'identical input equations. Excludes timing, analog, SRAM interiors, '
                         'initialization, CDC and extracted physical connectivity.'),
                  generated={p.name: digest(p) for p in output.iterdir() if p.is_file()})
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sources', 'generated')}, indent=2))


if __name__ == '__main__':
    main()
