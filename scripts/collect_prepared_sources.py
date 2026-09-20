#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Retain byte-replayed pinned dependency sources for offline structural tests.

The pristine Ibex sv2v output and interface bundle must match independent
scratch replays. This is not a mapped netlist or a substitute for RTL tests.
"""
import argparse
from datetime import date
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def collect(ibex_replay, interface_replay, output):
    archive = output.with_suffix('.tar.gz')
    notice = output.with_name(output.stem + '-NOTICES.txt')
    if any(p.exists() for p in (output, archive, notice)):
        raise ValueError('Refusing to replace prepared-source evidence')
    soc = ROOT / 'hw/soc'
    pin = subprocess.check_output(['git', '-C', str(soc / 'ext/ibex'),
                                   'rev-parse', 'HEAD'], text=True).strip()
    assert pin == '34b0705760ef3dfa00e99637432473d2be8f22f3'
    assert not subprocess.check_output(['git', '-C', str(soc / 'ext/ibex'),
                                       'status', '--porcelain'], text=True).strip()
    paths = sorted((soc / 'gen').glob('*.v'))
    assert {p.name for p in paths} == {p.name for p in ibex_replay.glob('*.v')}
    for p in paths:
        assert p.read_bytes() == (ibex_replay / p.name).read_bytes(), p
    for name in ['interfaces.bundle.vh', 'interfaces.bundle.json',
                 'interfaces-full.bundle.vh', 'interfaces-full.bundle.json']:
        p = soc / 'gen' / name
        assert p.read_bytes() == (interface_replay / name).read_bytes(), p
        paths.append(p)
    source_record = {profile: json.loads((soc / 'gen' / name).read_text())
                     for profile, name in [('base', 'interfaces.bundle.json'),
                                           ('full', 'interfaces-full.bundle.json')]}
    content = {str(p.relative_to(ROOT)): p.read_bytes() for p in paths}
    files = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
             for name, data in content.items()}
    with archive.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as stream:
            for name, data in content.items():
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(data), 0o644
                stream.addfile(member, io.BytesIO(data))
    old_notice = (ROOT / 'docs/evidence/ethernet-netlist-20260920-NOTICES.txt').read_text()
    notice.write_text('Prepared source snapshots: component licences and notices\n\n'
                     'Source files retain their original headers and licences. Ibex is Apache-2.0;\n'
                     'SpaceWire/CAN are LGPL-2.1-or-later; I2C/Ethernet/AXIS are MIT.\n'
                     'Exact upstream commits, transformation hashes and replay commands are in\n'
                     + output.name + '. Fetch corresponding sources with\n'
                     'make soc-prepare SOC_INTERFACE_PROFILE=full in this repository.\n'
                     'The base bundle contains no SpaceWire or CAN source. The optional full\n'
                     'bundle retains the CAN Bosch protocol notice, without a clearance claim.\n\n'
                     + old_notice[old_notice.index('The Ibex Project'):].rstrip() + '\n')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    result = {'date': date.today().isoformat(), 'scope': __doc__, 'ibex_commit': pin,
              'sv2v_version': subprocess.check_output([str(soc / 'tools/sv2v-Linux/sv2v'), '--version'], text=True).strip(),
              'interface_source_record': source_record,
              'replay_commands': [
                  'bash hw/soc/flow/sv2v_ibex.sh hw/soc/ext/ibex <fresh-output> hw/soc/tools/sv2v-Linux/sv2v',
                  'prepare_interfaces.prepare(base) and prepare(full) with SOC pointing to a fresh scratch root and read-only ext symlink'],
              'replays_byte_identical': True,
              'transform_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                  [soc / 'flow/sv2v_ibex.sh', soc / 'flow/prepare_interfaces.py']},
              'directories': [], 'files': files,
              'archive': {'file': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive)},
              'component_notices': {'file': notice.name, 'sha256': sha(notice)}}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'files': len(files), 'archive_bytes': archive.stat().st_size}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ibex-replay', required=True, type=Path)
    parser.add_argument('--interface-replay', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    collect(args.ibex_replay, args.interface_replay, args.output)
