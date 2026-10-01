# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small controls for cloud archival; no original ZIP download or native work."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import archive_setup_probe_complete as archive


def identity():
    run=dict(id=archive.RUN,head_sha=archive.SOURCE,head_branch='codex/complete-open-work',
        path='.github/workflows/timing-setup-probe.yml',event='workflow_dispatch',status='completed',
        conclusion='failure',run_attempt=1,repository={'full_name':archive.REPO},head_repository={'full_name':archive.REPO})
    artifact=dict(id=archive.ARTIFACT,name='setup-probe-final-1',expired=False,size_in_bytes=archive.SIZE,
        digest='sha256:'+archive.DIGEST,workflow_run={k:run[k] for k in ('id','head_sha','head_branch')})
    return run,artifact


@pytest.mark.parametrize('fault',[None,'success','event','source','fork','attempt','artifact','digest','size','expired','artifact-source'])
def test_workflow_failure_and_exact_native_artifact_lineage_required(fault):
    run,artifact=identity()
    if fault=='success':run['conclusion']='success'
    if fault=='event':run['event']='push'
    if fault=='source':run['head_sha']='0'*40
    if fault=='fork':run['head_repository']['full_name']='other/repo'
    if fault=='attempt':run['run_attempt']=2
    if fault=='artifact':artifact['id']+=1
    if fault=='digest':artifact['digest']='sha256:'+'0'*64
    if fault=='size':artifact['size_in_bytes']+=1
    if fault=='expired':artifact['expired']=True
    if fault=='artifact-source':artifact['workflow_run']['head_sha']='0'*40
    if fault is None:archive.identity(run,artifact)
    else:
        with pytest.raises(ValueError):archive.identity(run,artifact)


def comparator_pair():
    original=subprocess.check_output(['git','show',archive.SOURCE+':'+archive.COMPARATOR],cwd=ROOT)
    return original,original.replace(archive.OLD_LINE,archive.NEW_LINES)


@pytest.mark.parametrize('fault',[None,'old-source','extra-edit','wrong-float','wrong-threshold','same-source'])
def test_overlay_is_exact_representation_only_source_delta(fault):
    original,fixed=comparator_pair()
    if fault=='old-source':original+=b'\n'
    if fault=='extra-edit':fixed+=b'\n'
    if fault=='wrong-float':fixed=fixed.replace(b'list(left)',b'[float(v) for v in left]')
    if fault=='wrong-threshold':fixed+=b'\nTOLERANCE = 1e-3\n'
    if fault=='same-source':fixed=original
    if fault is None:
        diff=archive.exact_overlay(original,fixed)
        assert 'before_seconds=list(left)' in diff and archive.SOURCE in diff
    else:
        with pytest.raises(ValueError):archive.exact_overlay(original,fixed)


def test_exact_structure_check_does_not_only_trust_hashes(monkeypatch):
    original,fixed=comparator_pair();fixed+=b'\nUNREVIEWED = True\n'
    monkeypatch.setattr(archive,'FIX_SHA',hashlib.sha256(fixed).hexdigest())
    with pytest.raises(ValueError,match='solely'):archive.exact_overlay(original,fixed)


def make_sources(tmp_path,monkeypatch):
    capture=tmp_path/'capture';capture.mkdir();review=tmp_path/'review';review.mkdir()
    old,fixed=comparator_pair()
    blobs={name:('pinned '+name).encode() for name in (*archive.METHODS,archive.MANIFEST,*archive.LICENSES)}
    blobs[archive.COMPARATOR]=old
    def git_blob(repo,commit,name):
        return fixed if commit==archive.FIX_SOURCE else blobs[name]
    monkeypatch.setattr(archive,'git_blob',git_blob)
    pins={name:archive.pin(blobs[name]) for name in archive.METHODS}
    for name in archive.METHODS:
        path=capture/'methods'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blobs[name])
    (capture/'result.json').write_text(json.dumps(dict(github_source_commit=archive.SOURCE,method_files=pins)))
    (capture/'source-manifest.json').write_bytes(blobs[archive.MANIFEST])
    return capture,review,pins,old,fixed


@pytest.mark.parametrize('fault',[None,'capture-method','source-claim','manifest','method-pin'])
def test_only_separate_overlay_changes_original_capture_and_sources_stay_intact(tmp_path,monkeypatch,fault):
    capture,review,pins,old,fixed=make_sources(tmp_path,monkeypatch)
    if fault=='capture-method':(capture/'methods'/archive.METHODS[0]).write_bytes(b'changed')
    if fault in ('source-claim','method-pin'):
        row=json.loads((capture/'result.json').read_text())
        if fault=='source-claim':row['github_source_commit']='0'*40
        else:row['method_files'][archive.METHODS[0]]['sha256']='0'*64
        (capture/'result.json').write_text(json.dumps(row))
    if fault=='manifest':(capture/'source-manifest.json').write_bytes(b'changed')
    if fault is not None:
        with pytest.raises(ValueError):archive.prepare_verifiers(ROOT,capture,review)
    else:
        original,overlay,receipt=archive.prepare_verifiers(ROOT,capture,review)
        assert (original/archive.COMPARATOR).read_bytes()==old
        assert (capture/'methods'/archive.COMPARATOR).read_bytes()==old
        assert (overlay/archive.COMPARATOR).read_bytes()==fixed
        differences=[name for name in receipt['original_sources'] if receipt['original_sources'][name]!=receipt['overlay_sources'][name]]
        assert differences==[archive.COMPARATOR]
        assert receipt['raw_capture_modified'] is False and receipt['thresholds_modified'] is False
        assert {k:receipt['original_sources'][k] for k in archive.METHODS}==pins


def test_verifier_invocation_is_python_validate_only_and_memory_bounded(tmp_path,monkeypatch):
    calls=[]
    def run(command,**kwargs):
        calls.append((command,kwargs));kwargs['stdout'].write(b'verified\n')
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(archive.subprocess,'run',run)
    assert archive.invoke_verifier(tmp_path/'overlay',tmp_path/'capture',tmp_path,'corrected-verifier')==0
    command,kwargs=calls[0]
    assert command[0:2]==[sys.executable,'-B'] and command[3]=='validate'
    assert kwargs['preexec_fn'] is archive.common.verifier_limits
    assert all('AppImage' not in value and '_native_flow' not in value for value in command)
    row=json.loads((tmp_path/'corrected-verifier.json').read_text())
    assert row['address_space_limit_bytes']==4*1024**3 and row['native_tools_reexecuted'] is False


@pytest.mark.parametrize('fault',['unexpected-success','unrelated-error','corrected-reject'])
def test_wrong_old_or_new_verifier_outcome_blocks_publication(tmp_path,monkeypatch,fault):
    def invoke(source,capture,review,label):
        (review/(label+'.log')).write_text('ValueError: unrelated' if fault=='unrelated-error' else 'ValueError: Independent diagnostic reconstruction differs')
        return 0 if fault=='unexpected-success' else 1
    monkeypatch.setattr(archive,'invoke_verifier',invoke)
    with pytest.raises(ValueError):archive.verify_complete(tmp_path,tmp_path,tmp_path,tmp_path,{'files':{}})


def test_low_disk_no_network_or_publication(tmp_path,monkeypatch):
    monkeypatch.setattr(archive.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=archive.SIZE))
    def forbidden(*a,**k):raise AssertionError('No network with insufficient disk')
    monkeypatch.setattr(archive.common,'api',forbidden)
    assert archive.run(tmp_path/'out',ROOT,True)==1
    row=json.loads((tmp_path/'out/review/result.json').read_text())
    assert row['status']=='FAILED_PRESERVED' and 'disk' in row['error']
    assert row['native_tools_reexecuted'] is False and row['timing_accepted'] is False


@pytest.mark.parametrize('fault',[None,'collision','authenticated','anonymous'])
def test_publish_requires_unchanged_bytes_and_both_roundtrips(tmp_path,monkeypatch,fault):
    raw=b'unchanged native ZIP';digest=hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(archive,'SIZE',len(raw));monkeypatch.setattr(archive,'DIGEST',digest)
    path=tmp_path/archive.NAME;path.write_bytes(raw)
    asset=dict(id=1,name=archive.NAME,size=len(raw),digest='sha256:'+digest,
        browser_download_url=f'https://github.com/{archive.REPO}/releases/download/{archive.TAG}/{archive.NAME}')
    if fault=='collision':asset['digest']='sha256:'+'0'*64
    monkeypatch.setattr(archive.common,'api',lambda _:dict(assets=[asset]))
    def forbidden(*a,**k):raise AssertionError('Never replace or delete an existing release asset')
    monkeypatch.setattr(archive.subprocess,'run',forbidden)
    monkeypatch.setattr(archive.common,'command_hash',lambda *a:(len(raw),'0'*64 if fault=='authenticated' else digest))
    monkeypatch.setattr(archive.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(b'changed' if fault=='anonymous' else raw))
    if fault is None:
        result=archive.publish(path,tmp_path)
        assert result['authenticated_roundtrip_verified'] and result['anonymous_roundtrip_verified']
    else:
        with pytest.raises(ValueError):archive.publish(path,tmp_path)
    assert path.read_bytes()==raw


def test_scoped_workflow_pins_and_complete_census():
    import yaml
    w=yaml.load((ROOT/'.github/workflows/timing-setup-probe-complete-archive.yml').read_text(),Loader=yaml.BaseLoader)
    assert w['permissions']=={'contents':'read','actions':'read'}
    job=w['jobs']['archive'];assert job['permissions']=={'contents':'write','actions':'read'}
    assert w['concurrency']['cancel-in-progress']=='false'
    commands='\n'.join(s.get('run','') for s in job['steps'])
    assert 'git fetch --no-tags --depth=1 origin '+archive.SOURCE in commands
    assert 'git fetch --no-tags --depth=1 origin '+archive.FIX_SOURCE in commands
    assert 'archive_setup_probe_complete.py --publish' in commands
    assert 'AppImage' not in commands and '_native_flow' not in commands
    uploads=[s for s in job['steps'] if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(uploads)==1 and uploads[0]['if']=='always()'
    assert uploads[0]['with']['include-hidden-files']=='true'
    assert archive.MEMBERS==125 and archive.EXPANDED==517394979
    assert archive.common.sha(Path(archive.common.__file__))==archive.COMMON_SHA
    assert len(archive.METHODS)==11


@pytest.mark.parametrize('fault',['bytes','extra-file','missing'])
def test_verification_cannot_modify_original_capture_or_membership(tmp_path,monkeypatch,fault):
    capture=tmp_path/'capture';capture.mkdir();original=capture/'native-evidence';original.write_bytes(b'original')
    inventory={'files':{'native-evidence':archive.pin(b'original')}}
    def invoke(source,captured,review,label):
        if label=='original-verifier':
            (review/(label+'.log')).write_text('ValueError: Independent diagnostic reconstruction differs')
            return 1
        if fault=='bytes':original.write_bytes(b'modified')
        if fault=='extra-file':(capture/'unexpected').write_bytes(b'new')
        if fault=='missing':original.unlink()
        return 0
    monkeypatch.setattr(archive,'invoke_verifier',invoke)
    with pytest.raises(ValueError):archive.verify_complete(tmp_path,tmp_path,capture,tmp_path,inventory)
