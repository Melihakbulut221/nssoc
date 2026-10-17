#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read exact failed native ECO artifacts and expose every multiply driven bit."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from publish_cloud_results import publish_results

NAME = 'ethernet-hold-1-38336760984-1.tar.gz'
SHA = '419d4262aa667447cb8592a0506d2df3e15136e98518d36759edf74c8b79ac15'
BASE = 'cloud-ethernet-hold/'


def inspect(module):
    drivers = {}
    for name, cell in module['cells'].items():
        for pin, direction in cell['port_directions'].items():
            if direction == 'output':
                for bit in cell['connections'][pin]:
                    drivers.setdefault(str(bit), []).append(dict(cell=name, master=cell['type'], pin=pin,
                        connections=cell['connections']))
    for name, port in module['ports'].items():
        if port['direction'] == 'input':
            for bit in port['bits']:
                drivers.setdefault(str(bit), []).append(dict(port=name))
    bad = {bit: rows for bit, rows in drivers.items() if len(rows) > 1}
    return dict(multiple_drivers=bad,
        named_nets={name: row for name, row in module['netnames'].items()
                    if any(str(bit) in bad for bit in row['bits'])},
        ports={name: row for name, row in module['ports'].items()
               if name.startswith('eth_tx') or any(str(bit) in bad for bit in row['bits'])})


def main():
    result = dict(source_archive=NAME, source_archive_sha256=SHA, adopted=False)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / NAME
        subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--silent', '--show-error',
            'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/'+NAME,
            '-o', str(path)], check=True)
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == SHA
        with tarfile.open(path) as archive:
            for stage in ('before', 'after'):
                name = BASE+'logic/'+stage+'.json'
                raw = archive.extractfile(name).read()
                modules = json.loads(raw)['modules']
                tops = [m for m in modules.values() if m.get('attributes', {}).get('top')]
                assert len(tops) == 1
                result[stage] = dict(member=name, sha256=hashlib.sha256(raw).hexdigest(), **inspect(tops[0]))
            raw = archive.extractfile(BASE+'candidate.v').read()
            lines = raw.decode().splitlines()
            selected = set()
            for number, line in enumerate(lines):
                if 'eth_tx' in line or 'nssoc_eth_hold_' in line:
                    selected.update(range(max(0, number-2), min(len(lines), number+5)))
            result['native_verilog'] = dict(sha256=hashlib.sha256(raw).hexdigest(),
                selected_lines=[dict(line=i+1, text=lines[i]) for i in sorted(selected)])
    out = Path('ethernet-hold-multiple-driver-diagnosis.json')
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(publish_results('hold-diagnosis', [out])), flush=True)
    print(out.read_text(), flush=True)


if __name__ == '__main__':
    main()
