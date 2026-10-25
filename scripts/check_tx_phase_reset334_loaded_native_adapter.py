#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Count/transport-gate controls, not an electrical waveform substitute."""
import copy,json
import tx_phase_reset334_loaded_native_adapter as adapter
def reject(label,fn):
    try:fn()
    except(AssertionError,KeyError,ValueError,TypeError):return label
    raise AssertionError('Accepted '+label)
def controls():
    a=adapter.adapters();faults=[]
    # Test markers deliberately use synthetic names. Positive actual names/decks
    # must separately come from all four hash-pinned hosted preparation contracts.
    c={'hbt':{name+'.xd'+str(i):{} for name in ('xdut','xloadm','xloadq')for i in range(106)}}
    names=a.targets(c);assert len(names)==318
    block=a.flag_block(c,True)
    assert [r for r in block.splitlines()if r.startswith('alter ')]==['alter @'+n+'[off] = 1'for n in names]
    log=''.join('NSSOC_NATIVE_FLAG_BEGIN '+n+'\n  off 1\nNSSOC_NATIVE_FLAG_END\n'for n in names)
    assert a.flags(log,c,True)==dict(actual_HBT_targets=318,uniform_OFF_value=1,all_native_flags_read_back=True)
    for label,changed in [
      ('missing-native-target',log.split('NSSOC_NATIVE_FLAG_END\n',1)[1]),
      ('wrong-OFF-value',log.replace('off 1','off 0',1)),
      ('wrong-native-target',log.replace(names[0],'q.not_a_native_target',1)),
      ('duplicate-native-target',log+log.split('NSSOC_NATIVE_FLAG_END\n',1)[0]+'NSSOC_NATIVE_FLAG_END\n'),
      ('reordered-native-target',log.replace(names[0],'SWAP').replace(names[1],names[0]).replace('SWAP',names[1]))]:
        faults.append(reject(label,lambda:a.flags(changed,c,True)))
    for label,edit in [
      ('missing-HBT',lambda x:x['hbt'].pop(next(iter(x['hbt'])))),
      ('extra-HBT',lambda x:x['hbt'].update(extra={})),
      ('old106-HBT-census',lambda x:x.update(hbt={k:v for k,v in x['hbt'].items()if k.startswith('xdut.')}))]:
        changed=copy.deepcopy(c);edit(changed);faults.append(reject(label,lambda:a.targets(changed)))
    base='fixture\n.temp 27\n.tran .3125p 34n 0 .3125p\n.control\nop\nwrite op.raw all\nrun wave.raw\n.endc\n.end\n'
    initialized=a.initialized_deck(base,c);assert initialized.replace(block,'')==base
    op=a.op_only(base,c,True)
    assert '\nrun wave.raw\n'not in op and '.tran 'not in op
    assert op.replace(block,'')==base.replace('.tran .3125p 34n 0 .3125p\n','').replace('run wave.raw\n','')
    for label,bad in [
      ('preexisting-alter',base.replace('\nop\n','\nalter @q.x[nx] = 2\nop\n')),
      ('added-IC',base.replace('.temp 27','.ic v(x)=1\n.temp 27')),
      ('added-UIC',base.replace('.tran .3125p 34n 0 .3125p','.tran .3125p 34n 0 .3125p uic')),
      ('missing-transient',base.replace('run wave.raw\n',''))]:
        faults.append(reject(label,lambda:a.initialized_deck(bad,c)))
        reject(label+'-OP-only',lambda:a.op_only(bad,c,True))
    for p in adapter.PINS:
        sources={q:(adapter.ROOT/q).read_text()for q in adapter.PINS};sources[p]+='\n'
        faults.append(reject('changed-frozen-source-'+p,lambda:adapter.derive(sources)))
    good=dict(returncode=0,diagnostics=[],solver={'status':'PASS_NATIVE_SOLVER_OPTION_READBACK'},
      flags=dict(actual_HBT_targets=318,uniform_OFF_value=1,all_native_flags_read_back=True),
      zero_source_op=dict(columns=4726,all_saved_electrical_and_thermal_states_zero=True),
      capture=dict(columns=4727,complete_unmodified_rows=True),
      measurement=dict(diagnostic_screen_passed=True,all318_HBT_safety_passed=True,
        all_three_fixed_phase_screens_passed=True,hbt_safety={str(i):{}for i in range(318)},
        three_model_screens={n:{}for n in ('xdut','xloadm','xloadq')}),errors=[])
    assert adapter.check_gate(good)['passed']
    duplicate=copy.deepcopy(good);duplicate['zero_source_op']['columns']=4727
    assert adapter.check_gate(duplicate)['passed']
    mutations=[
      ('native-failure',lambda r:r.update(returncode=1)),
      ('numerical-diagnostic',lambda r:r.update(diagnostics=['gmin stepping'])),
      ('missing-solver-proof',lambda r:r.update(solver={})),
      ('old106-flags',lambda r:r['flags'].update(actual_HBT_targets=106)),
      ('missing-flag-readback',lambda r:r['flags'].update(all_native_flags_read_back=False)),
      ('wrong-OFF-gate',lambda r:r['flags'].update(uniform_OFF_value=0)),
      ('nonzero-OP',lambda r:r['zero_source_op'].update(all_saved_electrical_and_thermal_states_zero=False)),
      ('old358-OP-columns',lambda r:r['zero_source_op'].update(columns=358)),
      ('missing-full-capture',lambda r:r['capture'].update(complete_unmodified_rows=False)),
      ('wrong-raw-columns',lambda r:r['capture'].update(columns=4726)),
      ('rejected-measurement',lambda r:r['measurement'].update(diagnostic_screen_passed=False)),
      ('failed-one-HBT',lambda r:r['measurement'].update(all318_HBT_safety_passed=False)),
      ('failed-child-phase',lambda r:r['measurement'].update(all_three_fixed_phase_screens_passed=False)),
      ('missing-HBT-screen',lambda r:r['measurement']['hbt_safety'].pop('0')),
      ('missing-child-screen',lambda r:r['measurement']['three_model_screens'].pop('xloadm')),
      ('prior-validation-error',lambda r:r.update(errors=['retained failure']))]
    for label,edit in mutations:
        bad=copy.deepcopy(good);edit(bad);assert not adapter.check_gate(bad)['passed'],label;faults.append(label)
    assert len(faults)==30
    return dict(status='PASS_SOURCE_ONLY318_INITIALIZATION_AND_GATE_CONTROLS',
      source_derivations=a.source_proof,negative_controls=faults,
      synthetic_marker_fixture_only=True,actual_prepared_contracts_exercised=False,
      native_simulator_executed=False,electrical_accepted=False,all31_clock_tree_accepted=False,
      PLL_connected=False,full_PHY_accepted=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
