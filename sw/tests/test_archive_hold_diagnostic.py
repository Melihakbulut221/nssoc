# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded immutable cloud archival controls; never download the real large ZIP."""
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
import archive_hold_diagnostic as archive


def source_identity():
    run = dict(id=archive.RUN_ID,head_sha=archive.SOURCE,head_branch='codex/complete-open-work',
               path='.github/workflows/timing-hold-diagnostic.yml',event='workflow_dispatch',status='completed',
               conclusion='success',run_attempt=1,
               repository={'full_name':archive.REPO},head_repository={'full_name':archive.REPO})
    asset = dict(id=archive.ARTIFACT_ID,name=archive.ARTIFACT_NAME,size_in_bytes=archive.ARCHIVE_BYTES,
                 digest='sha256:'+archive.ARCHIVE_SHA256,expired=False,
                 workflow_run={key:run[key] for key in ('id','head_sha','head_branch')})
    return run,asset


@pytest.mark.parametrize('fault',[None,'run-id','commit','incomplete','failed','repository','fork','attempt','wrong-event','artifact','digest','size','expired','artifact-run'])
def test_source_metadata_requires_exact_successful_native_identity(fault):
    run,asset = source_identity()
    if fault == 'run-id': run['id'] += 1
    if fault == 'commit': run['head_sha'] = '0'*40
    if fault == 'incomplete': run['status'] = 'in_progress'
    if fault == 'failed': run['conclusion'] = 'failure'
    if fault == 'repository': run['repository']['full_name'] = 'other/repo'
    if fault == 'fork': run['head_repository']['full_name'] = 'other/repo'
    if fault == 'attempt': run['run_attempt'] = 2
    if fault == 'wrong-event': run['event'] = 'push'
    if fault == 'artifact': asset['id'] += 1
    if fault == 'digest': asset['digest'] = 'sha256:'+'0'*64
    if fault == 'size': asset['size_in_bytes'] += 1
    if fault == 'expired': asset['expired'] = True
    if fault == 'artifact-run': asset['workflow_run']['head_sha'] = '1'*40
    if fault is None: archive.verify_producer(run,asset)
    else:
        with pytest.raises(ValueError): archive.verify_producer(run,asset)


def tiny_zip(path,entries):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as output:
        for name,data in entries:
            if isinstance(name,zipfile.ZipInfo): output.writestr(name,data)
            else: output.writestr(name,data)


@pytest.mark.parametrize('fault',[None,'traversal','absolute','double-slash','backslash','drive','link','fifo','directory','duplicate','prefix'])
def test_safe_zip_rejects_unsafe_types_names_and_duplicate_members(tmp_path,monkeypatch,fault):
    monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=4*archive.GIB))
    path = tmp_path/'input.zip'
    name = {'traversal':'../escape','absolute':'/escape','double-slash':'a//b','backslash':'a\\b','drive':'C:/escape'}.get(fault,'methods/.github/workflows/probe.yml')
    if fault in ('link','fifo','directory'):
        item = zipfile.ZipInfo('unsafe/' if fault == 'directory' else 'unsafe')
        item.create_system = 3
        item.external_attr = ({'link':stat.S_IFLNK,'fifo':stat.S_IFIFO,'directory':stat.S_IFDIR}[fault] | 0o644) << 16
        name = item
    entries = [(name,b'original raw source')]
    if fault == 'duplicate': entries *= 2
    if fault == 'prefix': entries = [('a',b'file'),('a/b',b'collision')]
    with pytest.warns(UserWarning) if fault == 'duplicate' else __import__('contextlib').nullcontext():
        tiny_zip(path,entries)
    if fault is None:
        receipt = archive.extract(path,tmp_path/'extracted',expected_expanded=len(b'original raw source'),expected_members=1)
        assert receipt['member_count'] == 1
        assert (tmp_path/'extracted/methods/.github/workflows/probe.yml').read_bytes() == b'original raw source'
        assert receipt['files']['methods/.github/workflows/probe.yml']['sha256'] == hashlib.sha256(b'original raw source').hexdigest()
        with pytest.raises(FileExistsError): archive.extract(path,tmp_path/'extracted')
    else:
        with pytest.raises(ValueError): archive.extract(path,tmp_path/'extracted')
    assert not (tmp_path/'escape').exists()


@pytest.mark.parametrize('fault',['total','member','count','exact-total','exact-count','disk'])
def test_zip_expansion_budget_is_checked_before_creating_any_output(tmp_path,monkeypatch,fault):
    path = tmp_path/'input.zip'
    tiny_zip(path,[('one',b'12345678')])
    kwargs = {}
    if fault == 'total': monkeypatch.setattr(archive,'MAX_EXPANDED_BYTES',7)
    if fault == 'member': monkeypatch.setattr(archive,'MAX_MEMBER_BYTES',7)
    if fault == 'count': monkeypatch.setattr(archive,'MAX_MEMBERS',0)
    if fault == 'exact-total': kwargs['expected_expanded'] = 7
    if fault == 'exact-count': kwargs['expected_members'] = 2
    if fault == 'disk': monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=8))
    with pytest.raises(ValueError): archive.extract(path,tmp_path/'output',**kwargs)
    assert not (tmp_path/'output').exists()


def test_archive_crc_mismatch_preserves_failure_without_acceptance(tmp_path,monkeypatch):
    monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=4*archive.GIB))
    path = tmp_path/'input.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as output:
        output.writestr('file',b'unmodified evidence')
    raw = path.read_bytes().replace(b'unmodified evidence',b'corruption evidence')
    path.write_bytes(raw)
    with pytest.raises(zipfile.BadZipFile): archive.extract(path,tmp_path/'out')


def test_network_reader_never_exceeds_pinned_bytes():
    assert archive.stream_hash(io.BytesIO(b'abc'),3) == (3,hashlib.sha256(b'abc').hexdigest())
    with pytest.raises(ValueError): archive.stream_hash(io.BytesIO(b'abcd'),3)


def test_low_disk_never_downloads_or_publishes(tmp_path,monkeypatch):
    monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=456*1024**2))
    def forbidden(*args,**kwargs): raise AssertionError('No network action under failed resource guard')
    monkeypatch.setattr(archive,'api',forbidden)
    monkeypatch.setattr(archive,'publish',forbidden)
    assert archive.run(tmp_path/'out',ROOT,True) == 1
    row = json.loads((tmp_path/'out/review/result.json').read_text())
    assert row['status'] == 'FAILED_PRESERVED'
    assert row['native_tools_reexecuted'] is False and row['candidate_adopted'] is False
    assert row['timing_accepted'] is False and row['manufacturing_approval'] is False


def test_git_pins_bind_all_seven_captured_methods_before_verifier_execution(tmp_path,monkeypatch):
    capture,review = tmp_path/'capture',tmp_path/'review'
    capture.mkdir();review.mkdir()
    blobs = {name:('source '+name).encode() for name in (*archive.METHODS,archive.MANIFEST,*archive.LICENSES)}
    monkeypatch.setattr(archive,'git_blob',lambda repo,name:blobs[name])
    pins = {name:dict(bytes=len(blobs[name]),sha256=hashlib.sha256(blobs[name]).hexdigest()) for name in archive.METHODS}
    for name in archive.METHODS:
        target = capture/'methods'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blobs[name])
    (capture/'result.json').write_text(json.dumps(dict(github_source_commit=archive.SOURCE,method_files=pins)))
    (capture/'source-manifest.json').write_bytes(blobs[archive.MANIFEST])
    native,actual = archive.pin_native_methods(ROOT,capture,review)
    assert {key:actual[key] for key in archive.METHODS} == pins
    assert (native/'scripts/run_cloud_hold_diagnostic.py').read_bytes() == blobs['scripts/run_cloud_hold_diagnostic.py']
    (capture/'methods'/archive.METHODS[0]).write_bytes(b'tampered archive source')
    review2 = tmp_path/'review2';review2.mkdir()
    with pytest.raises(ValueError): archive.pin_native_methods(ROOT,capture,review2)


def test_git_blob_requests_exact_producer_commit_not_current_checkout(monkeypatch):
    calls = []
    def output(command):
        calls.append(command)
        return b'pinned producer source'
    monkeypatch.setattr(archive.subprocess,'check_output',output)
    assert archive.git_blob(ROOT,'scripts/run_cloud_hold_diagnostic.py') == b'pinned producer source'
    assert calls == [['git','-C',str(ROOT),'show',archive.SOURCE+':scripts/run_cloud_hold_diagnostic.py']]
    assert archive.EXPECTED_MEMBERS == 144 and archive.EXPECTED_EXPANDED_BYTES == 945676244


def test_release_collision_never_overwrites_or_deletes(tmp_path,monkeypatch):
    monkeypatch.setattr(archive,'ARCHIVE_BYTES',3)
    monkeypatch.setattr(archive,'ARCHIVE_SHA256',hashlib.sha256(b'abc').hexdigest())
    path = tmp_path/archive.ASSET_NAME;path.write_bytes(b'abc')
    monkeypatch.setattr(archive,'api',lambda _:dict(assets=[dict(name=archive.ASSET_NAME,size=4,digest='sha256:'+'0'*64)]))
    def forbidden(*args,**kwargs): raise AssertionError('Conflicting asset must never trigger mutation')
    monkeypatch.setattr(archive.subprocess,'run',forbidden)
    with pytest.raises(ValueError,match='different release bytes'): archive.publish(path,tmp_path)
    assert path.read_bytes() == b'abc'


def test_workflow_publishes_only_verified_pinned_run_with_scoped_permissions():
    import yaml
    workflow = yaml.load((ROOT/'.github/workflows/timing-hold-diagnostic-archive.yml').read_text(),Loader=yaml.BaseLoader)
    assert workflow['permissions'] == {'contents':'read','actions':'read'}
    job = workflow['jobs']['archive']
    assert job['permissions'] == {'contents':'write','actions':'read'}
    assert workflow['concurrency']['cancel-in-progress'] == 'false'
    commands = '\n'.join(step.get('run','') for step in job['steps'])
    assert 'git fetch --no-tags --depth=1 origin '+archive.SOURCE in commands
    assert 'archive_hold_diagnostic.py --publish' in commands
    assert 'AppImage' not in commands and 'openroad' not in commands
    uploads = [step for step in job['steps'] if step.get('uses','').startswith('actions/upload-artifact@')]
    assert len(uploads) == 1 and uploads[0]['if'] == 'always()'
    assert uploads[0]['with']['include-hidden-files'] == 'true'
    assert uploads[0]['with']['path'].endswith('/review/')


@pytest.mark.parametrize('existing',[False,True])
@pytest.mark.parametrize('fault',[None,'authenticated','anonymous'])
def test_publication_keeps_original_bytes_and_requires_both_roundtrips(tmp_path,monkeypatch,existing,fault):
    data = b'original ZIP bytes'
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(archive,'ARCHIVE_BYTES',len(data))
    monkeypatch.setattr(archive,'ARCHIVE_SHA256',digest)
    path = tmp_path/archive.ASSET_NAME;path.write_bytes(data)
    asset = dict(id=123,name=archive.ASSET_NAME,size=len(data),digest='sha256:'+digest,
                 browser_download_url=f'https://github.com/{archive.REPO}/releases/download/{archive.TAG}/{archive.ASSET_NAME}')
    state = {'published':existing}
    release = dict(assets=[],html_url='https://github.com/'+archive.REPO+'/releases/tag/'+archive.TAG)
    monkeypatch.setattr(archive,'api',lambda _:dict(release,assets=[asset] if state['published'] else []))
    commands = []
    def publish(command,**kwargs):
        commands.append(command)
        assert '--clobber' not in command and 'delete' not in command
        state['published'] = True
    monkeypatch.setattr(archive.subprocess,'run',publish)
    monkeypatch.setattr(archive,'command_hash',lambda *_:(len(data),'0'*64 if fault == 'authenticated' else digest))
    monkeypatch.setattr(archive.urllib.request,'urlopen',lambda *_a,**_k:io.BytesIO(b'wrong' if fault == 'anonymous' else data))
    if fault is None:
        receipt = archive.publish(path,tmp_path)
        assert receipt['original_zip_unchanged'] is True
        assert receipt['reused_existing_matching_asset'] is existing
        assert receipt['authenticated_roundtrip_verified'] is True and receipt['anonymous_roundtrip_verified'] is True
    else:
        with pytest.raises(ValueError): archive.publish(path,tmp_path)
    assert path.read_bytes() == data
    assert len(commands) == (0 if existing else 1)


def test_changed_download_never_reaches_publication(tmp_path,monkeypatch):
    monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=4*archive.GIB))
    run,artifact = source_identity()
    monkeypatch.setattr(archive,'api',lambda path:run if path.startswith('actions/runs/') else artifact)
    monkeypatch.setattr(archive,'download_archive',lambda path:path.write_bytes(b'corrupt untrusted bytes'))
    def forbidden(*args,**kwargs): raise AssertionError('Unverified bytes must never publish')
    monkeypatch.setattr(archive,'publish',forbidden)
    assert archive.run(tmp_path/'output',ROOT,True) == 1
    row = json.loads((tmp_path/'output/review/result.json').read_text())
    assert row['status'] == 'FAILED_PRESERVED' and 'pinned file' in row['error']
    assert row['timing_accepted'] is False and row['native_tools_reexecuted'] is False


@pytest.mark.parametrize('returncode',[0,2])
def test_verifier_invokes_only_pinned_source_without_native_runtime(tmp_path,monkeypatch,returncode):
    native,capture,review = tmp_path/'native-source',tmp_path/'capture',tmp_path/'review'
    capture.mkdir();review.mkdir()
    row = dict(status='COMPLETE_DIAGNOSTIC_ONLY',candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
               selected_source_metrics={'setup_wns_ns':-4.710829,'hold_wns_ns':-1.840329},
               sdc_sha256='0'*64,native_runs={},
               diagnostic={'native':{'stages':[{'name':name} for name in archive.STAGES]},'independently_checked_stages':{}})
    (capture/'result.json').write_text(json.dumps(row))
    (capture/'capture.json').write_text('{}')
    calls = []
    def run(command,**kwargs):
        calls.append((command,kwargs))
        return types.SimpleNamespace(returncode=returncode)
    monkeypatch.setattr(archive.subprocess,'run',run)
    if returncode:
        with pytest.raises(ValueError,match='verifier rejected'): archive.verify_capture(native,capture,review)
        assert not (review/'summary.json').exists()
    else:
        summary = archive.verify_capture(native,capture,review)
        assert summary['status'] == 'VERIFIED_COMPLETE_DIAGNOSTIC_ONLY'
        assert summary['timing_accepted'] is False and summary['candidate_adopted'] is False
    assert calls[0][0] == [sys.executable,'-B',str(native/'scripts/run_cloud_hold_diagnostic.py'),'validate',
                          '--directory',str(capture),'--manifest',str(native/archive.MANIFEST)]
    assert calls[0][1]['preexec_fn'] is archive.verifier_limits
    assert (review/'verifier.json').exists() and (review/'verifier.log').exists()
