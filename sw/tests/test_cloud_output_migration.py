"""Exercise deletion gates against a fake remote; never needs real GitHub."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/migrate_outputs_to_cloud.py'


def load(tmp_path):
    spec = importlib.util.spec_from_file_location('migration', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    module.BASE = tmp_path / 'hw/soc/out'
    module.STATE = module.BASE / 'cloud-migration-20261012'
    module.STATE.mkdir(parents=True)
    module.LIMIT = 64
    return module


def test_failed_manifest_keeps_original_and_resume_deletes_only_after_verified(tmp_path):
    m = load(tmp_path)
    source = m.BASE / 'unique.raw'
    source.write_bytes(b'raw captured evidence' * 11)
    remote = {}
    fail = [True]
    def publish(path, tag):
        if path.name.endswith('.manifest.json') and fail[0]:
            raise RuntimeError('offline before durable manifest')
        receipt = dict(name=path.name, bytes=path.stat().st_size,
                       sha256=m.digest(path), url='https://example.test/' + path.name)
        remote[path.name] = (path.read_bytes(), receipt)
        return receipt
    def release(tag):
        return dict(assets=[dict(name=k, size=r['bytes'], digest='sha256:' + r['sha256'])
                            for k, (_, r) in remote.items()])
    with patch.object(m, 'publish', publish), patch.object(m, 'release', release), \
            patch.object(m.subprocess, 'check_output', return_value='test-head'), \
            patch.object(sys, 'argv', ['migrate', '--apply']):
        with pytest.raises(RuntimeError, match='offline'):
            m.main()
        assert source.exists()
        fail[0] = False
        m.main()
        assert not source.exists()
    manifest = json.loads(remote['batch-000000.manifest.json'][0])
    restore = tmp_path / 'restore'
    restore.mkdir()
    for part in manifest['parts']:
        (restore / part['name']).write_bytes(remote[part['name']][0])
    record = dict(manifest['records'][0], parts=manifest['parts'])
    assert m.restore_manifest(record, restore).read_bytes() == b'raw captured evidence' * 11


def test_safe_excludes_symlinks_and_external_files(tmp_path):
    m = load(tmp_path)
    secret = tmp_path / 'outside'
    secret.write_text('outside project output')
    link = m.BASE / 'linked'
    link.symlink_to(secret)
    assert not m.safe(link)
    assert not m.safe(secret)
    state = m.STATE / 'journal'
    state.write_text('keep')
    assert not m.safe(state)


def test_changed_original_not_deleted_after_upload(tmp_path):
    m = load(tmp_path)
    source = m.BASE / 'case.log'
    source.write_text('original')
    def publish(path, tag):
        source.write_text('changed after archive creation')
        return dict(name=path.name, bytes=path.stat().st_size, sha256=m.digest(path))
    with patch.object(m, 'publish', publish), \
            patch.object(m.subprocess, 'check_output', return_value='test-head'), \
            patch.object(sys, 'argv', ['migrate', '--apply']):
        with pytest.raises(RuntimeError, match='Input changed'):
            m.main()
    assert source.read_text() == 'changed after archive creation'
