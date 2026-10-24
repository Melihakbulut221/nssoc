#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce244 rejection and inspect exact saved reset path; no native simulator."""
import argparse,contextlib,copy,io,json,os,re
from pathlib import Path
import numpy as np
import cloud_tx_phase_fast_assert_intrinsic as candidate
import cloud_tx_phase_rejected_capture_readback as prior_reader
import compare_cloud_routed_endpoints as restore
from cloud_tx_stream import read_streamed_wave
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-fast-assert-readback'
METHOD=ROOT/'scripts/tx-phase-fast-assert-readback-methods.json'
RUN=40098170615
HEAD='324b7b477b8b282099eb79d6d72b3f8bf87ca806'
SUMMARY='3ad8114c2f3a0f84fd7eb986b0846b98ad0027e977ba62737a019e2c3e28d9fa'
PARTS='8bc93457501ac935c8c19f7c46d7e90cc2a30fab566970b8c9dd67e4ff13ec70'
CASES=prior_reader.CASES
bench=candidate.bench
sha=candidate.original.sha
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    candidate.pins();prior_reader.pins()
    return m
def rejected(d):
    assert int(d['run_id'])==RUN and d['source_head']==HEAD
    assert d['status']=='REJECTED_FAST_ASSERT244_PRESERVE_COMPLETE_FAILURE_EVIDENCE'
    assert not d['all_four_diagnostic_screens_passed']and d['sources_and_models_unchanged']
    assert set(d['native_cases'])==set(CASES)
    assert all(d[k]is False for k in ('original241_transient_accepted','layout_RC_included','reset_hardware_qualified','all31_clock_tree_accepted','PLL_connected','full_PHY_accepted'))
    assert d['runtime_and_models']['engine_sha256']==candidate.original.ENGINE_SHA
    for label,row in d['native_cases'].items():
        assert row['complete']and row['returncode']==0 and row['errors']==[]and row['diagnostics']==[]
        assert row['primitive_count']==244 and row['hbt_count']==106 and row['vector_count']==358
        assert row['capture']['complete_unmodified_rows']and row['capture']['columns']==359
        assert row['acceptance_gate']==candidate.gate(row)
        assert row['diagnostic_screen_passed']==row['acceptance_gate']['passed']==(label=='p-initial-high')
        assert row['measurement']['all106_HBT_safety_passed']and len(row['measurement']['hbt_safety'])==106
    return True
def verify_case(source,label,folder,bound,receipt):
    old=source['native_cases'][label];sign,high=CASES[label]
    text=(folder/'candidate.spice').read_text();deck=(folder/'bench.cir').read_text();c=json.loads((folder/'contract.json').read_text())
    assert sha(folder/'candidate.spice')==old['source_sha256']==bench.SOURCE_SHA
    assert sha(folder/'bench.cir')==old['deck_sha256']and sha(folder/'contract.json')==old['contract_sha256']
    inc=re.findall(r'(?m)^\.include "([^"]+)"$',deck)
    libs=re.findall(r'(?m)^\.lib "([^"]+)" (hbt_typ|res_typ|cap_typ)$',deck)
    osdi=re.findall(r'(?m)^pre_osdi (\S+)$',deck)
    assert len(inc)==1 and len(libs)==3 and len(osdi)==1
    parents={str(Path(p).parent)for p,_ in libs};assert len(parents)==1
    base,expected=bench.prepare(text,bound,sign,high,inc[0],next(iter(parents)),osdi[0])
    built=candidate.initialized_deck(base,expected)
    expected.update(base_prepared_deck_sha256=expected['deck_sha256'],deck_sha256=bench.digest(built),
      initialization=dict(uniform_all106_native_OFF=1,selected_differential_phase=False,IC_or_UIC=False,prerequisite=receipt))
    assert deck==built and c==expected,'Original immutable244 deck/contract not reproduced'
    log=(folder/'native.log').read_text()
    assert sha(folder/'native.log')==old['native_log_sha256']==source['outputs'][label+'/native.log']
    assert candidate.original.verify_solver_options(log,bench.PROFILE)==old['solver']
    assert candidate.original.native_diagnostics(log,bench.PROFILE)==old['diagnostics']==[]
    assert candidate.initialization.flags(log,c,True)==old['flags']
    assert candidate.original.zero_op(folder/'op.raw',c['vectors'])==old['zero_source_op']
    return c
def diagnostic(t,values,c):
    def v(n):return np.zeros_like(t)if n=='0'else values['v('+n+')']
    pairs={k:v(p)-v(n)for k,p,n in [
      ('ARM','armp','armn'),('release','xdut.releasedp','xdut.releasedn'),
      ('run_base','xdut.xrun.bip','xdut.xrun.bin'),('run','xdut.runp','xdut.runn'),
      ('master_data','xdut.xm.data_p','xdut.xm.data_n'),('master_hold','xdut.xm.hold_p','xdut.xm.hold_n'),
      ('slave_data','xdut.xs.data_p','xdut.xs.data_n'),('slave_hold','xdut.xs.hold_p','xdut.xs.hold_n'),
      ('MP','mp','mn'),('QP','qp','qn'),('clock','clkp','clkn'),('conditioned_clock','xdut.ckp','xdut.ckn')]}
    requested=bench.RESET_ASSERT+np.array([-25,0,5,10,15,20,25,31.25,35,40,50,62.5,125])*1e-12
    def bracket(time):
        i=int(np.searchsorted(t,time,side='right'))-1
        assert 0<=i<len(t)-1 and t[i]<=time<=t[i+1]
        return dict(before_row=i,after_row=i+1,before_time_s=float(t[i]),after_time_s=float(t[i+1]))
    samples=[dict(time_s=float(time),native_bracket=bracket(time),
      differential_v={k:float(np.interp(time,t,y))for k,y in pairs.items()},
      fanin_bases_v={k:float(np.interp(time,t,v('xdut.xrun.'+k)))for k in ('bip','bin')},
      external_current_a={k:float(np.interp(time,t,values['i(v'+k+')']))for k in ('armp','armn','clkp','clkn','rail')})for time in requested]
    fixed=bench.START+(np.arange(256)+.5)*bench.UI;failures={}
    for k in ('MP','QP','release'):
        desired=2*bench.at_events(fixed,c['oracle']['events'],k)-1
        measured=np.interp(fixed,t,pairs[k]);margin=measured*desired
        failures[k]=[dict(index=int(i),time_s=float(fixed[i]),expected_sign=int(desired[i]),
          differential_v=float(measured[i]),signed_margin_v=float(margin[i]),native_bracket=bracket(fixed[i]))for i in np.flatnonzero(margin<bench.LIMITS['min_sign_margin_v'])]
    window=(t>=bench.RESET_ASSERT-bench.UI)&(t<=bench.RESET_ASSERT+2*bench.UI)
    transitions={}
    for k,y in pairs.items():
        transitions[k]={str(th):dict(rising_s=[float(q)for q in bench.crossings(t,y-th)if bench.RESET_ASSERT-bench.UI<=q<=bench.RESET_ASSERT+2*bench.UI],
          falling_s=[float(q)for q in bench.crossings(t,y-th,False)if bench.RESET_ASSERT-bench.UI<=q<=bench.RESET_ASSERT+2*bench.UI])for th in (-.1,0.,.1)}
    active=t>=bench.START
    currents={k:dict(minimum_a=float(values['i(v'+k+')'].min()),maximum_a=float(values['i(v'+k+')'].max()),
      mean_post_START_a=float(np.trapezoid(values['i(v'+k+')'][active],t[active])/(t[active][-1]-t[active][0])))for k in ('armp','armn','clkp','clkn','rail')}
    return dict(original_fixed_UI_margin_failures=failures,predeclared_reset_samples=samples,reset_window_threshold_crossings=transitions,
      external_source_currents=currents,sample_method='Original np.interp within explicitly recorded adjacent actual native samples; no phase/event fitting. Full original waveform and acceptance reproduction are separate strict prerequisites.',
      acceptance_changed=False,full_PHY_accepted=False)
def controls():
    locked=pins();saved=io.StringIO()
    with contextlib.redirect_stdout(saved):prior_reader.controls()
    old=json.loads(saved.getvalue());assert len(old['negative_controls'])==13
    d=json.loads(candidate.asset(672365442,SUMMARY));assert rejected(d);bad=[]
    for name,mut in [
      ('accept_rejected',lambda x:x.update(all_four_diagnostic_screens_passed=True)),
      ('wrong_source',lambda x:x.update(source_head='0'*40)),
      ('missing_case',lambda x:x['native_cases'].pop('n-initial-low')),
      ('missing_column',lambda x:x['native_cases']['n-initial-low']['capture'].update(columns=358)),
      ('hidden_diagnostic',lambda x:x['native_cases']['n-initial-low'].update(diagnostics=['warning'])),
      ('changed_gate',lambda x:x['native_cases']['n-initial-low']['acceptance_gate'].update(passed=True)),
      ('missing_HBT',lambda x:x['native_cases']['n-initial-low']['measurement']['hbt_safety'].pop(next(iter(x['native_cases']['n-initial-low']['measurement']['hbt_safety'])))),
      ('PHY_claim',lambda x:x.update(full_PHY_accepted=True))]:
        changed=copy.deepcopy(d);mut(changed)
        try:rejected(changed)
        except (AssertionError,KeyError,ValueError):bad.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(bad)==8 and pins()==locked
    print(json.dumps(dict(status='PASS244_EXACT_REJECTED_READBACK_CONTROLS_NO_SIMULATOR',prior_transport_and_archive_controls=old,
      exact_new_summary_faults=bad,native_execution=False,original244_accepted=False),indent=2))
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    locked=pins();OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING244_RESET_PATH_READBACK',run_id=os.environ['GITHUB_RUN_ID'],source_head=os.environ['GITHUB_SHA'],source_run=RUN,
      source_native_head=HEAD,cases={},original244_accepted=False,native_execution=False,layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        restore.OUT=ROOT/'hw/soc/out/phase-fast-readback-inputs';restore.OUT.mkdir(exist_ok=False)
        folder=restore.OUT/'captures'
        names=['pll-observer.summary.json']+[label+'/'+n for label in CASES for n in ('wave.raw','op.raw','candidate.spice','bench.cir','contract.json','native.log')]
        source,proof=restore.restore_report('tx-phase-fast-assert-intrinsic',RUN,SUMMARY,PARTS,folder,names)
        rejected(source);assert source['protected']==candidate.pins()['protected']
        receipt,_,_=candidate.prerequisite();assert receipt==source['zero_op_prerequisite']
        bound=bench.boundary((folder/'pll-observer.summary.json').read_bytes());assert bound==source['boundary']
        r.update(source_restoration=proof,original_rejection_status=source['status'],boundary=bound);save()
        for label in CASES:
            case=folder/label;c=verify_case(source,label,case,bound,receipt);old=source['native_cases'][label]
            t,values,capture=read_streamed_wave(case/'wave.raw',c['vectors'],bench.STOP,bench.STEP)
            assert capture==old['capture']and capture['raw_sha256']==source['outputs'][label+'/wave.raw']
            measurement=bench.review(t,values,c);assert measurement==old['measurement'],'Original full phase/safety report changed'
            row=dict(capture=capture,measurement=measurement,original_case_passed=old['diagnostic_screen_passed'],
              original_case_gate=old['acceptance_gate'],exact_original_report_reproduced=True,diagnostic=diagnostic(t,values,c))
            for n in ('wave.raw','op.raw','candidate.spice','bench.cir','contract.json','native.log'):assert sha(case/n)==source['outputs'][label+'/'+n]
            r['cases'][label]=row;save();print(json.dumps(dict(case=label,original_case_passed=row['original_case_passed'],exact_original_report_reproduced=True)),flush=True)
            del t,values
        assert len(r['cases'])==4 and sum(x['original_case_passed']for x in r['cases'].values())==1 and pins()==locked
        r.update(status='PASS_EXACT244_RESET_PATH_READBACK_ORIGINAL_THREE_CASE_REJECTION_REMAINS',sources_and_captures_unchanged=True)
    except BaseException as exc:r.update(status='FAIL_READBACK_NO_ACCEPTANCE',error=repr(exc));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--readback',action='store_true');a=p.parse_args()
    assert a.controls!=a.readback and os.environ.get('GITHUB_ACTIONS')=='true'
    controls()if a.controls else main()
