#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Retain recovered original F6 artifacts; refuse replacements for historical bytes.

Reads another checkout without modifying it. The three large artifacts must
match the pre-existing digest ledger; small run records must match the already
committed records. The archive contains original selected files and actual
step-directory names, not a newly generated or complete physical run.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
LARGE = [
    'hw/openlane/pilot_ihp/runs/signoff-6x2/final/def/tt_um_melihakbulut_nssoc.def',
    'hw/openlane/pilot_ihp/runs/signoff-6x2/final/nl/tt_um_melihakbulut_nssoc.nl.v',
    'hw/soc/out/s70-rom0-syn/soc_top.netlist.v',
]
RUNS = {'g0gates2': 'hw/openlane/aer_fifo/runs/g0gates2',
        'signoff-6x2': 'hw/openlane/pilot_ihp/runs/signoff-6x2'}


def collect(source, output):
    source = source.resolve()
    if output.exists():
        raise ValueError('Refusing to replace retained recovery')
    ledger = list(csv.DictReader((line for line in
        (ROOT / 'docs/80-artefact-digests.tsv').read_text().splitlines()
        if line.strip() and not line.startswith('#')), delimiter='\t'))
    files = list(LARGE)
    for tag, base in RUNS.items():
        for name, relative in [('metrics.json', 'final/metrics.json'),
                               ('resolved.json', 'resolved.json')]:
            path = base + '/' + relative
            if (source / path).read_bytes() != (ROOT / 'docs/evidence' / tag / name).read_bytes():
                raise ValueError('Recovered run disagrees with existing record: ' + path)
            files.append(path)
    files += ['hw/openlane/aer_fifo/runs/g0gates2/' + path for path in (
        'flow.log', 'error.log', '64-magic-drc/reports/drc.magic.rpt',
        '65-klayout-drc/reports/drc.klayout.json')]
    files += [str(p.relative_to(source)) for p in
              (source / RUNS['signoff-6x2']).glob('*-yosys-jsonheader/*.h.json')]
    directories = sorted({str(p.relative_to(source)) for base in RUNS.values()
                          for p in (source / base).iterdir() if p.is_dir()})
    records, content = {}, {}
    for name in sorted(files):
        data = (source / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if name in LARGE:
            identities = {(int(row['bytes']), row['sha256'])
                          for row in ledger if row['path'] == name}
            if identities != {(len(data), digest)}:
                raise ValueError('Not the original historical artifact: ' + name)
        records[name] = {'bytes': len(data), 'sha256': digest}
        content[name] = data
    notice = ('Recovered historical artifacts: component notices\n\n'
              'Project RTL and its generated layout/netlist: CERN-OHL-W-2.0.\n'
              'Ibex portions of the old SoC netlist: Apache-2.0, lowRISC contributors.\n'
              'This product includes hardware developed as part of the Ibex and OpenTitan projects.\n'
              'Ibex originated as zero-riscy at ETH Zurich and University of Bologna.\n'
              'These snapshots retain their source licences; they are not CC-BY documentation.\n'
              'No PDK cell implementation or proprietary IP is included.\n'
              'Corresponding project sources and historical build commands:\n'
              'https://github.com/Melihakbulut221/nssoc (docs/12, docs/31-34, docs/60).\n\n')
    for license_name in ['CERN-OHL-W-2.0', 'Apache-2.0']:
        notice += (ROOT / 'LICENSES' / (license_name + '.txt')).read_text() + '\n'
    notice_path = output.with_name(output.stem + '-NOTICES.txt')
    archive = output.with_suffix('.tar.gz')
    if notice_path.exists() or archive.exists():
        raise ValueError('Refusing to overwrite archive or notices')
    notice_path.write_text(notice)
    with archive.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as stream:
            for name in directories:
                member = tarfile.TarInfo(name)
                member.type, member.mode = tarfile.DIRTYPE, 0o755
                stream.addfile(member)
            for name, data in content.items():
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(data), 0o644
                stream.addfile(member, io.BytesIO(data))
    for name, info in records.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Source changed while collecting: ' + name)
    result = {
        'date': '2026-09-20', 'scope': __doc__, 'source_root': str(source),
        'source_checkout_head': subprocess.check_output(['git', '-C', str(source),
                                                        'rev-parse', 'HEAD'], text=True).strip(),
        'source_files_unchanged': True, 'historical_identity_matches': LARGE,
        'runs': RUNS, 'directories': directories, 'files': records,
        'archive': {'file': archive.name, 'bytes': archive.stat().st_size,
                    'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()},
        'component_notices': {'file': notice_path.name,
                             'sha256': hashlib.sha256(notice_path.read_bytes()).hexdigest()},
    }
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'archive_bytes': archive.stat().st_size,
                      'files': len(records), 'directories': len(directories)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    collect(args.source_root, args.output)
