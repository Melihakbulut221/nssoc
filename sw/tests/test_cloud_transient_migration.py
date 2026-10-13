# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted deletion and remote-readback fault controls for temporary migration."""
import importlib.util
from pathlib import Path
import sys
import tarfile

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('transient_migration', SCRIPTS / 'migrate_cloud_transients.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.fixture
def scope(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'BASES', (tmp_path,))
    root = tmp_path / 'nssoc-case'
    root.mkdir()
    return root


def test_changed_original_survives(scope):
    p = scope / 'result'
    p.write_bytes(b'unique native output')
    row = m.record(p)
    p.write_bytes(b'new result after snapshot')
    with pytest.raises(ValueError, match='changed'):
        m.remove_original(row)
    assert p.read_bytes() == b'new result after snapshot'


def test_link_target_never_removed_and_missing_resume_safe(scope):
    target = scope.parent / 'personal'
    target.write_text('keep')
    link = scope / 'link'
    link.symlink_to(target)
    row = m.record(link)
    assert m.remove_original(row)
    assert not m.remove_original(row)
    assert target.read_text() == 'keep'


def test_ancestor_link_and_other_project_rejected(scope):
    outside = scope.parent / 'other'
    outside.mkdir()
    p = outside / 'secret'
    p.write_text('keep')
    (scope / 'alias').symlink_to(outside, target_is_directory=True)
    assert not m.allowed(scope / 'alias' / 'secret')
    assert not m.allowed(p)
    with pytest.raises(ValueError, match='scope'):
        m.record(p)


def test_roundtrip_bytes_and_external_link_metadata(scope):
    p = scope / 'result'
    p.write_bytes(b'waveform bytes')
    link = scope / 'link'
    link.symlink_to('/unavailable/external/target')
    rows = [m.record(p), m.record(link)]
    archive = scope.parent / 'archive.tar.gz'
    with tarfile.open(archive, 'w:gz', dereference=False) as packed:
        for row in rows:
            packed.add(row['path'], arcname=row['member'], recursive=False)
    m.verify_archive(archive, rows)
    rows[0]['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='bytes differ'):
        m.verify_archive(archive, rows)


def test_duplicate_and_missing_archive_members_rejected(scope):
    p = scope / 'result'
    p.write_text('keep')
    row = m.record(p)
    archive = scope.parent / 'archive.tar.gz'
    with tarfile.open(archive, 'w:gz') as packed:
        packed.add(p, arcname=row['member'])
        packed.add(p, arcname=row['member'])
    with pytest.raises(ValueError, match='duplicate'):
        m.verify_archive(archive, [row])
    with tarfile.open(archive, 'w:gz'):
        pass
    with pytest.raises(ValueError, match='missing'):
        m.verify_archive(archive, [row])


def test_independent_batches_keep_failed_original_and_resume(scope, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import json
    import cloud_archive_readback as hosted
    state = scope.parent / 'transfer-state'
    state.mkdir()
    monkeypatch.setattr(m, 'STATE', state)
    paths = [scope / str(i) for i in range(3)]
    for p in paths:
        p.write_text('unique payload ' + p.name)
    rows = [m.record(p) for p in paths]
    remote = {}
    def publish(path, tag):
        remote[path.name] = path.read_bytes()
        return dict(name=path.name, bytes=path.stat().st_size, sha256=m.digest(path), url='https://example/' + path.name)
    monkeypatch.setattr(m, 'publish', publish)
    fail = [True]
    def proof(receipt, tag, destination):
        manifest = json.loads((state / receipt['name']).read_text())
        assert receipt['sha256'] == m.digest(state / receipt['name'])
        download = state / (manifest['receipt']['name'] + '.remote')
        download.write_bytes(remote[manifest['receipt']['name']])
        m.verify_archive(download, manifest['entries'])
        download.unlink()
        if manifest['entries'][0]['path'] == str(paths[1]) and fail[0]:
            raise ValueError('hosted proof failed')
        return dict(status='PASS')
    monkeypatch.setattr(hosted, 'wait_verified_readback', proof)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(m.transfer_batch, i, [r]) for i, r in enumerate(rows)]
        assert futures[0].result()['entries'] == 1
        with pytest.raises(ValueError, match='hosted proof failed'):
            futures[1].result()
        assert futures[2].result()['entries'] == 1
    assert [p.exists() for p in paths] == [False, True, False]
    fail[0] = False
    # Simulate ordered progress lost after another worker already finished.
    m.transfer_batch(1, [rows[1]])
    m.transfer_batch(2, [rows[2]])
    assert not any(p.exists() for p in paths)
