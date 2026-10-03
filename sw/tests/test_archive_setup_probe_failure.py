# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded failure preservation: no actual archive download or native execution."""
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import types
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import archive_setup_probe_failure as archive


def identity():
    run = dict(id=archive.RUN,head_sha=archive.SOURCE,head_branch='codex/complete-open-work',
        path='.github/workflows/timing-setup-probe.yml',event='push',status='completed',
        conclusion='failure',run_attempt=1,repository={'full_name':archive.REPO},
        head_repository={'full_name':archive.REPO})
    artifact = dict(id=archive.ARTIFACT,name='setup-probe-final-1',expired=False,
        size_in_bytes=archive.SIZE,digest='sha256:'+archive.DIGEST,
        workflow_run={key:run[key] for key in ('id','head_sha','head_branch')})
    return run,artifact


@pytest.mark.parametrize('fault',[None,'success','event','source','fork','attempt','artifact','digest','size','expired','artifact-source'])
def test_exact_failed_producer_identity(fault):
    run,artifact = identity()
    if fault == 'success': run['conclusion'] = 'success'
    if fault == 'event': run['event'] = 'workflow_dispatch'
    if fault == 'source': run['head_sha'] = '0'*40
    if fault == 'fork': run['head_repository']['full_name'] = 'other/repo'
    if fault == 'attempt': run['run_attempt'] = 2
    if fault == 'artifact': artifact['id'] += 1
    if fault == 'digest': artifact['digest'] = 'sha256:'+'0'*64
    if fault == 'size': artifact['size_in_bytes'] += 1
    if fault == 'expired': artifact['expired'] = True
    if fault == 'artifact-source': artifact['workflow_run']['head_sha'] = '0'*40
    if fault is None: archive.identity(run,artifact)
    else:
        with pytest.raises(ValueError): archive.identity(run,artifact)


def fixture(path,fault=None):
    flags = dict(candidate_adopted=False,timing_accepted=False,manufacturing_approval=False)
    result = dict(status='FAILED_PRESERVED',github_source_commit=archive.SOURCE,**flags)
    if fault == 'accepted': result['timing_accepted'] = True
    if fault == 'wrong-result-source': result['github_source_commit'] = '0'*40
    entries = {name:b'ordinary failure log\n' for name in archive.SELECTED}
    entries['result.json'] = json.dumps(result).encode()
    entries[archive.SELECTED[-1]] = b"dbJournal Assertion '!this->empty()' failed; rsz::Resizer::journalEnd()"
    if fault == 'wrong-error': entries[archive.SELECTED[-1]] = b'some unrelated error'
    if fault == 'oversized': entries['worker.log'] = b'x'*(archive.MAX_SELECTED+1)
    capture = dict(observation={'status':'FAILED_PRESERVED'},complete_diagnostic_evidence=False,
        restart_checkpoint_accepted=False,files={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
        source_truncated_during_copy=False,observed_source_bytes=len(data)) for name,data in entries.items()},**flags)
    if fault == 'hash': capture['files']['worker.log']['sha256'] = '0'*64
    if fault == 'truncated': capture['files']['worker.log']['source_truncated_during_copy'] = True
    if fault == 'complete': capture['complete_diagnostic_evidence'] = True
    if fault == 'checkpoint': capture['restart_checkpoint_accepted'] = True
    if fault == 'missing': del entries['worker.log']
    entries['capture.json'] = json.dumps(capture).encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as output:
        for name,data in entries.items(): output.writestr(name,data)
        if fault in ('traversal','symlink'):
            name = zipfile.ZipInfo('../escape' if fault == 'traversal' else 'link')
            if fault == 'symlink': name.create_system=3;name.external_attr=(stat.S_IFLNK|0o777)<<16
            output.writestr(name,b'outside')


@pytest.mark.parametrize('fault',[None,'accepted','wrong-result-source','wrong-error','oversized','hash','truncated','complete','checkpoint','missing','traversal','symlink'])
def test_bounded_selected_evidence_requires_failure_and_exact_capture_pins(tmp_path,fault):
    path = tmp_path/'input.zip';fixture(path,fault)
    if fault is not None:
        with pytest.raises(ValueError): archive.selected_failure(path,tmp_path/'selected')
    else:
        row = archive.selected_failure(path,tmp_path/'selected')
        assert row['zip_members'] == len(archive.SELECTED)+1
        assert row['full_native_output_validation'] is False and row['native_repair_succeeded'] is False
        assert set(row['selected_files']) == set(archive.SELECTED)
        with pytest.raises(FileExistsError): archive.selected_failure(path,tmp_path/'selected')
    assert not (tmp_path/'escape').exists()


def test_low_disk_preserves_failure_without_network(tmp_path,monkeypatch):
    monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=archive.SIZE))
    def forbidden(*args,**kwargs): raise AssertionError('Network forbidden by resource guard')
    monkeypatch.setattr(archive.common,'api',forbidden)
    assert archive.run(tmp_path/'out') == 1
    row = json.loads((tmp_path/'out/review/result.json').read_text())
    assert row['status'] == 'FAILED_PRESERVED' and 'disk' in row['error']
    assert row['native_reexecuted'] is False and row['timing_accepted'] is False


def test_conflicting_existing_asset_is_never_replaced(tmp_path,monkeypatch):
    path = tmp_path/archive.NAME;path.write_bytes(b'rawzip')
    monkeypatch.setattr(archive,'SIZE',6);monkeypatch.setattr(archive,'DIGEST',hashlib.sha256(b'rawzip').hexdigest())
    monkeypatch.setattr(archive.common,'api',lambda _:dict(assets=[dict(name=archive.NAME,size=7,digest='wrong',browser_download_url='wrong')]))
    def forbidden(*args,**kwargs): raise AssertionError('No release mutation')
    monkeypatch.setattr(archive.subprocess,'run',forbidden)
    with pytest.raises(ValueError,match='conflicting'): archive.publish(path,tmp_path)


def test_exact_existing_asset_requires_both_stream_roundtrips(tmp_path,monkeypatch):
    raw = b'rawzip';digest=hashlib.sha256(raw).hexdigest();path=tmp_path/archive.NAME;path.write_bytes(raw)
    monkeypatch.setattr(archive,'SIZE',len(raw));monkeypatch.setattr(archive,'DIGEST',digest)
    url=f'https://github.com/{archive.REPO}/releases/download/{archive.TAG}/{archive.NAME}'
    monkeypatch.setattr(archive.common,'api',lambda _:dict(assets=[dict(id=1,name=archive.NAME,size=len(raw),digest='sha256:'+digest,browser_download_url=url)]))
    monkeypatch.setattr(archive.common,'command_hash',lambda command,size:(len(raw),digest))
    monkeypatch.setattr(archive.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(raw))
    receipt=archive.publish(path,tmp_path)
    assert receipt['authenticated_roundtrip_verified'] and receipt['anonymous_roundtrip_verified']
    assert receipt['original_zip_unchanged']
    monkeypatch.setattr(archive.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(b'badzip'))
    with pytest.raises(ValueError,match='Anonymous'): archive.publish(path,tmp_path)


def test_pinned_shared_helper_and_scoped_workflow():
    assert archive.common.sha(Path(archive.common.__file__)) == archive.COMMON_SHA
    workflow=(ROOT/'.github/workflows/timing-setup-probe-failure-archive.yml').read_text()
    assert workflow.count('contents: write') == 1
    assert 'include-hidden-files: true' in workflow and 'if: always()' in workflow
    assert '--clobber' not in workflow and 'AppImage' not in workflow
    assert '      - .github/workflows/timing-setup-probe-failure-archive.yml' in workflow
    assert 'scripts/archive_setup_probe_failure.py --output' in workflow
