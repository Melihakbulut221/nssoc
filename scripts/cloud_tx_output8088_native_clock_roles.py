#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact qualified TX archive restoration and native clock-role proof, no simulation."""
import argparse,copy,json,os,subprocess,traceback
from pathlib import Path
import bind_tx_output8088_native_clock_roles as roles
import compare_cloud_routed_endpoints as restore
from cloud_verified_parts import controls as archive_controls
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-native-clock-roles'
WORK=ROOT/'hw/soc/out/cloud-tx-output8088-native-clock-roles-restored'
METHOD=ROOT/'scripts/tx-output8088-native-clock-roles-cloud-methods.json'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
GROUP='tx-output8088-branchtailfeed-interfaces'
REPO='repos/Melihakbulut221/nssoc/'
def host():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert roles.sha(ROOT/p)==h,(p,'Source changed')
    return m
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def validate_run(r):
    assert r['id']==roles.SOURCE_RUN and r['run_attempt']==1
    assert r['status']=='completed'and r['conclusion']=='success'
    assert r['head_sha']==roles.SOURCE_HEAD and r['head_branch']=='codex/tx-via3-rail-diagnosis'
    assert r['path']=='.github/workflows/tx-output8088-branchtailfeed-interfaces-cloud.yml'
def validate_summary(s):
    assert s['source_head']==roles.SOURCE_HEAD and s['sources_unchanged']
    assert s['status']=='PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES'
    assert s['native_returncode']==0 and s['no_new_simulation']
    assert s['accepted']is False and s['electrical_accepted']is False
    assert s['full_phy_accepted']is False and s['qualified_pex']is False
    assert s['interfaces_sha256']==roles.PIN['interfaces.json']
    assert s['counts']==dict(input_legs=124,data_bases=372,driver_handoffs=64,output_ports=4,native_terminals=28620)
    assert len(s['controls'])==8 and all(c['rejected']for c in s['controls'])
    assert len(s['actual_endpoint_faults'])==2 and all(c['rejected']for c in s['actual_endpoint_faults'])
    assert len(s['output_port_controls'])==2 and all(c['rejected']for c in s['output_port_controls'])
    for p,h in roles.PIN.items():assert s['outputs'][p]==h,(p,'Parent file hash changed')
def summary():
    b=subprocess.check_output(['gh','api',REPO+'releases/assets/671922034','-H','Accept: application/octet-stream'])
    import hashlib
    assert hashlib.sha256(b).hexdigest()==roles.SUMMARY
    s=json.loads(b);validate_summary(s);return s
def controls():
    host();pins();s=summary();r=api('actions/runs/'+str(roles.SOURCE_RUN));validate_run(r)
    faults=[]
    for fault in('wrong_source','missing_native_terminals','wrong_model','wrong_native_binder',
                 'wrong_interface','missing_fault','unrejected_fault','PHY_claim','native_failure',
                 'changed_runtime_run','uncompleted_run','wrong_workflow'):
        a=copy.deepcopy(s);b=copy.deepcopy(r)
        if fault=='wrong_source':a['source_head']='0'*40
        elif fault=='missing_native_terminals':a['counts']['native_terminals']-=1
        elif fault=='wrong_model':a['outputs']['composed/output8088-wire.spice']='0'*64
        elif fault=='wrong_native_binder':a['outputs']['bind-native-interfaces.py']='0'*64
        elif fault=='wrong_interface':a['interfaces_sha256']='0'*64
        elif fault=='missing_fault':a['controls'].pop()
        elif fault=='unrejected_fault':a['actual_endpoint_faults'][0]['rejected']=False
        elif fault=='PHY_claim':a['full_phy_accepted']=True
        elif fault=='native_failure':a['native_returncode']=1
        elif fault=='changed_runtime_run':b['run_attempt']=2
        elif fault=='uncompleted_run':b['status']='in_progress'
        else:b['path']='.github/workflows/unrelated.yml'
        try:validate_run(b);validate_summary(a)
        except AssertionError as e:faults.append(dict(name=fault,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+fault)
    archived=archive_controls()
    pins()
    return dict(status='PASS_EXACT_PARENT_METADATA_AND_ARCHIVE_CONTROLS_NOT_NATIVE_ROLES',
                source_run=roles.SOURCE_RUN,source_summary_sha256=roles.SUMMARY,
                controls=faults,archive_controls=archived,native_role_execution=False,full_phy_accepted=False)
def check_result(r,original_interface):
    assert original_interface==roles.PIN['interfaces.json']
    assert r['status']=='PASS_NATIVE_CLOCK_ROLE_BINDING_REQUIRES_REAL_DRIVER_AND_LOADED_WAVES'
    assert r['counts']==dict(pairs=31,public_clock_legs=62,selector_HBT_bases=124,tail_HBTs=62,original_native_terminals_rechecked=28620)
    assert r['source_run']==roles.SOURCE_RUN and r['source_head']==roles.SOURCE_HEAD
    assert r['summary_sha256']==roles.SUMMARY and r['parts_sha256']==roles.PARTS
    assert r['qualified_input_hashes']==roles.PIN and r['qualified_inputs_unchanged']and r['native_reprobe']
    for key in ('real_clock_drivers_implemented','electrical_accepted','reset_distribution_accepted',
                'full31_tree_accepted','PLL_connected','full_phy_accepted','mainchip_integrated'):
        assert r[key]is False,(key,'Scope widened')
    assert len(r['clocks'])==62 and len({x['macro']for x in r['clocks'].values()})==31
    assert all(len(x['selector_devices'])==2 and len(x['tail_devices'])==2 for x in r['clocks'].values())
    assert len({d['native_id']for x in r['clocks'].values()for d in x['selector_devices']})==124
    assert len(r['role_controls'])==14 and all(c['rejected']for c in r['role_controls'])
    assert len({c['name']for c in r['role_controls']})==14
    assert len(r['actual_polarity_faults'])==31 and len({c['macro']for c in r['actual_polarity_faults']})==31
    assert all(c['wrong_p_to_n_rejected']and c['wrong_n_to_p_rejected']for c in r['actual_polarity_faults'])
def main():
    host();method=pins();OUT.mkdir(parents=True,exist_ok=False);assert not WORK.exists()
    restore.OUT=OUT
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,
                electrical_accepted=False,no_new_simulation=True,source_run=roles.SOURCE_RUN)
    def save():(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        validate_run(api('actions/runs/'+str(roles.SOURCE_RUN)))
        pinned=summary()
        restored,proof=restore.restore_report(GROUP,roles.SOURCE_RUN,roles.SUMMARY,roles.PARTS,WORK,list(roles.PIN))
        assert restored==pinned and roles.sha(WORK/'result.json')==roles.SUMMARY
        validate_summary(restored);report['restore']=proof;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert roles.sha(app)==APP_SHA
        with(OUT/'native-role-binding.log').open('w')as log:
            code=subprocess.call([str(app),'python',str(ROOT/'scripts/bind_tx_output8088_native_clock_roles.py'),
                                  str(WORK),str(WORK/'result.json'),str(OUT/'native')],
                                 cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        report['native_returncode']=code;save()
        assert code==0,'Native clock role, bank topology or physical polarity check rejected'
        r=json.loads((OUT/'native/clock-roles.json').read_text())
        original_hash=roles.sha(OUT/'native/original-interfaces.json');check_result(r,original_hash)
        pins();assert all(roles.sha(WORK/p)==h for p,h in roles.PIN.items())
        report.update(status=r['status'],sources_unchanged=True,counts=r['counts'],
            clock_roles_sha256=roles.sha(OUT/'native/clock-roles.json'),
            original_interfaces_sha256=original_hash,role_controls=r['role_controls'],
            actual_polarity_faults=r['actual_polarity_faults'],source_summary_sha256=roles.SUMMARY,
            source_parts_sha256=roles.PARTS,protected_inputs=roles.PIN,
            next='Use actual role map in reviewed real clock-driver/load composition; no electrical, phase, reset, PLL or fullPHY acceptance.')
    except BaseException as e:
        report.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        report['outputs']={str(p.relative_to(OUT)):roles.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2))
    else:main()
