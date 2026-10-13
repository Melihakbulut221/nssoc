#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read the preserved exact-buffer placement timing report on a hosted runner."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tarfile

from read_opensta_phase_slacks import parse_phases

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-buffer-timing'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def native():
    """Resolve every reported cell to exact native placement and signal nets."""
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, str(OUT / 'relocated-placement.odb'))
    block = db.getChip().getBlock()
    scale = block.getDbUnitsPerMicron()
    text = (OUT / 'relocated-placement-sta.log').read_text()
    reported = {}
    for name, pin, master in re.findall(r'[^\n]*[\^v] +(.+?)/(\S+) +\(([^)]+)\)\s*$', text, re.M):
        name = name.strip()
        if name in reported:
            assert reported[name] == master, (name, reported[name], master)
        reported[name] = master
    assert reported
    instances = {i.getName(): i for i in block.getInsts()}
    cells, nets = {}, {}
    for name, master in sorted(reported.items()):
        assert name in instances, ('Unbound timing cell', name)
        inst = instances[name]
        assert inst.getMaster().getName() == master
        rect = inst.getBBox()
        pins = []
        for terminal in inst.getITerms():
            net = terminal.getNet()
            pins.append(dict(pin=terminal.getMTerm().getName(), direction=str(terminal.getIoType()),
                             net=None if net is None else net.getName()))
            if net is None or str(net.getSigType()) in ('POWER', 'GROUND'):
                continue
            if net.getName() not in nets:
                nets[net.getName()] = dict(signal_type=str(net.getSigType()),
                    terminals=[dict(instance=t.getInst().getName(), master=t.getInst().getMaster().getName(),
                                    pin=t.getMTerm().getName(), direction=str(t.getIoType()))
                               for t in net.getITerms()],
                    boundary_pins=[t.getName() for t in net.getBTerms()])
        cells[name] = dict(master=master, pins=pins,
                          bbox_um=[v/scale for v in (rect.xMin(),rect.yMin(),rect.xMax(),rect.yMax())])
    result = dict(status='COMPLETE_NATIVE_REPORTED_TIMING_CELL_BINDING', timing_accepted=False,
                  odb_sha256=sha(OUT / 'relocated-placement.odb'),
                  sta_log_sha256=sha(OUT / 'relocated-placement-sta.log'),
                  reported_cells=len(reported), cells=cells, nets=nets,
                  scope='Read-only binding of all reported cells and their incident nets. Placement estimates only.')
    (OUT / 'native-cells.json').write_text(json.dumps(result, indent=2) + '\n')

def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Archive readback runs only on GitHub')
    evidence_path = ROOT / 'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json'
    evidence = json.loads(evidence_path.read_text())
    assert evidence['run'] == 38371498733
    assert evidence['status'] == 'FAILED_NATIVE_GLOBAL_ROUTE_CONGESTION'
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', timing_accepted=False, source_run=evidence['run'],
                  evidence_sha256=sha(evidence_path), archive=evidence['receipt'],
                  scope='Exact preserved placement estimates only. No routing, timing ECO or signoff acceptance.')
    try:
        packed = OUT / 'source.tar.gz'
        receipt = evidence['receipt']
        subprocess.run(['curl', '--fail', '--location', '--retry', '4',
                        receipt['url'], '-o', str(packed)], check=True)
        assert packed.stat().st_size == receipt['bytes']
        assert sha(packed) == receipt['sha256']
        names = ('relocated-placement-sta.log', 'relocated-placement-sta.tcl', 'relocated-placement.odb')
        wanted = {'cloud-newer-postcts/' + name: name for name in names}
        found = set()
        with tarfile.open(packed, 'r|gz') as archive:
            for member in archive:
                if member.name in wanted:
                    assert member.name not in found and member.isfile() and member.size < 100_000_000
                    name = wanted[member.name]
                    (OUT / name).write_bytes(archive.extractfile(member).read())
                    assert sha(OUT / name) == evidence['failure_outputs'][name]
                    found.add(member.name)
        assert found == set(wanted)
        packed.unlink()
        phases = parse_phases((OUT / 'relocated-placement-sta.log').read_text(), 'CORNER')
        assert set(phases) == {corner + '_' + kind for corner in ('slow', 'typical', 'fast') for kind in ('min', 'max')}
        protected = {name: sha(OUT / name) for name in names}
        with (OUT / 'native.log').open('w') as log:
            code = subprocess.call([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', '-python', str(Path(__file__).resolve())],
                env=dict(os.environ, CLOUD_BUFFER_TIMING_NATIVE='1'), stdout=log, stderr=subprocess.STDOUT)
        assert code == 0, ('native-binding', code)
        assert all(sha(OUT / name) == digest for name, digest in protected.items())
        binding = json.loads((OUT / 'native-cells.json').read_text())
        result.update(native_binding_sha256=sha(OUT / 'native-cells.json'),
                      native_reported_cells=binding['reported_cells'])
        result.update(status='COMPLETE_EXACT_PLACEMENT_TIMING_REPORT_READBACK',
                      placement_odb_sha256=evidence['failure_outputs']['relocated-placement.odb'],
                      phases=phases, restored={name:sha(OUT / name) for name in names})
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

if __name__ == '__main__':
    native() if os.environ.get('CLOUD_BUFFER_TIMING_NATIVE') == '1' else main()
