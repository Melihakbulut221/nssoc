#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only exact-model preparation. No simulator/native CAD invocation."""
import argparse,hashlib,json,os,subprocess,traceback
from pathlib import Path
import tx_phase_reset334_loaded_contract as bench
import check_tx_phase_reset334_loaded_preparation as checker
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-phase-reset334-loaded-preparation'
METHOD='scripts/tx-phase-reset334-loaded-preparation-methods.json'
GROUP='tx-phase-reset334-loaded-preparation'
BINDING=dict(run=40169988733,head='76eb57e7fc57086f0ccb7c087196c22065d2a740',release=423194058,
 group='tx-phase-reset334-loaded-binding',summary_asset=674308153,
 summary_sha256='ea7ca38a1c9cecdf374f3ba6ecdeb520275d51186a71d72c226e6a7a5474ae6b',
 parts_sha256='88f8ff5eef5780145db35053821775b1b60b37888294a42038bfc96d8b9b43b3')
def sha(path):return bench.digest(Path(path).read_bytes())
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def asset(ident,digest):
    meta=api('releases/assets/'+str(ident));assert meta['state']=='uploaded'and meta['digest']=='sha256:'+digest
    raw=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/releases/assets/'+str(ident),'-H','Accept: application/octet-stream'])
    assert len(raw)==meta['size']and bench.digest(raw)==digest
    return raw
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert not m['native_transient_authorized']
    return m
def source_controls():
    m=methods();proof=checker.controls();assert len(proof['rejected'])==15
    p=publication.controls();assert len(p['rejected'])==17
    return dict(status='PASS_THREE_MODEL_SOURCE_CONTROLS_ONLY',protected_files=len(m['protected']),
      preparation_controls=proof,publication_controls=p,simulator_invoked=False,**bench.FLAGS)
def prerequisite():
    run=api('actions/runs/'+str(BINDING['run']))
    assert run['head_sha']==BINDING['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    release=api('releases/'+str(BINDING['release']))
    assert release['tag_name']=='cloud-results-'+str(BINDING['run'])+'-1-'+BINDING['group']
    assert api('git/ref/tags/'+release['tag_name'])['object']['sha']==BINDING['head']
    assert any(a['id']==BINDING['summary_asset']for a in release['assets'])
    summary=asset(BINDING['summary_asset'],BINDING['summary_sha256'])
    report=json.loads(summary)
    assert report['source_head']==BINDING['head']and report['run_id']==BINDING['run']
    assert report['status']=='PASS_TWO_PHYSICAL334_ROLE_BINDINGS_NOT_LOADED_ELECTRICAL_ACCEPTANCE'
    assert report['validation_errors']==[]and report['sources_unchanged']and report['actual_native_binding_executed']
    return summary,report
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    m=methods();assert m['hosted_preparation_authorized']is True and m['native_transient_authorized']is False
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING_EXACT_PHYSICAL334_MODEL_PREPARATION',source_head=os.environ['GITHUB_SHA'],
      run_id=int(os.environ['GITHUB_RUN_ID']),validation_errors=[],simulator_invoked=False,new_extraction=False,
      native_runtime_or_model_libraries_installed=False,fixture_model_library_paths_only=True,**bench.FLAGS)
    try:
        tag,head=publication.context(GROUP,os.environ)
        result['release_prerequisite']=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
        raw,report=prerequisite();(OUT/'binding.summary.json').write_bytes(raw)
        selected=[p+'-bindings-and-controls.json'for p in ('p','n')]
        selected +=['qualified-rc/'+p+'/composition/reset334-wire.spice'for p in ('p','n')]
        restored,proof=reports.restore_report(BINDING['group'],BINDING['run'],BINDING['summary_sha256'],
          BINDING['parts_sha256'],OUT/'qualified-binding',selected)
        assert restored==report;result['qualified_binding_archive']=proof
        models={p:(OUT/'qualified-binding/qualified-rc'/p/'composition/reset334-wire.spice').read_text()for p in ('p','n')}
        payload={p:(OUT/'qualified-binding'/(p+'-bindings-and-controls.json')).read_bytes()for p in ('p','n')}
        observer=asset(bench.original.OBSERVER_ASSET,bench.original.OBSERVER_SHA)
        obrun=api('actions/runs/'+str(bench.original.OBSERVER_RUN))
        assert obrun['head_sha']==bench.original.OBSERVER_HEAD and obrun['run_attempt']==1
        assert obrun['status']=='completed'and obrun['conclusion']=='success'
        (OUT/'original-PLL-observer.summary.json').write_bytes(observer)
        paths={p:str(OUT/'qualified-binding/qualified-rc'/p/'composition/reset334-wire.spice')for p in ('p','n')}
        result['preparation']=checker.positive_prepare(raw,payload,models,observer,
          (ROOT/'hw/soc/analog/pcie/clock_div2_assert_offset_v4.spice').read_text(),
          paths,'/fixture/sg13g2-ngspice-models','/fixture/r3_cmc.osdi',OUT/'cases')
        assert result['preparation']['status']=='PASS_FOUR_EXACT_MODEL_PREPARATIONS_NOT_ELECTRICAL_ACCEPTANCE'
        assert len(result['preparation']['actual_input_faults'])==8 and len(result['preparation']['cases'])==4
        result['original_parent_TX_rejection']=json.loads((ROOT/'docs/evidence/tx-phase334-parent-TX-rejection-boundary-20261025.json').read_text())
        assert not result['original_parent_TX_rejection']['electrical_screen_passed']
        methods();result['sources_unchanged']=True
        result['status']='PASS_FOUR_REAL_THREE_MODEL_PREPARATIONS_NOT_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result['status']='FAIL_THREE_MODEL_PREPARATION'
        result['validation_errors'].append(dict(error=repr(error),traceback=traceback.format_exc()))
        raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        write(OUT/'result.json',result)
        print(json.dumps(dict(status=result['status'],result_sha256=sha(OUT/'result.json'),
          validation_errors=result['validation_errors'],simulator_invoked=False,
          postlayout_electrical_accepted=False,full_PHY_accepted=False)),flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source-controls',action='store_true');args=a.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.source_controls:print(json.dumps(source_controls(),indent=2,allow_nan=False))
    else:main()
