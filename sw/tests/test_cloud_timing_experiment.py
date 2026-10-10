# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud input integrity, complete evidence, fixed-baseline guards and observers."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_timing_experiment as cloud
from run_timing_experiments import eligible


def entry(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value)+'\n')


def manifest():
    files = {'config.json': entry(b'config'), 'state.json': entry(b'state'),
             'source.log': entry(b'completed C10'), 'pdk/ihp-sg13g2/config.tcl': entry(b'pdk')}
    files.update({'methods/'+name: entry(name.encode()) for name in cloud.METHODS})
    return dict(schema=1, pdk='ihp-sg13g2', pdk_root='pdk', methods_dir='methods',
                config='config.json', initial_state='state.json', source_log='source.log', files=files,
                selected_source_metrics=dict(setup_wns_ns=-4.710829, hold_wns_ns=-1.840329),
                archive=dict(url='https://github.com/owner/repo/releases/download/v1/input.tar.gz', **entry(b'archive')),
                runtime=dict(url='https://github.com/librelane/librelane/releases/download/3.0.5/runtime.AppImage',
                             sha256=cloud.RUNTIME_SHA256, bytes=cloud.RUNTIME_BYTES))


def measurement(profile, phase, **changes):
    row=dict(profile=profile,phase=phase,signoff=False,parasitics='global_route_estimates',
             setup_wns_ns=-4.91,hold_wns_ns=-1.84,setup_tns_ns=-4320.,hold_tns_ns=-26.,
             setup_violating_endpoints=1384,hold_violating_endpoints=113,
             slew_violations=0,capacitance_violations=1,instance_count=103697,
             area_um2=4092933.,utilization_fraction=.535)
    row.update(changes)
    return row


def candidate(tmp_path, profile, after=None, before=None, elapsed=120):
    out=tmp_path/profile
    out.mkdir()
    m=manifest()
    write(out/'source-manifest.json',m)
    paths={}
    for name in ('odb','def','nl','sdc','pnl'):
        p=out/'run'/('soc_top.'+name);p.parent.mkdir(exist_ok=True);p.write_bytes(('native '+name).encode());paths[name]=str(p)
    write(out/'run/state_out.json',paths)
    source=m['selected_source_metrics']
    first=before or measurement(profile,'before')
    second=after or measurement(profile,'after',setup_wns_ns=-4.7,setup_tns_ns=-4200.)
    row=dict(profile=profile,status='COMPLETE_ESTIMATE_ONLY',returncode=0,before=first,after=second,
        elapsed_seconds=elapsed,eligible_estimate=eligible(first,second,source,'setup'),
        cloud_output_root=str(out),work=str(tmp_path/'work'),
        manifest_sha256=cloud.sha(out/'source-manifest.json'),bundle_sha256=m['archive']['sha256'],
        initial_state_template_sha256=m['files']['state.json']['sha256'],config_template_sha256=m['files']['config.json']['sha256'],
        source_log_sha256=m['files']['source.log']['sha256'],selected_source_metrics=source,runtime_sha256=cloud.RUNTIME_SHA256,
        method_sha256={name:m['files']['methods/'+name]['sha256'] for name in cloud.METHODS},
        runner_sha256=cloud.sha(ROOT/'scripts/run_cloud_timing_experiment.py'),sdc_sha256=cloud.sha(out/'run/soc_top.sdc'),
        output_state=str(out/'run/state_out.json'),
        output_sha256={str(p):cloud.sha(p) for p in (out/'run').iterdir()})
    write(out/'portable-state.json',cloud.portable_state(paths,out,tmp_path/'work/bundle'))
    write(out/'result.json',row)
    destination=tmp_path/(profile+'-capture')
    cloud.capture(out,destination)
    return destination/'result.json'


def mutate_result(path, change):
    row=json.loads(path.read_text());change(row);write(path,row)
    cap=json.loads((path.parent/'capture.json').read_text());cap['files']['result.json'].update(entry(path.read_bytes()))
    write(path.parent/'capture.json',cap)


@pytest.mark.parametrize('fault', ['absolute','traversal','double-slash','backslash','runtime','missing-method','url','nan'])
def test_manifest_fail_closed(fault):
    m=manifest()
    if fault in ('absolute','traversal','double-slash','backslash'):
        m['files'][{'absolute':'/root/x','traversal':'../x','double-slash':'a//b','backslash':'a\\b'}[fault]]=entry(b'x')
    elif fault=='runtime':m['runtime']['sha256']='0'*64
    elif fault=='missing-method':del m['files']['methods/timing_experiment_step.tcl']
    elif fault=='url':m['archive']['url']='http://example.com/input.tar.gz'
    else:m['selected_source_metrics']['setup_wns_ns']=float('nan')
    with pytest.raises(ValueError):cloud.validate_manifest(m)


def test_actual_published_manifest_contract_if_present():
    p=ROOT/'docs/evidence/timing-cloud-input-20260930.json'
    if not p.exists():pytest.skip('Campaign input manifest not present')
    m=cloud.validate_manifest(json.loads(p.read_text()))
    assert m['selected_source_metrics']==dict(setup_wns_ns=-4.710829,hold_wns_ns=-1.840329)
    assert all(n in m['files'] for n in ('original/source.log','methods/timing_experiment_step.tcl'))


@pytest.mark.parametrize('fault', [None,'traversal','link','duplicate','missing','hash','size','extra'])
def test_stream_restore_checks_every_member(tmp_path,fault):
    inventory={'dir/cell':entry(b'geometry')}
    archive=tmp_path/'input.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        entries=[] if fault=='missing' else [('dir/cell',b'geometry')]
        if fault=='duplicate':entries*=2
        if fault=='extra':entries.append(('extra',b'x'))
        for n,data in entries:
            info=tarfile.TarInfo('../escape' if fault=='traversal' else n);info.size=len(data)
            if fault=='link':info.type=tarfile.SYMTYPE;info.linkname='/tmp/foreign';info.size=0
            tar.addfile(info,io.BytesIO(data))
    if fault=='hash':inventory['dir/cell']['sha256']='0'*64
    if fault=='size':inventory['dir/cell']['bytes']+=1
    if fault is None:
        cloud.restore(archive,tmp_path/'bundle',inventory)
        cloud.verify_bundle(tmp_path/'bundle',inventory)
        assert (tmp_path/'bundle/dir/cell').read_bytes()==b'geometry'
        with pytest.raises(FileExistsError):cloud.restore(archive,tmp_path/'bundle',inventory)
    else:
        with pytest.raises(ValueError):cloud.restore(archive,tmp_path/'bundle',inventory)
    assert not (tmp_path/'escape').exists()


def test_bundle_and_path_translation_cannot_silently_change_inputs(tmp_path):
    root=tmp_path/'bundle';root.mkdir();(root/'x').write_bytes(b'pinned')
    inv={'x':entry(b'pinned')}
    assert cloud.translate({'a':['@BUNDLE@/x'],'literal':'nom_slow'},root,inv)=={'a':[str(root/'x')],'literal':'nom_slow'}
    for bad in ('@BUNDLE@/../x','prefix@BUNDLE@/x','/nix/store/other/x','@BUNDLE@/missing'):
        with pytest.raises(ValueError):cloud.translate(bad,root,inv)
    (root/'extra').write_bytes(b'unknown')
    with pytest.raises(ValueError,match='unlisted'):cloud.verify_bundle(root,inv)


def test_completed_ab_uses_both_gain_rates_and_keeps_signoff_false(tmp_path):
    a=candidate(tmp_path,'setup_baseline',elapsed=120)
    b=candidate(tmp_path,'setup_batch4',elapsed=60)
    out=cloud.compare([a,b],tmp_path/'comparison.json')
    assert out['status']=='COMPLETE_ESTIMATE_COMPARISON_ONLY'
    assert out['compared_profile']=='setup_batch4'
    assert out['selected_checkpoint_preserved'] and not out['timing_accepted']


@pytest.mark.parametrize('fault',['missing-receipt','missing-odb','bad-hash','partial-race','truncated','state-dependency','portable-state','input-id'])
def test_incomplete_or_changed_candidate_is_never_compared(tmp_path,fault):
    a=candidate(tmp_path,'setup_baseline');b=candidate(tmp_path,'setup_batch4')
    cap=b.parent/'capture.json'
    if fault=='missing-receipt':cap.unlink()
    elif fault=='missing-odb':(b.parent/'run/soc_top.odb').unlink()
    elif fault=='bad-hash':(b.parent/'run/soc_top.odb').write_bytes(b'changed')
    elif fault in ('partial-race','truncated'):
        value=json.loads(cap.read_text())
        if fault=='partial-race':value.update(complete_candidate_views=False,observation={'status':'RUNNING'},partial_native_database_excluded=True)
        else:value['files']['result.json']['source_truncated_during_copy']=True
        write(cap,value)
    elif fault=='state-dependency':
        mutate_result(b,lambda row:row['output_sha256'].pop(str(tmp_path/'setup_batch4/run/soc_top.pnl')))
    elif fault=='portable-state':
        p=b.parent/'portable-state.json';value=json.loads(p.read_text());value['odb']='@RESULT@/different';write(p,value)
        value=json.loads(cap.read_text());value['files']['portable-state.json'].update(entry(p.read_bytes()));write(cap,value)
    else:mutate_result(b,lambda row:row.update(bundle_sha256='0'*64))
    result=cloud.compare([a,b],tmp_path/'comparison.json')
    assert result['status']=='INCOMPLETE_AB' and result['compared_profile'] is None


@pytest.mark.parametrize('fault',['missing','none','malformed','fresh-before','source-regression','hold-regression'])
def test_missing_jobs_and_cross_domain_or_selected_source_guards(tmp_path,fault):
    a=candidate(tmp_path,'setup_baseline')
    if fault=='missing':paths=[a,tmp_path/'absent.json']
    elif fault=='none':paths=None
    elif fault=='malformed':
        p=tmp_path/'bad.json';p.write_text('{');paths=[a,p]
    else:
        after=measurement('setup_batch4','after',setup_wns_ns=-4.7,setup_tns_ns=-4200.)
        before=measurement('setup_batch4','before')
        if fault=='fresh-before':before['capacitance_violations']=2
        if fault=='source-regression':after['setup_wns_ns']=-4.8  # improves fresh -4.91, worse than selected -4.710829
        if fault=='hold-regression':after['hold_wns_ns']=-1.9
        b=candidate(tmp_path,'setup_batch4',after=after,before=before,elapsed=60);paths=[a,b]
    result=cloud.compare(paths,tmp_path/'comparison.json')
    if fault in ('source-regression','hold-regression'):
        assert result['status']=='COMPLETE_ESTIMATE_COMPARISON_ONLY'
        assert result['eligible_profiles']==['setup_baseline'] and result['compared_profile']=='setup_baseline'
    else:assert result['status']=='INCOMPLETE_AB'


def test_pending_capture_excludes_native_database_and_wait_does_not_signal(tmp_path):
    out=tmp_path/'worker';out.mkdir()
    write(out/'result.json',dict(status='RUNNING'))
    write(out/'launch.json',dict(pid=os.getpid(),identity=None))
    (out/'native.log').write_text('working\n');(out/'soc_top.odb').write_bytes(b'half db')
    result=cloud.wait(out,seconds=0)
    assert not result['terminal'] and result['worker_was_not_signaled']
    receipt=cloud.capture(out,tmp_path/'progress')
    assert not receipt['complete_candidate_views'] and not (tmp_path/'progress/soc_top.odb').exists()
    assert (tmp_path/'progress/native.log').read_text()=='working\n'


def test_workflow_observes_without_native_timeout_and_pins_actions():
    import yaml
    path=ROOT/'.github/workflows/timing-cloud-experiments.yml'
    value=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
    job=value['jobs']['setup']
    assert job['timeout-minutes']=='360'
    assert job['strategy']['fail-fast']=='false'
    assert set(job['strategy']['matrix']['profile'])==set(cloud.PROFILES)
    assert set(value['on']['push']['paths'])=={'.github/workflows/timing-cloud-experiments.yml','docs/evidence/timing-cloud-input-20260930.json'}
    commands='\n'.join(s.get('run','') for s in job['steps'])
    assert '--seconds 60' in commands and '--seconds 9000' in commands and '--seconds 7200' in commands
    assert 'timeout ' not in commands and 'kill ' not in commands
    for step in job['steps']:
        assert 'timeout-minutes' not in step
        if 'uses' in step:assert len(step['uses'].split('@')[1])==40


def test_start_creates_native_run_directory_before_detached_worker(tmp_path,monkeypatch):
    import types
    from run_timing_experiments import completed_slacks,state_pins
    blobs={'config.json':b'{}', 'pdk/ihp-sg13g2/config.tcl':b'pdk'}
    for field in ('odb','nl','def','sdc'):blobs['inputs/'+field]=field.encode()
    blobs['state.json']=json.dumps({field:'@BUNDLE@/inputs/'+field for field in ('odb','nl','def','sdc')}).encode()
    blobs['source.log']=(b'ALL_32_HARD_MACRO_MASTERS_LOCATIONS_ORIENTATIONS_PRESERVED\n'
                         b'CHUNK_SETUP_WNS_BEGIN\nworst slack max -4.710829\nCHUNK_SETUP_WNS_END\n'
                         b'CHUNK_HOLD_WNS_BEGIN\nworst slack min -1.840329\nCHUNK_HOLD_WNS_END\n'
                         b'COMPLETE_CHECKPOINT_REQUIRES_FRESH_ROUTING_RCX_STA_AND_EQUIVALENCE\n')
    blobs.update({'methods/'+name:name.encode() for name in cloud.METHODS})
    m=manifest();m['files']={name:entry(data) for name,data in blobs.items()}
    archive=tmp_path/'original.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for name,data in blobs.items():
            info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
    m['archive'].update(entry(archive.read_bytes()));mp=tmp_path/'manifest.json';write(mp,m)
    def download(pin,path):
        path.write_bytes(b'fake-runtime-not-executed' if path.name=='runtime.AppImage' else archive.read_bytes())
    monkeypatch.setattr(cloud,'download',download)
    monkeypatch.setattr(cloud,'resource_sample',lambda directory:dict(available_memory_bytes=16*cloud.GIB,free_disk_bytes=20*cloud.GIB))
    policy=types.SimpleNamespace(completed_slacks=completed_slacks,state_pins=state_pins,snapshot=lambda pid:dict(pid=pid,birth='1'))
    monkeypatch.setattr(cloud,'load_policy',lambda *args:policy)
    seen=[]
    def launch(command,**kwargs):
        assert (tmp_path/'output/run').is_dir()
        assert (tmp_path/'output/prepared/state.json').is_file()
        assert kwargs['stdin']==cloud.subprocess.DEVNULL and kwargs['start_new_session'] is True
        assert kwargs['close_fds'] is True and kwargs['stderr']==cloud.subprocess.STDOUT
        seen.append(command)
        return types.SimpleNamespace(pid=12345)
    monkeypatch.setattr(cloud.subprocess,'Popen',launch)
    row=cloud.start(mp,'setup_baseline',tmp_path/'output',tmp_path/'work')
    assert row['status']=='PREPARED' and seen[0][-3:]==['_worker','--output',str(tmp_path/'output')]
    assert json.loads((tmp_path/'output/launch.json').read_text())['pid']==12345


def test_resource_failure_never_launches_or_downloads(tmp_path,monkeypatch):
    mp=tmp_path/'manifest.json';write(mp,manifest())
    monkeypatch.setattr(cloud,'resource_sample',lambda directory:dict(available_memory_bytes=3*cloud.GIB,free_disk_bytes=20*cloud.GIB))
    def forbidden(*args,**kwargs):raise AssertionError('Resource failure must precede native/download work')
    monkeypatch.setattr(cloud,'download',forbidden);monkeypatch.setattr(cloud.subprocess,'Popen',forbidden)
    with pytest.raises(ValueError,match='resource guard'):
        cloud.start(mp,'setup_baseline',tmp_path/'output',tmp_path/'work')
    assert json.loads((tmp_path/'output/result.json').read_text())['status']=='FAILED_PRESERVED'
    assert not (tmp_path/'output/launch.json').exists()


def test_job_environment_uses_only_server_available_contexts():
    # GitHub rejects runner context before scheduling jobs.<id>.env.
    # https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability
    import re
    import yaml
    allowed={'github','needs','strategy','matrix','vars','secrets','inputs'}
    workflow=yaml.load((ROOT/'.github/workflows/timing-cloud-experiments.yml').read_text(),Loader=yaml.BaseLoader)
    for job in workflow['jobs'].values():
        for value in job.get('env',{}).values():
            for expression in re.findall(r"\$\{\{(.*?)\}\}",value):
                contexts=set(re.findall(r"\b([a-zA-Z_][a-zA-Z_0-9]*)\s*\.",expression))
                assert contexts <= allowed, (expression,contexts-allowed)
    assert workflow['jobs']['setup']['env']['CLOUD_WORK']=='${{ github.workspace }}/timing-cloud-input'
