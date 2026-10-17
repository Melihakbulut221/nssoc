# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small pure source/ZIP/receipt controls; no Git history, network or native tools."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_targeted_hold_archive as verify


def pin(data):return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def fixture(tmp_path,monkeypatch):
    capture=tmp_path/'capture';capture.mkdir();review=tmp_path/'review';review.mkdir()
    sources={name:('synthetic '+name+'\n').encode() for name in (*verify.METHODS,verify.MANIFEST,*verify.common.LICENSES)}
    for name in verify.METHODS:
        p=capture/'methods'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(sources[name])
    (capture/'source-manifest.json').write_bytes(sources[verify.MANIFEST])
    flags=dict(candidate_adopted=False,timing_accepted=False,manufacturing_approval=False)
    row=dict(flags,status='COMPLETE_DIAGNOSTIC_ONLY',github_source_commit=verify.SOURCE,
        manifest_sha256=pin(sources[verify.MANIFEST])['sha256'],
        method_files={name:pin(sources[name]) for name in verify.METHODS},
        native_runs={name:dict(returncode=0) for name in ('native-controls','native-diagnostic')},
        diagnostic=dict(flags,native=dict(flags,stages=[dict(name=name) for name in verify.STAGES],
            timing_metrics={},buffer_budget={},repair_invocation={}),
            aggregate_guard_assessment=dict(aggregate_estimate_guard_passed=False),
            independently_checked_stages={},full_endpoint_comparisons={}))
    (capture/'result.json').write_text(json.dumps(row));(capture/'capture.json').write_text('{}')
    monkeypatch.setattr(verify,'source_blob',lambda name:sources[name])
    return capture,review,row,sources


def inventory(capture):
    files={str(p.relative_to(capture)):pin(p.read_bytes()) for p in capture.rglob('*') if p.is_file()}
    return dict(member_count=len(files),expanded_bytes=sum(p['bytes'] for p in files.values()),files=files)


@pytest.mark.parametrize('fault',[None,'commit','extra-method','captured-method','method-pin','manifest-pin','manifest-bytes'])
def test_immutable_source_boundary_without_checkout_history(tmp_path,monkeypatch,fault):
    capture,review,row,sources=fixture(tmp_path,monkeypatch)
    if fault=='commit':row['github_source_commit']='0'*40
    if fault=='extra-method':row['method_files']['unexpected.py']=pin(b'new')
    if fault=='captured-method':(capture/'methods'/verify.METHODS[0]).write_bytes(b'wrong bytes')
    if fault=='method-pin':row['method_files'][verify.METHODS[0]]['sha256']='0'*64
    if fault=='manifest-pin':row['manifest_sha256']='0'*64
    if fault=='manifest-bytes':(capture/'source-manifest.json').write_bytes(b'changed manifest')
    (capture/'result.json').write_text(json.dumps(row))
    if fault is not None:
        with pytest.raises(ValueError):verify.pin_sources(capture,review)
    else:
        source,pins=verify.pin_sources(capture,review)
        assert set(pins)==set(sources)
        for name,data in sources.items():assert (source/name).read_bytes()==data


@pytest.mark.parametrize('fault',[None,'verifier-failure','capture-edit','capture-extra','source-edit',
    'source-extra','symlink','acceptance','incomplete','missing-stage','native-failure'])
def test_replay_only_invokes_exact_python_and_preserves_original_bytes(tmp_path,monkeypatch,fault):
    capture,review,row,_=fixture(tmp_path,monkeypatch)
    if fault=='acceptance':row['diagnostic']['native']['candidate_adopted']=True
    if fault=='incomplete':row['status']='RUNNING'
    if fault=='missing-stage':row['diagnostic']['native']['stages'].pop()
    if fault=='native-failure':row['native_runs']['native-diagnostic']['returncode']=1
    (capture/'result.json').write_text(json.dumps(row))
    source,pins=verify.pin_sources(capture,review);inv=inventory(capture);commands=[]
    def pure_process(command,**kwargs):
        commands.append(command)
        assert command[:4]==[sys.executable,'-B',str(source/'scripts/run_cloud_targeted_hold.py'),'validate']
        assert kwargs['preexec_fn'] is verify.common.verifier_limits and kwargs['timeout']==300
        if fault=='capture-edit':(capture/'capture.json').write_text('changed')
        if fault=='capture-extra':(capture/'extra').write_text('new')
        if fault=='source-edit':
            p=source/verify.METHODS[0];p.chmod(0o644);p.write_text('changed')
        if fault=='source-extra':(source/'extra.py').write_text('new')
        if fault=='symlink':(capture/'link').symlink_to('result.json')
        return SimpleNamespace(returncode=1 if fault=='verifier-failure' else 0)
    monkeypatch.setattr(verify.subprocess,'run',pure_process)
    if fault is None:
        result=verify.replay(source,capture,review,inv,pins)
        assert result['full_stage_physical_and_corner_path_replay'] and result['candidate_adopted'] is False
        assert result['aggregate_guard_assessment']['aggregate_estimate_guard_passed'] is False
    else:
        with pytest.raises(ValueError):verify.replay(source,capture,review,inv,pins)
    assert len(commands)==1


@pytest.mark.parametrize('fault',[None,'zip-digest','member-census','unsafe-member'])
def test_small_zip_exact_bytes_safe_extraction_and_success_only_cleanup(tmp_path,monkeypatch,fault):
    capture,_,_,_=fixture(tmp_path,monkeypatch);archive=tmp_path/'original.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in capture.rglob('*'):
            if p.is_file():z.write(p,str(p.relative_to(capture)))
        if fault=='unsafe-member':z.writestr('../escape',b'unsafe')
    with zipfile.ZipFile(archive) as z:
        members=z.infolist();expanded=sum(m.file_size for m in members)
    monkeypatch.setattr(verify,'SIZE',archive.stat().st_size)
    monkeypatch.setattr(verify,'DIGEST','0'*64 if fault=='zip-digest' else verify.common.sha(archive))
    monkeypatch.setattr(verify,'MEMBERS',len(members)+(1 if fault=='member-census' else 0))
    monkeypatch.setattr(verify,'EXPANDED',expanded)
    monkeypatch.setattr(verify.common,'DISK_RESERVE',0)
    monkeypatch.setattr(verify.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=0))
    output=tmp_path/'final';before=archive.read_bytes()
    if fault is None:
        assert verify.main(['--archive',str(archive),'--output',str(output)])==0
        assert not (output/'capture').exists() and (output/'producer-source').is_dir()
        assert json.loads((output/'result.json').read_text())['capture_removed_after_success'] is True
    else:
        with pytest.raises(ValueError):verify.main(['--archive',str(archive),'--output',str(output)])
        assert not (tmp_path/'escape').exists()
    assert archive.read_bytes()==before
