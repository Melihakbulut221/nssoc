# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal a closed, clean current regression with all native test artifacts."""
from pathlib import Path
import hashlib
import json
import tarfile
import xml.etree.ElementTree as ET

B = Path(__file__).absolute().parent
R = Path.cwd()
O = B / 'v23-final-controls01'
T = Path('/dev/shm/nssoc-integrity-v23-current-full-controls04')


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


row = json.loads((O / 'result.json').read_text())
assert row['status'] == 'PASS_CURRENT_V23_FULL_NON4118_REGRESSION'
assert row['returncode'] == 0 and row['passed'] == 36 and row['stop_reason'] is None
for who in ['owner', 'child']:
    identity = row[who]
    p = Path('/proc') / str(identity['pid']) / 'stat'
    if p.exists():
        s = p.read_text()
        fields = s[s.rfind(')') + 2:].split()
        assert fields[19] != str(identity['start_ticks']) or fields[0] == 'Z'
assert row['source_pins'] == {name: pin(R / name) for name in row['source_pins']}
for name, expected in row['outputs'].items():
    assert pin(name) == expected, name
cases = list(ET.parse(O / 'tests.xml').iter('testcase'))
assert len(cases) == 36 and all(not any(c.find(t) is not None for t in ['failure', 'error', 'skipped']) for c in cases)
paths = {}


def add(path, name):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and name not in paths
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    paths[name] = path


for p in T.rglob('*'):
    if p.is_file() and not p.is_symlink():
        add(p, 'tests/' + str(p.relative_to(T)))
for p in O.rglob('*'):
    if p.is_file() and not p.is_symlink():
        add(p, 'capture/' + str(p.relative_to(O)))
for name in row['source_pins']:
    add(R / name, 'sources/' + name)
for name in ['run_v23_final_controls01.py', 'seal_v23_final_controls01.py', 'v23-final-launch01.json', 'v23-final-controller01.log']:
    add(B / name, 'methods/' + name)
for name in ['Apache-2.0', 'CERN-OHL-W-2.0', 'CC-BY-4.0']:
    add(R / 'LICENSES' / (name + '.txt'), 'notices/' + name + '.txt')
members = {name: dict(restore_path=str(p), **pin(p)) for name, p in paths.items()}
archive = B / 'pcie-integrity-v23-current-full-controls04-20261006.tar.xz'
assert not archive.exists()
with tarfile.open(archive, 'w:xz', preset=3) as tar:
    for name, path in paths.items():
        tar.add(path, arcname=name, recursive=False)
seen = set()
with tarfile.open(archive, 'r:xz') as tar:
    for member in tar:
        assert member.isfile() and not member.issparse() and member.name not in seen and member.name in members
        with tar.extractfile(member) as stream:
            actual = dict(bytes=member.size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
        assert actual == {key: members[member.name][key] for key in actual}
        seen.add(member.name)
assert seen == set(members)
assert all(pin(path) == {key: members[name][key] for key in ('bytes', 'sha256')} for name, path in paths.items())
record = dict(status='PASS_CLOSED_CURRENT_V23_36_PREDICATES_ALL_NATIVE_ARTIFACTS',
              archive=dict(path=str(archive), **pin(archive)), members=members,
              result=pin(O / 'result.json'), sources=row['source_pins'],
              passed=36, failed=0, skipped=0, earlier_47_execution_history_preserved=True,
              scope='New full execution of the final V23 non4118 test sources plus real block-burst test. Earlier three campaigns remain immutable. This does not accept mapped timing, MAX4118 V23, full PHY or chip integration.',
              full_phy_acceptance=False, timing_accepted=False)
(B / 'pcie-integrity-v23-current-full-controls04-validation-20261006.json').write_text(json.dumps(record, indent=2) + '\n')
print(dict(status=record['status'], archive=record['archive'], members=len(members)))
