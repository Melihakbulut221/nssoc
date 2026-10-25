#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the worst reported paths to exact saved OpenDB signal connectivity."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-timing-paths'
SOURCE = ROOT / 'cloud-global-setup'
ARCHIVE = 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/global-setup-cloud-buffered-38307868589-1.tar.gz'
ARCHIVE_SHA = '56ea57e8aeff5027d0c5cf2e26d83adca5f4cab03ffe1c083548c322bebc9744'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def native():
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, str(SOURCE / 'global.odb'))
    block = db.getChip().getBlock()
    # OpenSTA renders escaped bus brackets without OpenDB's escape character.
    # Require a unique reversible spelling, rather than fuzzy name matching.
    names = {}
    for inst in block.getInsts():
        rendered = re.sub(r'\\([\[\]])', r'\1', inst.getName())
        assert rendered not in names, ('Ambiguous rendered instance', rendered)
        names[rendered] = inst
    log = (SOURCE / 'native.log').read_text()
    paths = []
    for phase in re.split(r'(?m)^CORNER_', log)[1:]:
        phase_name = phase.splitlines()[0].strip()
        if not re.fullmatch(r'(slow|typical|fast)_(max|min)', phase_name):
            continue
        groups = set()
        for part in phase.split('Startpoint:')[1:]:
            group = re.search(r'(?m)^Path Group: (.+)$', part)
            if group is None or group[1] in groups:
                continue
            groups.add(group[1])
            # report_checks returns worst first within each group. Preserve the
            # complete original path while probing only its data/clock cells.
            slack = re.search(r'(?m)^\s*([\d.+-]+)\s+slack \((?:VIOLATED|MET)\)', part)
            assert slack, (phase_name, group[1])
            part = part[:slack.end()]
            cells = []
            for line in part.splitlines():
                match = re.search(r'[\^v] (.+)/([^/ ]+) \((sg13g2_\w+|RM_\w+)\)\s*$', line)
                if not match:
                    continue
                name, pin, master = match.groups()
                inst = names.get(name)
                assert inst and inst.getMaster().getName() == master, (
                    name, master, inst.getName() if inst else None,
                    inst.getMaster().getName() if inst else None)
                term = inst.findITerm(pin)
                assert term, (name, pin)
                pins = {}
                for t in inst.getITerms():
                    if str(t.getSigType()) in ('POWER', 'GROUND'):
                        continue
                    net = t.getNet()
                    peers = []
                    if net:
                        for peer in net.getITerms():
                            if str(peer.getIoType()) == 'OUTPUT':
                                peers.append(peer.getInst().getName() + '/' + peer.getMTerm().getName())
                    pins[t.getMTerm().getName()] = dict(
                        direction=str(t.getIoType()), net=net.getName() if net else None,
                        drivers=sorted(peers),
                        terminals=len(net.getITerms()) if net else 0,
                        ports=sorted(t.getName() for t in net.getBTerms()) if net else [])
                cells.append(dict(instance=name, odb_instance=inst.getName(), master=master, pin=pin,
                                  location=list(inst.getLocation()), pins=pins,
                                  reported_timing_line=line.strip()))
            assert cells, (phase_name, group[1])
            paths.append(dict(phase=phase_name, group=group[1], slack_ns=float(slack[1]),
                              native_path='Startpoint:' + part, cells=cells))
    expected = json.loads((SOURCE / 'result.json').read_text())['phases']
    for phase, values in expected.items():
        actual = {p['group']: p for p in paths if p['phase'] == phase}
        assert actual.keys() == values['groups'].keys(), phase
        for group, value in values['groups'].items():
            assert abs(actual[group]['slack_ns'] - value['worst_slack_ns']) <= 1e-6
    (OUT / 'paths.json').write_text(json.dumps(dict(
        status='PASS_EXACT_REPORTED_PATH_CONNECTIVITY_BINDING_NOT_TIMING_CLOSURE',
        source_odb_sha256=sha(SOURCE / 'global.odb'),
        source_log_sha256=sha(SOURCE / 'native.log'), paths=paths), indent=2) + '\n')


def main():
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False, source_url=ARCHIVE,
                  scope='Read-only native mapping of each worst reported corner/group path. No netlist, constraints, clock or physical state edits; original timing failures preserved.')
    try:
        packed = OUT / 'input.tar.gz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '4', ARCHIVE, '-o', str(packed)], check=True)
        assert sha(packed) == ARCHIVE_SHA
        result['archive_sha256'] = ARCHIVE_SHA
        assert not SOURCE.exists()
        with tarfile.open(packed) as tar:
            tar.extractall(ROOT, filter='data')
        packed.unlink()
        pinned = json.loads((ROOT / 'docs/evidence/cloud-global-route-pair-20261013.json').read_text())['sources']['buffered']['outputs']
        for name in ('global.odb', 'native.log'):
            assert sha(SOURCE / name) == pinned[name]
        with (OUT / 'native.log').open('w') as log:
            subprocess.run([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', '-python', str(Path(__file__).resolve())], env=dict(os.environ, NSSOC_NATIVE_PATH_TRACE='1'), stdout=log, stderr=subprocess.STDOUT, check=True)
        for name in ('global.odb', 'native.log'):
            assert sha(SOURCE / name) == pinned[name]
        trace = json.loads((OUT / 'paths.json').read_text())
        result.update(status=trace['status'], paths=len(trace['paths']), report_sha256=sha(OUT / 'paths.json'))
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    native() if os.environ.get('NSSOC_NATIVE_PATH_TRACE') == '1' else main()
