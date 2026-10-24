#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guard fresh244 execution with actual prerequisite and unchanged original controls."""
import contextlib,copy,io,json,os
from pathlib import Path
import cloud_tx_phase_fast_assert_intrinsic as candidate
import check_tx_phase_fast_assert_preparation as preparation
import check_tx_phase_async_preset_intrinsic as original_controls
import cloud_tx_phase_zero_op_initialization as initialization
def recorded(fn):
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):fn()
    return json.loads(capture.getvalue())
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    locked=candidate.pins()
    original=recorded(original_controls.main)
    assert original['status']=='PASS_INTRINSIC241_PREPARATION_FIXED_OBSERVERS_AND_NATIVE_LOADER_CONTROLS_NO_DUT_TRANSIENT'
    assert len(original['full_raw_reader_controls'])==7 and len(original['zero_OP_reader_controls'])==8
    prepared=recorded(preparation.main);assert len(prepared['positive_cases'])==4 and len(prepared['negative_controls'])==8
    init=recorded(initialization.controls);assert len(init['negative_controls'])==11
    receipt,raw,_=candidate.prerequisite();d=json.loads(raw)
    run=candidate.api('actions/runs/'+str(candidate.OP_RUN))
    assert candidate.validate_op(d,run)==receipt
    failures=[]
    def fail(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):failures.append(label)
        else:raise AssertionError('Accepted '+label)
    for label,key,val in [('failed_run','conclusion','failure'),('wrong_source','head_sha','0'*40),('live_run','status','in_progress')]:
        altered={**run,key:val};fail(label,lambda:candidate.validate_op(d,altered))
    for label,fn in [
      ('missing_case',lambda a:a['cases'].pop('p-uniform-off1')),
      ('hidden_default_failure',lambda a:a['cases']['p-default-off0'].update(diagnostics=[])),
      ('uniform_diagnostic',lambda a:a['cases']['n-uniform-off1'].update(diagnostics=['warning'])),
      ('wrong_native_flag',lambda a:a['cases']['p-uniform-off1']['flags'].update(uniform_OFF_value=0)),
      ('incomplete_OP',lambda a:a['cases']['p-uniform-off1']['zero_source_op'].update(columns=354)),
      ('false_transient_acceptance',lambda a:a.update(original_native_transient_accepted=True))]:
        altered=copy.deepcopy(d);fn(altered);fail(label,lambda:candidate.validate_op(altered,run))
    _,bound=candidate.original.observer();text=(candidate.ROOT/candidate.bench.builder.OUTPUT).read_text()
    decks={}
    for sign in ('p','n'):
        for high in (True,False):
            base,c=candidate.bench.prepare(text,bound,sign,high,'candidate.spice','/models','/r3.osdi')
            body=candidate.initialized_deck(base,c)
            assert len(c['vectors'])==358 and len(c['hbt'])==106
            assert body.replace(initialization.flag_block(c,True),'')==base
            assert sum(l.startswith('alter ')for l in body.splitlines())==106
            decks[sign+'-'+str(high)]={'sha256':candidate.bench.digest(body),'vectors':358,'uniform_targets':106,'original_deck_recovered':True}
    fail('IC',lambda:candidate.initialized_deck(base.replace('.temp 27','.ic v(mp)=1\n.temp 27'),c))
    fail('UIC',lambda:candidate.initialized_deck(base.replace('.control','* uic\n.control'),c))
    fail('preexisting_alter',lambda:candidate.initialized_deck(base.replace('\nop\n','\nalter @q.fake[nx] = 4\nop\n'),c))
    # Successful process or good waveform alone must never erase a rejected
    # numerical/initialization/capture/phase/safety screen.
    good=dict(returncode=0,diagnostics=[],solver={'status':'PASS_NATIVE_SOLVER_OPTION_READBACK'},
      flags=dict(actual_HBT_targets=106,uniform_OFF_value=1,all_native_flags_read_back=True),
      zero_source_op=dict(all_saved_electrical_and_thermal_states_zero=True,columns=358),
      capture={'complete_unmodified_rows':True},measurement={'diagnostic_screen_passed':True},errors=[])
    assert candidate.gate(good)['passed']
    gate_faults=[]
    for label,key,value in [('process','returncode',1),('numerical','diagnostics',['temperature NaN']),
      ('missing_diagnostics','diagnostics',None),('solver','solver',{}),('flags','flags',{}),
      ('OP','zero_source_op',{}),('capture','capture',{}),('phase_or_safety','measurement',{'diagnostic_screen_passed':False}),
      ('earlier_error','errors',[{'stage':'native','error':'bad'}]),('missing_errors','errors',None)]:
        bad={**good,key:value};assert not candidate.gate(bad)['passed'];gate_faults.append(label)
    assert len(failures)==12 and len(gate_faults)==10 and candidate.pins()==locked
    print(json.dumps(dict(status='PASS_FAST_ASSERT244_FRESH_NATIVE_CONTROLLER_CONTROLS_NO_DUT_TRANSIENT',
      exact_original_zero_OP_prerequisite=receipt,original_loader_and_reader_controls=original,
      unchanged_original_phase_and_safety_preparation=prepared,all106_flag_controls=init,
      four_uniform_decks=decks,prerequisite_and_deck_faults=failures,acceptance_gate_faults=gate_faults,
      native_program_scope='Original one-resistor loader controls only; no244 DUT transient',
      fast_assert244_DUT_executed=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
