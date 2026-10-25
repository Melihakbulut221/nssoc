#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify expanded initialization on exact completed decks; never execute a DUT."""
import argparse,copy,json,os,subprocess,traceback
from pathlib import Path
import tx_phase_reset334_loaded_native_adapter as adapter
import check_tx_phase_reset334_loaded_native_adapter as checker
import cloud_tx_phase_reset334_loaded_preparation as preparation
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-phase-reset334-loaded-adapter'
METHOD='scripts/tx-phase-reset334-loaded-native-adapter-methods.json'
GROUP='tx-phase-reset334-loaded-adapter'
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert adapter.digest((ROOT/p).read_bytes())==h,p
    assert m['native_transient_authorized']is False
    return m
def controls():
    m=methods();c=checker.controls();assert len(c['negative_controls'])==30
    p=publication.controls();assert len(p['rejected'])==17
    return dict(status='PASS318_SOURCE_ADAPTER_CONTROLS_ONLY',
      source_controls=c,publication_controls=p,protected_files=len(m['protected']),
      native_simulator_executed=False,electrical_accepted=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    m=methods();assert m['hosted_adapter_controls_authorized']is True
    OUT.mkdir(exist_ok=False);reports.OUT=OUT;spec=adapter.PREPARATION
    result=dict(status='RUNNING_EXACT318_PREPARED_DECK_ADAPTER_CONTROLS',
      source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      validation_errors=[],native_simulator_executed=False,runtime_installed=False,
      zero_source_OP_executed=False,transient_executed=False,electrical_accepted=False,
      all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
    try:
        tag,head=publication.context(GROUP,os.environ)
        result['release_prerequisite']=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
        run=preparation.api('actions/runs/'+str(spec['run']))
        assert run['head_sha']==spec['head']and run['run_attempt']==1
        assert run['status']=='completed'and run['conclusion']=='success'
        oldtag='cloud-results-'+str(spec['run'])+'-1-tx-phase-reset334-loaded-preparation'
        assert preparation.api('git/ref/tags/'+oldtag)['object']['sha']==spec['head']
        summary_raw=preparation.asset(spec['summary_asset'],spec['summary_sha256'])
        summary=json.loads(summary_raw);(OUT/'preparation.summary.json').write_bytes(summary_raw)
        parts_raw=preparation.asset(spec['parts_asset'],spec['parts_sha256']);parts=json.loads(parts_raw)
        assert parts['bytes']==spec['archive_bytes']and parts['sha256']==spec['archive_sha256']
        assert parts['verification']['all_parts_and_combined_bytes_verified']
        (OUT/'preparation.parts.json').write_bytes(parts_raw)
        labels=[s+'-initial-'+h for s in ('p','n')for h in ('high','low')]
        selected=['cases/'+label+'/'+name for label in labels for name in ('bench.cir','contract.json')]
        restored,proof=reports.restore_report('tx-phase-reset334-loaded-preparation',spec['run'],
          spec['summary_sha256'],spec['parts_sha256'],OUT/'prepared',selected)
        assert restored==summary;result['full_preparation_archive_restore']=proof
        cases={};a=adapter.adapters()
        for label in labels:
            base=OUT/'prepared/cases'/label;deck=(base/'bench.cir').read_text()
            contract_raw=(base/'contract.json').read_bytes();contract=json.loads(contract_raw)
            expected=summary['preparation']['cases'][label]
            assert adapter.digest(contract_raw)==expected['contract_sha256']
            initialized,proof=adapter.prepared_contract(label,deck,contract,summary_raw)
            (base/'initialized-bench.cir').write_text(initialized)
            names=a.targets(contract)
            log=''.join('NSSOC_NATIVE_FLAG_BEGIN '+n+'\n  off 1\nNSSOC_NATIVE_FLAG_END\n'for n in names)
            flags=a.flags(log,contract,True);assert flags['actual_HBT_targets']==318
            faults=[
              checker.reject('missing-real-target',lambda:a.flags(log.split('NSSOC_NATIVE_FLAG_END\n',1)[1],contract,True)),
              checker.reject('wrong-real-target-OFF',lambda:a.flags(log.replace('off 1','off 0',1),contract,True)),
              checker.reject('changed-exact-prepared-deck',lambda:adapter.prepared_contract(label,deck+'\n',contract,summary_raw))]
            cases[label]=dict(**proof,actual_HBT_names=names,all318_target_markers_exercised=True,
              marker_log_is_synthetic_not_native_readback=True,negative_controls=faults)
        assert len(cases)==4 and sum(len(c['negative_controls'])for c in cases.values())==12
        result['cases']=cases
        result['original_parent_TX_rejection']=summary['original_parent_TX_rejection']
        assert not result['original_parent_TX_rejection']['electrical_screen_passed']
        assert methods()==m;result['sources_unchanged']=True
        result['status']='PASS_FOUR_EXACT318_DECK_ADAPTERS_NO_NATIVE_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:
        result['status']='FAIL_EXACT318_PREPARED_DECK_ADAPTER_CONTROLS'
        result['validation_errors'].append(dict(error=repr(error),traceback=traceback.format_exc()))
        raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):adapter.digest(p.read_bytes())for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        write(OUT/'result.json',result)
        print(json.dumps(dict(status=result['status'],result_sha256=adapter.digest((OUT/'result.json').read_bytes()),
          validation_errors=result['validation_errors'],native_simulator_executed=False,electrical_accepted=False)),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-controls',action='store_true');p.add_argument('--prepared-controls',action='store_true')
    a=p.parse_args();assert a.source_controls!=a.prepared_controls
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.source_controls:print(json.dumps(controls(),indent=2,allow_nan=False))
    else:main()
