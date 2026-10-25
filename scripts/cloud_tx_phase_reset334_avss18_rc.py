#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One fresh two-polarity intrinsic/MIM then both-order RC pipeline; no simulation."""
import argparse,copy,hashlib,json,os,subprocess,traceback
from pathlib import Path
import tx_phase_reset334_avss18_rc_admission as admission
import tx_phase_reset334_avss18_rc_adapter as adapter
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter

def completed_controls():
    m=admission.methods();c=m['completed_source_controls'];assert isinstance(c,dict)
    for p,h in c['proof_files'].items():assert m['protected'][p]==h and admission.sha(admission.ROOT/p)==h
    tested=json.loads((admission.ROOT/c['tested_method_path']).read_bytes())
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    normalized=copy.deepcopy(m);normalized.update(native_execution_authorized=False,extraction_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((admission.ROOT/c['result_path']).read_bytes())
    assert r['status']=='PASS_AVSS18_FRESH_RC_SOURCE_CONTROLS_NO_NATIVE'
    assert r['native_execution']is r['extraction_executed']is r['simulation_executed']is False
    run=admission.frozen.api('actions/runs/'+str(c['run']));job=admission.frozen.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-avss18-rc-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    raw=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+admission.frozen.REPO+'/actions/jobs/'+str(c['job'])+'/logs'])
    assert raw==(admission.ROOT/c['log_path']).read_bytes()
    return dict(run=c['run'],job=c['job'],head=c['head'],log_sha256=hashlib.sha256(raw).hexdigest(),
      all_tested_protected_bytes_preserved=True)

def preflight():
    m=admission.methods()
    assert m['native_execution_authorized']is True and m['extraction_authorized']is True
    assert os.environ.get('ImageOS')=='ubuntu22'
    controls=completed_controls()
    waiter.wait(adapter.GROUP,os.environ)
    tag,head=release.context(adapter.GROUP,os.environ)
    proof=release.validate_release(release.api('releases/tags/'+tag),release.api('git/ref/tags/'+tag),tag,head)
    assert not proof['existing_assets'],'One fresh run; never reuse an existing production capsule'
    proof['completed_source_controls']=controls
    return proof

def write(path,r):
    b=(json.dumps(r,indent=2,allow_nan=False)+'\n').encode()
    temp=path.with_suffix('.json.tmp');temp.write_bytes(b);temp.replace(path)

def main():
    proof=preflight();root=adapter.OUT;root.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING_FRESH_AVSS18_NATIVE_RC',source_head=os.environ['GITHUB_SHA'],
      run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,reservation=proof,
      original_physical_source=admission.SOURCE,accepted=False,qualified_pex=False,
      electrical_accepted=False,physical_reset_qualified=False,all31_clock_tree_accepted=False,
      PLL_connected=False,full_phy_accepted=False,simulation_executed=False,
      geometry_generation_executed=False,old_R_rescaled=False,
      original_electrical_rejection_preserved=True,stages={})
    result=root/'result.json';write(result,r)
    write(root/'source-controls-prerequisite.json',proof['completed_source_controls'])
    error=None
    try:
        prior,proof=adapter.run_intrinsic()
        write(root/'physical-prerequisite.json',prior['physical_prerequisite'])
        r['stages']['intrinsic']=dict(status=prior['status'],source_sha256=admission.sha(adapter.INTRINSIC/'result.json'),derivation=proof)
        write(result,r)
        precise,proof=adapter.run_precision(prior)
        r['stages']['precision']=dict(status=precise['status'],source_sha256=admission.sha(adapter.PRECISION/'result.json'),derivation=proof)
        r['polarities']=precise['polarities']
        assert all(precise[k]is False for k in ('accepted','qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted'))
        r.update(status='PASS_FRESH_AVSS18_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED',
          fresh_native_RC_extracted=True,both_polarities_and_orders_verified=True,
          original_13_wire_9_MIM_faults_each_order_and19_composition_faults_preserved=True)
    except BaseException as e:
        error=e;r.update(status='FAIL_FRESH_AVSS18_RC',error=repr(e),traceback=traceback.format_exc())
    finally:
        for name,directory in [('fresh-intrinsic-result',adapter.INTRINSIC),('fresh-two-order-result',adapter.PRECISION)]:
            saved=directory/'result.json'
            if saved.is_file():
                copied=root/(name+'.json');copied.write_bytes(saved.read_bytes())
                assert admission.sha(copied)==admission.sha(saved)
        try:admission.methods();r['protected_sources_unchanged']=True
        except BaseException as e:
            error=error or e;r.update(status='FAIL_FRESH_AVSS18_RC',protected_sources_unchanged=False,source_error=repr(e))
        r['outputs']={str(p.relative_to(root)):admission.sha(p)for p in root.rglob('*')if p.is_file()and p!=result}
        write(result,r)
    if error is not None:raise error
    assert r['status']=='PASS_FRESH_AVSS18_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED'
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--preflight',action='store_true');args=p.parse_args()
    if args.controls:
        from check_tx_phase_reset334_avss18_rc import controls
        print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif args.preflight:print(json.dumps(preflight(),indent=2),flush=True)
    else:main()
