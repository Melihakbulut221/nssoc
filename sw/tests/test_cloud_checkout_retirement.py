# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls: checkout deletion requires every transfer and cloud handoff."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('retirement', SCRIPTS / 'retire_local_checkout.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def put(root, relative, **value):
    p = root / 'hw/soc/out' / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))


@pytest.fixture
def ready_root(tmp_path):
    for family in ('20261012', 'pnr-20261013', 'tools-20261013'):
        put(tmp_path, 'cloud-migration-' + family + '/transfer-progress.json', status='COMPLETE_SELECTED_REGULAR_OUTPUT_FILES')
    put(tmp_path, 'cloud-migration-transients-20261013/progress.json', status='COMPLETE_REMOTE_READBACK_AND_LOCAL_CLEANUP')
    put(tmp_path, 'cloud-migration-finalization-20261013/state.json', status='FINAL_HOSTED_RECONSTRUCTION_RUNNING', run_id=123)
    return tmp_path


@pytest.mark.parametrize('family', ['20261012', 'pnr-20261013', 'tools-20261013'])
def test_every_output_family_required(ready_root, family):
    assert m.ready(ready_root)['run_id'] == 123
    put(ready_root, 'cloud-migration-' + family + '/transfer-progress.json', status='RUNNING')
    with pytest.raises(RuntimeError, match='not complete'):
        m.ready(ready_root)


def test_transient_readback_and_real_cloud_run_required(ready_root):
    put(ready_root, 'cloud-migration-finalization-20261013/state.json', status='WAITING_ALL_TRANSFERS')
    with pytest.raises(RuntimeError, match='not dispatched'):
        m.ready(ready_root)
    put(ready_root, 'cloud-migration-finalization-20261013/state.json', status='FINAL_HOSTED_RECONSTRUCTION_RUNNING', run_id=123)
    put(ready_root, 'cloud-migration-transients-20261013/progress.json', status='RUNNING')
    with pytest.raises(RuntimeError, match='not complete'):
        m.ready(ready_root)


def test_scope_rejects_neighbor_and_symlink_ancestor(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    root.mkdir()
    neighbor = tmp_path / 'personal'
    neighbor.mkdir()
    (neighbor / 'unique').write_text('preserve')
    (root / 'link').symlink_to(neighbor, target_is_directory=True)
    monkeypatch.setattr(m, 'ROOT', root)
    assert m.allowed(root / 'source.v')
    assert m.allowed(root / 'link')
    assert not m.allowed(root / 'link' / 'unique')
    assert not m.allowed(neighbor / 'unique')
    assert not m.allowed(root / '..' / 'personal' / 'unique')


@pytest.mark.parametrize('change', [{'status': 'FAIL'}, {'manifest_sha256': 'different'}, {'manifest_url': 'https://wrong'}])
def test_hosted_success_must_bind_exact_manifest(change):
    import cloud_archive_readback as readback
    manifest = dict(sha256='exact-manifest-hash', url='https://exact')
    proof = dict(status='PASS_EVERY_REMOTE_ARCHIVE_MEMBER', manifest_sha256=manifest['sha256'], manifest_url=manifest['url'])
    readback.check_result(proof, manifest)
    proof.update(change)
    with pytest.raises(ValueError, match='exact manifest'):
        readback.check_result(proof, manifest)
