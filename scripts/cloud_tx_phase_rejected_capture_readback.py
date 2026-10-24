#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reread rejected intrinsic captures without rerunning or accepting the DUT."""
import argparse,copy,json,os,re,tempfile
from pathlib import Path
import numpy as np
import cloud_tx_phase_async_preset_intrinsic as original
import tx_phase_async_preset_diagnostic as bench
import check_tx_phase_async_preset_intrinsic as old_controls
import compare_cloud_routed_endpoints as restore
from cloud_verified_parts import controls as archive_controls
from cloud_tx_stream import read_streamed_wave
from run_cloud_tx_mux4 import native_diagnostics,verify_solver_options
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-rejected-capture-readback'
METHOD=ROOT/'scripts/tx-phase-rejected-capture-readback-methods.json'
RUN=40093613768
HEAD='fe649b9d96356afe9ff45c25ed1f5ea094d47035'
SUMMARY='ac0588977d072e418fcc15362fe6439efce9a0a31106aafdb948358b5dcf40a9'
PARTS='adc576815a3c4a7bff605311a7f4d9d31319a6731d5297ec58454d4cbc6206a7'
CASES={s+'-'+('initial-high'if h else'initial-low'):(s,h)for s in ('p','n')for h in (True,False)}
def pins():
    d=json.loads(METHOD.read_text())
    for p,h in d['protected'].items():assert sha(ROOT/p)==h,p
    return d
def rejected_summary(d):
    assert int(d['run_id'])==RUN and d['source_head']==HEAD
    assert d['status']=='REJECTED_INTRINSIC_RESET_DIAGNOSTIC_PRESERVE_ALL_FAILURES'
    assert not d['all_four_complete']and not d['all_four_diagnostic_screens_passed']
    assert d['sources_unchanged']and set(d['native_cases'])==set(CASES)
    assert not any(d[k]for k in ('reset_hardware_qualified','layout_RC_included','PLL_connected','full_PHY_accepted'))
    for c,row in d['native_cases'].items():
        assert row['returncode']==0 and not row['complete']and not row['diagnostic_screen_passed']
        assert row['hbt_count']==106 and row['primitive_count']==241 and row['vector_count']==355
        assert row['error']=="AssertionError('Native diagnostics/process failure')"
        assert row['diagnostics']and any('NaN'in v for v in row['diagnostics'])and any('stepping'in v for v in row['diagnostics'])
    return True
def validate_case(d,label,folder,bound):
    sign,high=CASES[label];row=d['native_cases'][label]
    source=(folder/'candidate.spice').read_text();deck=(folder/'bench.cir').read_text()
    contract=json.loads((folder/'contract.json').read_text())
    assert sha(folder/'candidate.spice')==row['source_sha256']==bench.SOURCE_SHA
    assert sha(folder/'bench.cir')==row['deck_sha256']
    assert sha(folder/'contract.json')==row['contract_sha256']
    source_path=re.findall(r'(?m)^\.include "([^"]+)"$',deck)
    libs=re.findall(r'(?m)^\.lib "([^"]+)" (hbt_typ|res_typ|cap_typ)$',deck)
    osdi=re.findall(r'(?m)^pre_osdi (\S+)$',deck)
    assert len(source_path)==1 and len(libs)==3 and len(osdi)==1
    parents={str(Path(p).parent)for p,c in libs};assert len(parents)==1
    rebuilt,expected=bench.prepare(source,bound,sign,high,source_path[0],next(iter(parents)),osdi[0])
    assert deck==rebuilt and contract==expected,'Changed original source/contract/deck'
    log=(folder/'native.log').read_text()
    assert sha(folder/'native.log')==row['native_log_sha256']==d['outputs'][label+'/native.log']
    assert verify_solver_options(log,bench.PROFILE)==row['solver']
    diagnostics=native_diagnostics(log,bench.PROFILE)
    assert diagnostics==row['diagnostics']and diagnostics,'Original numerical rejection must remain'
    return contract,dict(returncode=row['returncode'],diagnostics=diagnostics,
      original_rejection_exactly_reproduced=True,numerically_accepted=False,
      source_sha256=sha(folder/'candidate.spice'),deck_sha256=sha(folder/'bench.cir'),
      contract_sha256=sha(folder/'contract.json'),log_sha256=sha(folder/'native.log'))
def disposition(cases):
    assert set(cases)==set(CASES)
    assert all(c['original_rejection_exactly_reproduced']and not c['numerically_accepted']for c in cases.values())
    assert all(c['capture']['complete_unmodified_rows']and c['capture']['columns']==356 for c in cases.values())
    assert all(len(c['measurement']['hbt_safety'])==106 for c in cases.values())
    return dict(status='PASS_READBACK_OF_REJECTED_NATIVE_CAPTURES_NOT_CIRCUIT_ACCEPTANCE',
      all_four_original_rejections_reproduced=True,all_four_transport_complete=True,
      rejected_waveform_screen_results={k:v['measurement']['diagnostic_screen_passed']for k,v in cases.items()},
      original_native_accepted=False,native_execution=False,reset_hardware_qualified=False,
      layout_RC_included=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    locked=pins();archive=archive_controls();reject=[]
    def fails(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):reject.append(name)
        else:raise AssertionError('Corruption accepted: '+name)
    good={label:dict(original_rejection_exactly_reproduced=True,numerically_accepted=False,
      capture=dict(complete_unmodified_rows=True,columns=356),
      measurement=dict(hbt_safety={str(i):{}for i in range(106)},diagnostic_screen_passed=True))for label in CASES}
    assert not disposition(good)['original_native_accepted']
    for name,key,value in [('waived_diagnostics','numerically_accepted',True),
      ('changed_rejection','original_rejection_exactly_reproduced',False)]:
        bad=copy.deepcopy(good);bad['p-initial-high'][key]=value;fails(name,lambda:disposition(bad))
    for name,key,value in [('incomplete_capture','complete_unmodified_rows',False),('missing_column','columns',355)]:
        bad=copy.deepcopy(good);bad['p-initial-high']['capture'][key]=value;fails(name,lambda:disposition(bad))
    bad=copy.deepcopy(good);bad.pop('n-initial-low');fails('missing_case',lambda:disposition(bad))
    bad=copy.deepcopy(good);bad['n-initial-high']['measurement']['hbt_safety'].pop('105');fails('missing_HBT',lambda:disposition(bad))
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'fixture.raw';v=['v(a)','@q.x.qnpn13g2[ic]'];step=bench.STEP
        rows=np.array([[0.,0.,0.],[step,1.,.001],[2*step,-1.,-.001]])
        old_controls.raw_fixture(p,v,rows)
        assert read_streamed_wave(p,v,2*step,step)[2]['complete_unmodified_rows']
        base=p.read_bytes()
        for name,data in [('truncated',base[:-1]),('extra_byte',base+b'x'),
          ('wrong_vector',base.replace(b'v(a)',b'v(b)')),('wrong_count',base.replace(b'No. Points: 3',b'No. Points: 4'))]:
            p.write_bytes(data);fails(name,lambda:read_streamed_wave(p,v,2*step,step))
        for name,rows in [('nonfinite',np.array([[0.,0.,0.],[step,np.nan,.001],[2*step,0.,0.]])),
          ('nonmonotone',np.array([[0.,0.,0.],[step,0.,0.],[step,0.,0.]])),
          ('gap',np.array([[0.,0.,0.],[.5*step,0.,0.],[2*step,0.,0.]]))]:
            old_controls.raw_fixture(p,v,rows);fails(name,lambda:read_streamed_wave(p,v,2*step,step))
    assert len(reject)==13 and pins()==locked
    print(json.dumps(dict(status='PASS_REJECTED_CAPTURE_READER_CONTROLS_NO_NATIVE',negative_controls=reject,
      archive_controls=archive,original_acceptance_always_false=True,native_execution=False),indent=2))
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    locked=pins();original_pins=original.source_pins();OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING_REJECTED_CAPTURE_READBACK',run_id=os.environ['GITHUB_RUN_ID'],source_head=os.environ['GITHUB_SHA'],
      source_run=RUN,source_native_head=HEAD,summary_sha256=SUMMARY,parts_sha256=PARTS,cases={},
      scope='Exact full-column readback of already rejected four intrinsic captures. Original numerical rejection remains authoritative even if observations pass. No simulator, changed circuit, signal phase fit, solver option, parameter, capture or acceptance waiver.',
      original_native_accepted=False,native_execution=False,reset_hardware_qualified=False,layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        restore.OUT=ROOT/'hw/soc/out/phase-rejected-readback-inputs';restore.OUT.mkdir(exist_ok=False)
        capture=restore.OUT/'captures'
        selected=['pll-observer.summary.json']+[label+'/'+name for label in CASES for name in ('wave.raw','op.raw','candidate.spice','bench.cir','contract.json','native.log')]
        source,proof=restore.restore_report('tx-phase-async-preset-intrinsic',RUN,SUMMARY,PARTS,capture,selected)
        rejected_summary(source);assert source['protected']==original_pins
        assert source['runtime_and_models']['engine_sha256']==original.ENGINE_SHA
        bound=bench.boundary((capture/'pll-observer.summary.json').read_bytes());assert bound==source['boundary']
        result.update(source_restoration=proof,original_status=source['status'],boundary=bound);save()
        for label in CASES:
            case=capture/label
            contract,row=validate_case(source,label,case,bound);result['cases'][label]=row;save()
            # OP and transient observations do not retroactively waive diagnostics.
            try:row['zero_source_op']=original.zero_op(case/'op.raw',contract['vectors'])
            except (AssertionError,KeyError,ValueError)as exc:row['zero_source_op_error']=repr(exc)
            t,values,transport=read_streamed_wave(case/'wave.raw',contract['vectors'],bench.STOP,bench.STEP)
            row['capture']=transport;assert transport['raw_sha256']==source['outputs'][label+'/wave.raw']
            row['measurement']=bench.review(t,values,contract)
            active=t>=bench.START
            row['all_saved_ranges']={name:dict(minimum=float(v.min()),maximum=float(v.max()),
              post_START_minimum=float(v[active].min()),post_START_maximum=float(v[active].max()))for name,v in values.items()}
            row['failed_HBT']={k:v for k,v in row['measurement']['hbt_safety'].items()if not v['passed']}
            row['thermal_vectors']=[k for k in values if k.endswith('.dt)')]
            assert len(row['thermal_vectors'])==127
            for name in ('wave.raw','op.raw','candidate.spice','bench.cir','contract.json','native.log'):
                assert sha(case/name)==source['outputs'][label+'/'+name]
            save()
            print(json.dumps(dict(case=label,transport_complete=True,original_native_accepted=False,
              rows=transport['header_rows'],failed_HBT=len(row['failed_HBT']),
              observed_signal_passed=row['measurement']['signals']['diagnostic_signal_screen_passed'])),flush=True)
            del t,values
        result.update(disposition(result['cases']))
        assert pins()==locked and original.source_pins()==original_pins
        result['sources_and_captures_unchanged']=True
    except BaseException as exc:result.update(status='FAIL_READBACK_NO_CIRCUIT_ACCEPTANCE',error=repr(exc));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--readback',action='store_true')
    a=p.parse_args();assert a.controls!=a.readback
    controls()if a.controls else main()
