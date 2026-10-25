#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the exact failed postroute ODB pair; retain the original clock assertion."""
import argparse,ast,hashlib,json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import mainchip_saved_postroute_admission as admission
import mainchip_clock_diagnostic_helpers as helpers
import ensure_cloud_tested_source_release as guard
from cloud_mainchip_postroute_review import api
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-clock-diagnostic'
METHOD='scripts/mainchip-clock-diagnostic-methods.json'
ORIGINAL='scripts/check_mainchip_route12_all_clocks.py'
ORIGINAL_SHA='ed5669d48a87ce30d00fc3213792f7f57001651d4907d9367ca2b705f945c74b'
GROUP='mainchip-route12-clock-diagnostic'
SOURCE_RUN=40209284989
SOURCE_HEAD='d861793277aa2b724c083c8b478d52db06725e56'
SOURCE_GROUP='mainchip-route12-saved-postroute'
SUMMARY='7e09bafa19e24a6de1c6fa3113ec104fc7fe7a43e421ad61b233164308223bd5'
PARTS='4ae4920f85e70ab51029414c68a0ee4bb69891007642198a02e14da8188d4823'
BEFORE='geometry/routed/work/before-guide-read.odb'
AFTER='geometry/routed/work/detailed-route.odb'
BEFORE_SHA='2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a'
AFTER_SHA='9cdf9a6fb32d49894a5b23bd12ae4e6f400e1a945a9d2601e728f2d4ec7e0ae8'
MARKER=" assert snapshots['before']==snapshots['after'],'Source clock/fixed physical route or attached instance geometry changed'\n"
ADDITION=" from mainchip_clock_diagnostic_helpers import write_diagnosis\n write_diagnosis(out,snapshots,hashes)\n"
def methods():
    admission.methods()
    m=json.loads((ROOT/METHOD).read_bytes())
    for p,h in m['protected'].items():assert admission.sha(ROOT/p)==h,p
    return m
def derive():
    old=(ROOT/ORIGINAL).read_text()
    assert hashlib.sha256(old.encode()).hexdigest()==ORIGINAL_SHA and old.count(MARKER)==1
    new=old.replace(MARKER,ADDITION+MARKER)
    assert new.replace(ADDITION+MARKER,MARKER)==old
    ast.parse(new)
    return new,dict(original_sha256=ORIGINAL_SHA,derived_sha256=hashlib.sha256(new.encode()).hexdigest(),
        additive_insertions=1,original_selection_and_assertion_retained=True)
def live_source():
    run=api('actions/runs/'+str(SOURCE_RUN))
    assert run['id']==SOURCE_RUN and run['head_sha']==SOURCE_HEAD and run['run_attempt']==1
    assert run['head_branch']=='codex/mainchip-saved-postroute'
    assert run['path']=='.github/workflows/mainchip-saved-postroute-cloud.yml'
    assert run['status']=='completed'and run['conclusion']=='failure'
    jobs=api('actions/runs/'+str(SOURCE_RUN)+'/jobs?per_page=100')['jobs']
    assert {j['id']:j['conclusion']for j in jobs}=={121216874360:'success',121217089037:'failure'}
    tag='cloud-results-'+str(SOURCE_RUN)+'-1-'+SOURCE_GROUP
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,SOURCE_HEAD)
    return dict(run=SOURCE_RUN,source=SOURCE_HEAD,attempt=1,original_native_failure_retained=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--publish',action='store_true');args=p.parse_args()
    assert not(args.controls and args.publish)
    assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=methods()
    if args.publish:
        import publish_mainchip_saved_postroute as pub
        pub.GROUP=GROUP
        print(json.dumps(pub.publish_evidence(OUT,ROOT/('publication-'+GROUP)),indent=2),flush=True);return
    program,derivation=derive()
    if args.controls:
        print(json.dumps(dict(status='PASS_ADDITIVE_CLOCK_DIAGNOSTIC_SOURCE_NOT_NATIVE',
            source_head=os.environ['GITHUB_SHA'],derivation=derivation,
            comparison=helpers.controls(),protected=len(m['protected']),
            native_execution=False,final_timing_complete=False,full_phy_accepted=False),indent=2),flush=True);return
    assert m['diagnostic_execution_authorized']is True
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING_DIAGNOSTIC',source_head=os.environ['GITHUB_SHA'],
        accepted=False,final_timing_complete=False,full_phy_accepted=False,native_routing_started=False,
        scope='Read-only original1691-clock snapshot diagnosis. No gate bypass, route repair, RC, STA or signoff.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save();protected={}
    try:
        r['source']=live_source()
        selected=[BEFORE,AFTER,'geometry/result.json','geometry/topology.json','geometry/fixed-clock.json',
            'geometry/all-source-clocks.log','geometry/all-clocks/before.def','geometry/all-clocks/after.def']
        old,proof=reports.restore_report(SOURCE_GROUP,SOURCE_RUN,SUMMARY,PARTS,OUT/'source',selected)
        frozen=ROOT/'docs/evidence/mainchip-saved-postroute-first-native-full-summary-20261025.json'
        assert admission.sha(frozen)==SUMMARY and old==json.loads(frozen.read_bytes())
        assert old['status']=='FAIL_OR_ERROR'and old['error']=="AssertionError(('all-source-clocks', 1))"
        assert old['source_head']==SOURCE_HEAD and old['final_timing_complete']is False
        before=OUT/'source'/BEFORE;after=OUT/'source'/AFTER
        assert admission.sha(before)==BEFORE_SHA and admission.sha(after)==AFTER_SHA
        protected={str(OUT/'source'/p):old['outputs'][p]for p in selected}
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert admission.sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        target=OUT/'original-clock-check-with-report.py';target.write_text(program)
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        env.update(NSSOC_CLOCK_BEFORE=str(before),NSSOC_CLOCK_AFTER=str(after),
            NSSOC_CLOCK_AUDIT=str(OUT/'audit'),PYTHONPATH=str(ROOT/'scripts'))
        with(OUT/'native.log').open('w')as log:
            code=subprocess.call([str(app),'openroad','-exit','-python',str(target)],cwd=ROOT,
                env=env,stdout=log,stderr=subprocess.STDOUT)
        r.update(native_returncode=code,derivation=derivation,restore=proof);save()
        d=json.loads((OUT/'audit/diagnosis.json').read_bytes())
        assert d['before_nets']==d['after_nets'] and d['before_nets']>100 and d['accepted']is False
        assert d['original_equality_passed']is False and d['changed_nets']>0 and code==1
        assert 'AssertionError: Source clock/fixed physical route or attached instance geometry changed'in(OUT/'native.log').read_text()
        for side in ('before','after'):
            assert admission.sha(OUT/'audit'/(side+'.def'))==old['outputs']['geometry/all-clocks/'+side+'.def']
        assert all(admission.sha(Path(p))==h for p,h in protected.items())
        r.update(status='COMPLETE_DIAGNOSTIC_ORIGINAL_ALL_CLOCK_GATE_STILL_FAILED',
            diagnosis=d,inputs_unchanged=True,original_clock_gate_passed=False)
    except BaseException as e:
        r.update(status='FAIL_DIAGNOSTIC',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['inputs_unchanged']=all(admission.sha(Path(p))==h for p,h in protected.items())if protected else False
        r['outputs']={str(p.relative_to(OUT)):admission.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save();methods()
if __name__=='__main__':main()
