"""Seal closed local-spool controls and launch evidence; exclude active native data."""
from pathlib import Path
import datetime
import hashlib
import io
import json
import os
import tarfile
import xml.etree.ElementTree as ET

R = Path.cwd()
B = R / 'hw/soc/out/pcie-pll-local-spool-v1-20261006'
D = B / 'finite01'
D.mkdir(exist_ok=False)


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def write(path, value):
    with path.open('xb') as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def check(entry):
    path = Path(entry['path'])
    assert pin(path) == {key: entry[key] for key in ('bytes', 'sha256')}, path
    return path


freeze = json.loads((B / 'source-freeze02.json').read_text())
peer = json.loads((B / 'source-saved-peer-root02.json').read_text())
assert peer['status'] == 'PASS_SOURCE_AND_SAVED_LOCAL_PLL_CAPTURE_AND_PUBLISHER'
assert peer['freeze'] == pin(B / 'source-freeze02.json') and not peer['findings']
support = json.loads((B / 'launch01/source-peer-vco01.json').read_text())
assert support['status'] == 'PASS_SOURCE_ONLY_DETACHED_LOCAL_PLL_V5_LAUNCH'
assert support['policy'] == pin(B / 'launch01/policy.json') and not support['findings']
files = {}
external = {}


def add(path):
    path = Path(path).absolute()
    assert path.is_file(), path
    if path.is_relative_to(R):
        name = 'repository/' + str(path.relative_to(R))
    elif path.is_relative_to('/dev/shm'):
        name = 'dev-shm/' + str(path.relative_to('/dev/shm'))
    else:
        raise AssertionError(('Unexpected capture root', path))
    assert name not in files or files[name]['path'] == str(path)
    files[name] = dict(path=str(path), **pin(path))


for item in (freeze['sources'] + list(freeze['dependencies'].values())
             + freeze['evidence'] + freeze['actual_fixture_files']):
    path = check(item)
    if path.name == 'python' and '/.venv/bin/' in str(path):
        external[str(path)] = pin(path)
    else:
        add(path)
excluded = []
for path in sorted(B.rglob('*')):
    if not path.is_file():
        continue
    rel = path.relative_to(B)
    if rel.parts[0] in ('publication01', 'finite01'):
        continue
    if rel.parts[0] == '__pycache__':
        continue
    if rel.parts[0] == 'launch01' and path.name in (
            'active-checkpoint.json', 'launch.log', 'supervisor.log',
            'publication.log', 'publication-supervisor.log'):
        excluded.append(str(path))
        continue
    if path.name == 'finite-seal01-controller.log':
        continue
    add(path)
assert all('/publication01/' not in value['path'] for value in files.values())
assert not any('pcie-pll-local-captures' in value['path'] for value in files.values())
assert not any('nssoc-pll-acquisition-v5-max125-local-01' in value['path']
               for value in files.values())

campaigns = []
for control in freeze['controls']:
    cases = ET.parse(control['xml']['path']).findall('.//testcase')
    failures = sum(case.find('failure') is not None or case.find('error') is not None
                   for case in cases)
    skipped = sum(case.find('skipped') is not None for case in cases)
    assert len(cases) == control['cases']
    assert failures == control['failed']
    assert len(cases) - failures - skipped == control['passed']
    campaigns.append(dict(name=control['name'], cases=len(cases), failed=failures,
                          passed=len(cases) - failures - skipped, skipped=skipped))
current = {}
for case in ET.parse(B / 'complete-controls03.xml').findall('.//testcase'):
    if 'test_pcie_pll_local_capture_v1' not in case.attrib['classname']:
        current[(case.attrib['classname'], case.attrib['name'])] = case
for case in ET.parse(B / 'bridge-controls05.xml').findall('.//testcase'):
    current[(case.attrib['classname'], case.attrib['name'])] = case
assert len(current) == 69
assert all(not list(case) for case in current.values())

manifest = dict(status='CLOSED_LOCAL_PLL_SPOOL_SOURCE_CONTROL_AND_LAUNCH_CAPTURE',
                utc=datetime.datetime.now(datetime.UTC).isoformat(),
                files=files, external_runtime_pins=external,
                excluded_active_paths=excluded,
                excluded_active_roots=[str(B / 'publication01'),
                    str(R / 'hw/soc/out/pcie-pll-local-captures/v5-max125-01'),
                    '/dev/shm/nssoc-pll-acquisition-v5-max125-local-01'],
                scope='Closed source, fixtures, historical failures, source peers and '
                      'immutable launch observations only. Native and independent publisher '
                      'remain active outside archive. Sparse cap-test files are captured '
                      'losslessly as all logical bytes; runtime Python is separately pinned.')
archive = D / 'pcie-pll-local-spool-v1-controls-and-launch-20261006.tar.xz'
write(D / 'members.json', manifest)
with tarfile.open(archive, 'w:xz', preset=1) as tar:
    for name, entry in sorted(files.items()):
        path = check(entry)
        info = tarfile.TarInfo(name)
        info.size = entry['bytes']
        info.mode = 0o644
        info.mtime = 0
        with path.open('rb') as stream:
            tar.addfile(info, stream)
        assert pin(path) == {key: entry[key] for key in ('bytes', 'sha256')}
    data = encoded(manifest)
    info = tarfile.TarInfo('members.json')
    info.size = len(data)
    info.mode = 0o644
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))
seen = set()
with tarfile.open(archive, 'r|xz') as tar:
    for member in tar:
        assert member.isfile() and member.name not in seen
        seen.add(member.name)
        stream = tar.extractfile(member)
        expected = pin(D / 'members.json') if member.name == 'members.json' else files[member.name]
        assert member.size == expected['bytes']
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected['sha256']
assert seen == set(files) | {'members.json'}
for entry in files.values():
    check(entry)
result = dict(status='PASS_FULL_MEMBER_LOCAL_PLL_SPOOL_FINITE_CAPTURE',
              archive=dict(path=str(archive), **pin(archive)),
              members=dict(path=str(D / 'members.json'), **pin(D / 'members.json')),
              member_count=len(seen), data_members=len(files),
              logical_data_bytes=sum(item['bytes'] for item in files.values()),
              campaigns=campaigns, current_predicates=69,
              current_test_counts=dict(core=30, capture=18, publisher=21),
              source_allowlist={str(Path(item['path']).relative_to(R)):
                  {key: item[key] for key in ('bytes', 'sha256')} for item in freeze['sources']},
              source_freeze=pin(B / 'source-freeze02.json'),
              aggregate_peer=pin(B / 'source-saved-peer-root02.json'),
              support_peer=pin(B / 'launch01/source-peer-vco01.json'),
              method=pin(__file__), findings=[],
              scope=manifest['scope'], native_completion=False,
              numerical_convergence=False, physical_acceptance=False)
write(D / 'pcie-pll-local-spool-v1-controls-and-launch-validation-20261006.json', result)
print(json.dumps(result, indent=2))
