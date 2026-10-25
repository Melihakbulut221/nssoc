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
import archive_targeted_hold_failure as archive


def identity():
    run = dict(id=archive.RUN,head_sha=archive.SOURCE,head_branch='codex/complete-open-work',
        path='.github/workflows/timing-targeted-hold.yml',event='push',status='completed',
        conclusion='failure',run_attempt=1,repository={'full_name':archive.REPO},
        head_repository={'full_name':archive.REPO})
    artifact = dict(id=archive.ARTIFACT,name='targeted-hold-final-1',expired=False,
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


def fixture(path,monkeypatch,fault=None):
    flags=dict(candidate_adopted=False,timing_accepted=False,manufacturing_approval=False)
    entries={name:b'small selected evidence\n' for name in (*archive.SELECTED,*('methods/'+n for n in archive.METHODS))}
    entries['unselected-large.bin']=b'opaque geometry bytes'
    capture=dict(observation={'status':'FAILED_PRESERVED'},complete_diagnostic_evidence=False,
        restart_checkpoint_accepted=False,files={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
        source_truncated_during_copy=False,observed_source_bytes=len(data)) for name,data in entries.items()},**flags)
    if fault=='hash':capture['files']['unselected-large.bin']['sha256']='0'*64
    if fault=='truncated':capture['files']['unselected-large.bin']['source_truncated_during_copy']=True
    if fault=='accepted':capture['timing_accepted']=True
    if fault=='complete':capture['complete_diagnostic_evidence']=True
    if fault=='checkpoint':capture['restart_checkpoint_accepted']=True
    if fault=='missing':del entries['worker.log']
    entries['capture.json']=json.dumps(capture).encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in entries.items():z.writestr(name,data)
        if fault in ('traversal','symlink'):
            name=zipfile.ZipInfo('../escape' if fault=='traversal' else 'link')
            if fault=='symlink':name.create_system=3;name.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(name,b'outside')
    monkeypatch.setattr(archive,'EXPECTED_MEMBERS',len(entries))
    monkeypatch.setattr(archive,'EXPECTED_EXPANDED',sum(map(len,entries.values())))
    monkeypatch.setattr(archive,'inspect_failure',lambda output,members:dict(native_repair_started=False))
    if fault=='census':monkeypatch.setattr(archive,'EXPECTED_MEMBERS',len(entries)+1)


@pytest.mark.parametrize('fault',[None,'accepted','hash','truncated','complete','checkpoint','missing','traversal','symlink','census'])
def test_every_member_capture_pin_is_checked_even_when_not_selected(tmp_path,monkeypatch,fault):
    path=tmp_path/'input.zip';fixture(path,monkeypatch,fault)
    if fault:
        with pytest.raises(ValueError):archive.selected_failure(path,tmp_path/'selected')
    else:
        row=archive.selected_failure(path,tmp_path/'selected')
        assert row['all_member_capture_pins_verified'] and row['all_member_crc_verified']
        assert row['native_repair_started'] is False
        assert 'unselected-large.bin' in row['member_inventory']
        assert not (tmp_path/'selected/unselected-large.bin').exists()
        with pytest.raises(FileExistsError):archive.selected_failure(path,tmp_path/'selected')
    assert not(tmp_path/'escape').exists()


def test_source_boundary_uses_exact_commit_and_no_checkout_history(tmp_path,monkeypatch):
    raw={name:('exact source: '+name).encode() for name in (*archive.METHODS,archive.MANIFEST)}
    record=dict(method_files={name:dict(bytes=len(raw[name]),sha256=hashlib.sha256(raw[name]).hexdigest())for name in archive.METHODS})
    for name,data in raw.items():
        p=tmp_path/('methods/'+name if name in archive.METHODS else 'source-manifest.json')
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    seen=[]
    def boundary(name):seen.append(name);return raw[name]
    monkeypatch.setattr(archive,'source_blob',boundary)
    pins=archive.source_pins(tmp_path,record)
    assert set(pins)==set(seen)==set(raw)
    (tmp_path/'methods'/archive.METHODS[0]).write_bytes(b'changed')
    with pytest.raises(ValueError,match='pinned file'):archive.source_pins(tmp_path,record)


def test_source_fetch_pins_commit_via_api_not_git_history(monkeypatch):
    calls=[]
    monkeypatch.setattr(archive.subprocess,'check_output',lambda command:calls.append(command)or b'source')
    assert archive.source_blob('scripts/example.py')==b'source'
    assert calls==[['gh','api','-H','Accept: application/vnd.github.raw+json',f'repos/{archive.REPO}/contents/scripts/example.py?ref={archive.SOURCE}']]


def selected_receipts(tmp_path,monkeypatch,fault=None):
    def save(name,row):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(row))
    def blob(name,data):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    config={'PNR_CORNERS':archive.CORNERS}
    configpin=blob('source-config.json',json.dumps(config).encode());statepin=blob('source-state.json',b'{}')
    manifest=dict(runtime={'sha256':'runtime'},archive={'sha256':'bundle'},config='config.json',initial_state='state.json',files={'config.json':configpin,'state.json':statepin})
    save('source-manifest.json',manifest)
    record=dict(status='FAILED_PRESERVED',github_source_commit=archive.SOURCE,diagnostic_kind='targeted_hold_probe',selected_checkpoint_preserved=True,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,manifest_sha256='manifest',runtime_sha256='runtime',bundle_sha256='bundle',
        native_runs={'native-controls':{'returncode':0},'native-diagnostic':{'returncode':1}})
    if fault=='accepted':record['timing_accepted']=True
    if fault=='runtime':record['runtime_sha256']='other'
    save('result.json',record)
    native=dict(corners=[dict(name=c)for c in archive.CORNERS],endpoint_count=23527,engine_endpoint_count=23527,exported_endpoint_count=23527,
        negative_vertex_endpoints=113,engine_negative_vertex_endpoints=113,all_endpoint_coverage=True)
    if fault=='native-count':native['exported_endpoint_count']-=1
    save(archive.STEP+'matched_before/native.json',native)
    rows=['endpoint\tglobal_vertex_slack_seconds']+[f'q{i}\t'+('-1e-9'if i<113 else 'UNCONSTRAINED')for i in range(23527)]
    if fault=='duplicate':rows[-1]=rows[-2]
    if fault=='nonfinite':rows[-1]='last\tnan'
    if fault=='negatives':rows[1]='q0\t1e-9'
    blob(archive.STEP+'matched_before/endpoints.tsv','\n'.join(rows).encode())
    log=archive.GATE+'\n'+archive.FAILURE+' '.join(archive.CORNERS)+'\n'
    if fault=='repair-started':log+=archive.FORBIDDEN_MARKERS[0]+'\n'
    if fault=='missing-gate':log=archive.FAILURE
    blob(archive.STEP+'openroad-resizertimingpostgrt.log',log.encode())
    monkeypatch.setattr(archive,'source_pins',lambda *a:{archive.MANIFEST:{'sha256':'manifest'}})
    monkeypatch.setattr(archive,'replay_controls',lambda *a:dict(original_targeted_validator_rejected=True))
    return {}


@pytest.mark.parametrize('fault',[None,'accepted','runtime','native-count','duplicate','nonfinite','negatives','repair-started','missing-gate','repair-receipt'])
def test_real_baseline_census_and_incomplete_flags_are_required(tmp_path,monkeypatch,fault):
    members=selected_receipts(tmp_path,monkeypatch,fault)
    if fault=='repair-receipt':members[archive.STEP+'repair-invocation.json']=object()
    if fault:
        with pytest.raises(ValueError):archive.inspect_failure(tmp_path,members)
    else:
        row=archive.inspect_failure(tmp_path,members)
        assert row['matched_before_census']['endpoint_count']==23527
        assert row['matched_before_census']['negative_vertex_endpoints']==113
        assert row['original_targeted_validator_passed'] is False
        assert row['native_binary_rehashed'] is False
        assert row['native_repair_started'] is False


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
    workflow=(ROOT/'.github/workflows/timing-targeted-hold-failure-archive.yml').read_text()
    assert workflow.count('contents: write') == 1
    assert 'include-hidden-files: true' in workflow and 'if: always()' in workflow
    assert '--clobber' not in workflow and 'AppImage' not in workflow
    assert '      - .github/workflows/timing-targeted-hold-failure-archive.yml' in workflow
    assert 'scripts/archive_targeted_hold_failure.py --output' in workflow
