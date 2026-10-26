#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Owned-process fresh two-order wire/MIM RC from the exact saved tail-M4 physical capsule."""
import argparse,ast,copy,hashlib,json,os,subprocess,sys,traceback,types
from pathlib import Path
import tx_phase_reset334_tail_m4_rc_admission as admission
import tx_phase_reset334_tail_m4_rc_adapter as adapter
import ensure_cloud_tested_source_release as guard
import wait_cloud_tested_source_release as waiter
import cdr_v59_tail_access_runtime as runtime
ROOT=admission.ROOT
METHOD=admission.METHOD
GROUP=adapter.GROUP
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-tail-m4-rc'
STAGE=adapter.OUT
ORIGINAL='scripts/cloud_tx_phase_reset334_avss18_rc.py'
ORIGINAL_SHA='4e867fc7a91205576009eb0a2f4d4624fd42061a8fe51c77e30a2e2d2b1a40b5'
STATUS='PASS_TAIL_M4_FRESH_RC_SOURCE_CONTROLS_NO_NATIVE'
PASS='PASS_FRESH_TAIL_M4_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
sha=admission.sha
EDITS=[('RUNNING_FRESH_AVSS18_NATIVE_RC', 'RUNNING_FRESH_TAIL_M4_NATIVE_RC'), ('PASS_FRESH_AVSS18_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED', 'PASS_FRESH_TAIL_M4_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED'), ('FAIL_FRESH_AVSS18_RC', 'FAIL_FRESH_TAIL_M4_RC')]

def write(path,r):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def methods():
    m=admission.methods()
    assert m['owned_process']==dict(seconds=18000,minimum_available_kib=2097152,maximum_group_rss_kib=10485760,output_limit_per_stream_bytes=16777216)
    return m

def completed_controls():
    m=methods();c=m['completed_source_controls'];assert isinstance(c,dict)
    tested_raw=(ROOT/c['tested_method_path']).read_bytes();tested=json.loads(tested_raw)
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    for p,h in c['proof_files'].items():assert m['protected'][p]==h==sha(ROOT/p)
    normalized=copy.deepcopy(m)
    normalized.update(native_execution_authorized=False,extraction_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((ROOT/c['result_path']).read_bytes())
    assert r['status']==STATUS and r['native_executed']is False
    run=admission.frozen.api('actions/runs/'+str(c['run']));job=admission.frozen.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-rc-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+guard.REPO+'/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    for key in ('publication','imports','wait'):
        record=json.loads((ROOT/c[key+'_path']).read_bytes())
        assert record==r['completed_auxiliary_controls'][key]
    return dict(run=c['run'],job=c['job'],head=c['head'],log_sha256=hashlib.sha256(log).hexdigest(),
                tested_method_sha256=hashlib.sha256(tested_raw).hexdigest(),all_tested_pins_unchanged=True)


def authorize(m):
    assert m['native_execution_authorized']is m['extraction_authorized']is True
    for key in ('simulation_authorized','geometry_generation_authorized','continuation_authorized','zero_op_authorized'):
        assert m[key]is False,key
    release={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '='in line:
            k,v=line.split('=',1);release[k]=v.strip('"')
    assert release['ID']=='ubuntu'and release['VERSION_ID']=='22.04'
    assert os.environ['ImageOS']=='ubuntu22'

def derive():
    m=methods();raw=(ROOT/ORIGINAL).read_bytes();assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='main')
    before=ast.get_source_segment(raw.decode(),node);after=before;edits=[]
    for old,new in EDITS:
        count=after.count(old);assert count>0 and new not in after
        after=after.replace(old,new);edits.append(dict(before=old,after=new,count=count))
    reverse=after
    for e in reversed(edits):
        assert reverse.count(e['after'])==e['count'];reverse=reverse.replace(e['after'],e['before'])
    assert reverse==before;ast.parse(after)
    proof=dict(original_main_sha256=hashlib.sha256(before.encode()).hexdigest(),
               generated_main_sha256=hashlib.sha256(after.encode()).hexdigest(),edit_count=len(edits))
    assert proof==m['controller_derivation']
    return after,dict(**proof,reversed_byte_exact=True,edits=edits)

def preflight():
    m=methods();authorize(m);controls=completed_controls()
    waiter.wait(GROUP,os.environ)
    tag,head=guard.context(GROUP,os.environ)
    reservation=guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert not reservation['existing_assets']
    return dict(reservation=reservation,completed_controls=controls,source_head=os.environ['GITHUB_SHA'],
                run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']))

def child_preflight():
    m=methods();authorize(m)
    proof=json.loads((OUT/'authorized-preflight.json').read_bytes())
    assert (proof['source_head'],proof['run_id'],proof['run_attempt'])==(os.environ['GITHUB_SHA'],int(os.environ['GITHUB_RUN_ID']),1)
    assert proof['completed_controls']==completed_controls()
    tag,head=guard.context(GROUP,os.environ)
    current=guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert current==proof['reservation']and not current['existing_assets']
    return dict(current,completed_source_controls=proof['completed_controls'])

def install():
    body,proof=derive()
    module=types.ModuleType('tail_m4_qualified_rc_main')
    module.__dict__.update(json=json,os=os,traceback=traceback,adapter=adapter,admission=admission,
                           preflight=child_preflight,write=write)
    exec(compile(body,'derived-tail-M4-qualified-RC-main','exec'),module.__dict__)
    return module,proof

def child():
    methods();module,_=install();module.main()

def finalize(report):
    native=STAGE/'result.json';report['native_result_present']=native.is_file()
    if native.is_file():
        raw=native.read_bytes();copied=OUT/'native-RC-result.json';copied.write_bytes(raw)
        report.update(native_result_sha256=hashlib.sha256(raw).hexdigest(),native_result_bytes=len(raw),
                      native_result_raw_path=copied.name)
        assert sha(copied)==report['native_result_sha256']
        try:
            parsed=json.loads(raw);assert isinstance(parsed,dict),'Native result must be an object'
        except Exception as error:
            report.update(status='FAIL_OR_ERROR',native_result_parse_error=repr(error),
                          native_result_parse_traceback=traceback.format_exc())
        else:report['native_result']=parsed
    for name,directory in [('fresh-intrinsic-result',adapter.INTRINSIC),('fresh-two-order-result',adapter.PRECISION)]:
        saved=directory/'result.json'
        if saved.is_file():
            copied=OUT/(name+'.json');copied.write_bytes(saved.read_bytes());assert sha(copied)==sha(saved)
    prior=STAGE/'physical-prerequisite.json'
    if prior.is_file():(OUT/'physical-prerequisite.json').write_bytes(prior.read_bytes())
    try:methods();report['protected_sources_unchanged']=True
    except BaseException as error:
        report.update(status='FAIL_OR_ERROR',protected_sources_unchanged=False,
                      source_error=repr(error),source_traceback=traceback.format_exc())
    report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
    write(OUT/'result.json',report)
    return report

def run_owned_child():
    import signal,threading
    m=methods();trace=OUT/'supervision';trace.mkdir(exist_ok=False)
    owned=runtime.supervisor(ROOT,OUT,trace,methods,m['protected'][runtime.SAMPLER])
    old_signals={s:signal.signal(s,owned.interrupted)for s in (signal.SIGTERM,signal.SIGINT)}
    worker=threading.Thread(target=owned.heartbeat,daemon=True);worker.start()
    try:
        probe=runtime.launcher(ROOT,methods,m['protected'][runtime.PROBE])
        observed=probe.probe(Path(os.environ['CLOUD_APPIMAGE']),APP_SHA,OUT/'runtime-preflight')
        write(OUT/'runtime-preflight.json',observed)
        assert observed['accepted']and observed['interpreter']['pya_version']=='0.30.7'
        result=owned.supervised([sys.executable,'-B',ROOT/'scripts/cloud_tx_phase_reset334_tail_m4_rc.py','--child'],
            'complete-two-polarity-both-order-RC',False,seconds=m['owned_process']['seconds'],cwd=OUT)
        record=json.loads((trace/'complete-two-polarity-both-order-RC.command.json').read_text())
        assert record['returncode']==result.returncode and not record['supervision_failure']
        assert not record['process_group_cleanup']['remaining_live']
        return record
    finally:
        owned.stop_process(owned.ACTIVE);owned.STOP.set();worker.join(timeout=2)
        for sig,handler in old_signals.items():signal.signal(sig,handler)
        owned.sample('final_resource_sample')


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),electrical_accepted=False,full_phy_accepted=False,
      simulation_executed=False,geometry_generation_executed=False,continuation_executed=False,zero_op_executed=False,
      original_electrical_rejection_preserved=True,old_R_rescaled=False)
    write(OUT/'result.json',report);error=None
    try:
        report['preflight']=preflight();write(OUT/'authorized-preflight.json',report['preflight'])
        report['derivation']=derive()[1];write(OUT/'result.json',report)
        report['supervisor']=run_owned_child()
        native=json.loads((STAGE/'result.json').read_bytes())
        assert report['supervisor']['returncode']==0 and native['status']==PASS
        assert native['protected_sources_unchanged']and native['fresh_native_RC_extracted']
        assert native['both_polarities_and_orders_verified']
        assert native['original_13_wire_9_MIM_faults_each_order_and19_composition_faults_preserved']
        for key in ('electrical_accepted','full_phy_accepted','simulation_executed','geometry_generation_executed','old_R_rescaled'):
            assert native[key]is False,key
        report.update(status=PASS,native_extraction_completed=True,both_orders_qualified=True,
                      fresh_current_four_OP_and_original_loaded_waveforms_required=True)
    except BaseException as e:
        error=e;report.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc())
    finally:finalize(report)
    if error is not None:raise error
    assert report['status']==PASS
    return report

def controls():
    methods()
    from check_tx_phase_reset334_tail_m4_rc import controls as check
    return check()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--child',action='store_true');a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif a.child:child()
    else:main()
