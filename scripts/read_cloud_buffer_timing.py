#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read the preserved exact-buffer placement timing report on a hosted runner."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

from read_opensta_phase_slacks import parse_phases

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-buffer-timing'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

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
        names = ('relocated-placement-sta.log', 'relocated-placement-sta.tcl')
        wanted = {'cloud-newer-postcts/' + name: name for name in names}
        found = set()
        with tarfile.open(packed, 'r|gz') as archive:
            for member in archive:
                if member.name in wanted:
                    assert member.name not in found and member.isfile() and member.size < 20_000_000
                    name = wanted[member.name]
                    (OUT / name).write_bytes(archive.extractfile(member).read())
                    assert sha(OUT / name) == evidence['failure_outputs'][name]
                    found.add(member.name)
        assert found == set(wanted)
        packed.unlink()
        phases = parse_phases((OUT / 'relocated-placement-sta.log').read_text(), 'CORNER')
        assert set(phases) == {corner + '_' + kind for corner in ('slow', 'typical', 'fast') for kind in ('min', 'max')}
        result.update(status='COMPLETE_EXACT_PLACEMENT_TIMING_REPORT_READBACK',
                      placement_odb_sha256=evidence['failure_outputs']['relocated-placement.odb'],
                      phases=phases, restored={name:sha(OUT / name) for name in names})
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

if __name__ == '__main__':
    main()
