# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify all saved runtime members, restore only missing owned Magic files."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import tarfile

B = Path(__file__).resolve().parent
V = B.parent / 'pcie-vco-v6-local-v1-wire-20261005'
ARCHIVE = V / 'shutdown-private-runtime.tar.gz'
EXPECTED = {'bytes': 9118811, 'sha256': '5d561195d6adad2e4fe5ea29cba675a0bebbb382b52337a843b762825f4947f9'}
PREFIXES = {'nssoc-magic-area-product-v4-build', 'nssoc-magic-pad-stack-tech-v1'}


def pin(path):
    with Path(path).open('rb') as stream:
        return dict(bytes=Path(path).stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


assert pin(ARCHIVE) == EXPECTED
inventory = json.loads((V / 'shutdown-runtime-inventory.json').read_text())
members = {}
with tarfile.open(ARCHIVE, 'r:gz') as archive:
    for member in archive:
        name = PurePosixPath(member.name)
        assert member.isfile() and not name.is_absolute() and '..' not in name.parts
        assert member.name not in members
        with archive.extractfile(member) as stream:
            members[member.name] = dict(bytes=member.size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
assert members == inventory['members'] and len(members) == 403
restored, existing = {}, {}
with tarfile.open(ARCHIVE, 'r:gz') as archive:
    for member in archive:
        if PurePosixPath(member.name).parts[0] not in PREFIXES:
            continue
        target = Path('/dev/shm') / member.name
        assert not target.is_symlink()
        assert all(not p.is_symlink() for p in target.parents)
        if target.exists():
            assert pin(target) == members[member.name]
            existing[str(target)] = pin(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.extractfile(member) as source, target.open('xb') as output:
            while data := source.read(1024**2):
                output.write(data)
            output.flush()
            os.fsync(output.fileno())
        target.chmod(member.mode & 0o777)
        assert pin(target) == members[member.name]
        restored[str(target)] = pin(target)
assert len(existing) + len(restored) == 398
record = dict(status='PASS_PRIVATE_RUNTIME_ALL403_MEMBERS_OWNED398_MAGIC_FILES_EXACT',
              archive=EXPECTED, inventory=pin(V / 'shutdown-runtime-inventory.json'),
              method=pin(__file__), all_members=members, restored=restored,
              existing_unchanged=existing,
              shared_ngspice_OSDI_or_other_files_written=False,
              all_restored_full_readback=True, native_executed=False)
out = B / 'magic-runtime-restoration.json'
assert not out.exists()
out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(status=record['status'], restored=len(restored), existing=len(existing), receipt=pin(out))))
