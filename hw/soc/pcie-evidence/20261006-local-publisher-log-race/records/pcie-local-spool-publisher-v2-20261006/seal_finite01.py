"""Seal finite worker controls; exclude the active publisher and native spool."""
from pathlib import Path
import hashlib
import io
import json
import os
import tarfile

R = Path.cwd()
B = Path(__file__).resolve().parent
F = B / 'finite01'
F.mkdir()
def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())

freeze = json.loads((B / 'source-freeze01.json').read_text())
for path, expected in freeze['pins'].items():
    assert pin(path) == expected, path
peer = json.loads((B / 'source-saved-peer-vco01.json').read_text())
assert peer['status'] == 'PASS_SOURCE_SAVED_PUBLISHER_V2_AND_LAUNCH' and not peer['findings']
assert peer['freeze'] == pin(B / 'source-freeze01.json') and peer['policy'] == pin(B / 'launch01/policy.json')
assert peer['actual_current_predicates'] == 31 and peer['historical_failed'] == 5
paths = set()
for path in freeze['pins']:
    p = Path(path)
    if p.is_relative_to(B) or (p.is_relative_to(R / 'scripts') and p.suffix == '.py') or (p.is_relative_to(R / 'sw/tests') and p.suffix == '.py'):
        paths.add(p)
# Only finite reviewer files and immutable startup receipts are added. In
# particular publication01/, native captures and launch publication.log stay out.
for p in B.iterdir():
    if p.is_file() and p.suffix in ('.py', '.json', '.log', '.xml'):
        paths.add(p)
for name in ('policy.json', 'launch-once.json', 'detached-receipt.json', 'root-launch01.log'):
    paths.add(B / 'launch01' / name)
for name in ('Apache-2.0', 'CC-BY-4.0'):
    paths.add(R / 'LICENSES' / (name + '.txt'))
paths = sorted(paths)
assert all(not p.is_symlink() and p.is_file() for p in paths)
assert not any(p.is_relative_to(B / 'publication01') for p in paths)
files = {str(p.relative_to(R)): dict(path=str(p), **pin(p)) for p in paths}
links = {}
for name in ('fixtures01', 'fixtures02', 'fixtures03'):
    for p in (B / name).rglob('*'):
        if p.is_symlink():
            links[str(p.relative_to(R))] = os.readlink(p)
manifest = dict(status='FINITE_WORKER_V2_CONTROLS_SOURCES_AND_STARTUP', files=files,
                fixture_symlinks_as_metadata_only=links, active_journals_excluded=True,
                current_predicates=31, historical_executions=93, historical_passed=88,
                historical_failed=5, full_phy_acceptance=False, native_completion=False)
encoded = (json.dumps(manifest, indent=2) + '\n').encode()
(F / 'members.json').write_bytes(encoded)
archive = F / 'pcie-local-spool-publisher-v2-controls-20261006.tar.xz'
with tarfile.open(archive, 'x:xz', preset=1) as tar:
    for name, row in files.items():
        p = Path(row['path'])
        with p.open('rb') as stream:
            info = tarfile.TarInfo(name)
            info.size = row['bytes']
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, stream)
        assert pin(p) == {k: row[k] for k in ('bytes', 'sha256')}
    info = tarfile.TarInfo('members.json')
    info.size = len(encoded)
    tar.addfile(info, io.BytesIO(encoded))
seen = set()
with tarfile.open(archive, 'r|xz') as tar:
    for member in tar:
        assert member.isfile() and member.name not in seen
        expected = (pin(F / 'members.json') if member.name == 'members.json'
                    else {k: files[member.name][k] for k in ('bytes', 'sha256')})
        actual = dict(bytes=member.size, sha256=hashlib.file_digest(tar.extractfile(member), 'sha256').hexdigest())
        assert actual == expected
        seen.add(member.name)
assert seen == set(files) | {'members.json'}
for row in files.values():
    assert pin(row['path']) == {k: row[k] for k in ('bytes', 'sha256')}
result = dict(status='PASS_FINITE_PUBLISHER_V2_ARCHIVE_FULL_READBACK', archive=dict(path=str(archive), **pin(archive)),
              manifest=dict(path=str(F / 'members.json'), **pin(F / 'members.json')), members=len(seen),
              full_logical_bytes=sum(row['bytes'] for row in files.values()) + len(encoded),
              source=pin(__file__), freeze=pin(B / 'source-freeze01.json'), peer=pin(B / 'source-saved-peer-vco01.json'),
              sources=freeze['sources'], active_journals_excluded=True, current_predicates=31,
              full_phy_acceptance=False, native_completion=False)
(F / 'pcie-local-spool-publisher-v2-controls-validation-20261006.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
