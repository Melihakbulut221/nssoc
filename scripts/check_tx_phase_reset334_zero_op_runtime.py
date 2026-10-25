#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only gate controls and optional actual prepared-deck path tests."""
import copy,json
import tx_phase_reset334_zero_op_runtime as runtime
def reject(label,fn):
    try:fn()
    except(AssertionError,KeyError,ValueError,TypeError):return label
    raise AssertionError('Accepted '+label)
def controls():
    good=dict(returncode=0,diagnostics=[],solver=dict(status='PASS_NATIVE_SOLVER_OPTION_READBACK'),
      flags=dict(actual_HBT_targets=318,uniform_OFF_value=1,all_native_flags_read_back=True),
      zero_source_op=dict(rows=1,columns=4726,all_saved_electrical_and_thermal_states_zero=True),
      wave_raw_exists=False,source_and_runtime_unchanged=True,errors=[])
    assert runtime.gate(good)['passed']
    duplicate=copy.deepcopy(good);duplicate['zero_source_op']['columns']=4727
    assert runtime.gate(duplicate)['passed']
    mutations=[
      ('native-nonzero-return',lambda r:r.update(returncode=1)),
      ('numerical-diagnostic',lambda r:r.update(diagnostics=['gmin stepping'])),
      ('missing-solver',lambda r:r.update(solver={})),
      ('old106-targets',lambda r:r['flags'].update(actual_HBT_targets=106)),
      ('selective-OFF-value',lambda r:r['flags'].update(uniform_OFF_value=0)),
      ('missing-native-readback',lambda r:r['flags'].update(all_native_flags_read_back=False)),
      ('multiple-OP-rows',lambda r:r['zero_source_op'].update(rows=2)),
      ('old358-vector-set',lambda r:r['zero_source_op'].update(columns=358)),
      ('nonzero-OP-state',lambda r:r['zero_source_op'].update(all_saved_electrical_and_thermal_states_zero=False)),
      ('unexpected-transient-file',lambda r:r.update(wave_raw_exists=True)),
      ('changed-source-or-runtime',lambda r:r.update(source_and_runtime_unchanged=False)),
      ('retained-validation-error',lambda r:r.update(errors=['original failure']))]
    rejected=[]
    for label,edit in mutations:
        bad=copy.deepcopy(good);edit(bad);assert not runtime.gate(bad)['passed'];rejected.append(label)
    assert len(rejected)==12
    return dict(status='PASS_SOURCE_ONLY_EXPANDED_ZERO_OP_GATE_LOGIC',negative_controls=rejected,
      actual_prepared_path_test_executed=False,native_executed=False,zero_OP_accepted=False,transient_accepted=False)
def positive_paths(cases,summary_raw,models):
    """Must run in hosted preparation with authenticated complete cases/models."""
    assert set(cases)=={s+'-initial-'+h for s in ('p','n')for h in ('high','low')}
    paths={'p':'/qualified/native/p.spice','n':'/qualified/native/n.spice'}
    positives={};faults=[]
    for label,(deck,contract)in cases.items():
        kwargs=dict(label=label,prepared_deck=deck,contract=contract,summary_raw=summary_raw,
          models=models,model_paths=paths,model_directory='/qualified/model-library',osdi='/qualified/r3_cmc.osdi')
        op,proof=runtime.runtime_deck(**kwargs)
        assert len(proof['six_path_cards'])==6 and proof['byte_exact_reversal']
        assert '.tran 'not in op and '\nrun 'not in op and op.count('\nop\n')==1
        assert proof['uniform_all318_OFF']==1 and not proof['transient_allowed']
        positives[label]=proof
        for kind,edit in [
          ('changed-model-P',lambda d:d['models'].update(p=d['models']['p']+'\n')),
          ('missing-model-N',lambda d:d['models'].pop('n')),
          ('aliased-model-paths',lambda d:d['model_paths'].update(n=d['model_paths']['p'])),
          ('OSDI-newline',lambda d:d.update(osdi='/qualified/bad\npath')),
          ('OSDI-whitespace',lambda d:d.update(osdi='/qualified/bad path')),
          ('quoted-model-path',lambda d:d['model_paths'].update(p='/qualified/bad"path')),
          ('changed-prepared-deck',lambda d:d.update(prepared_deck=d['prepared_deck']+'\n')),
          ('changed-prepared-contract',lambda d:d['contract'].update(hbt_count=106))]:
            bad=copy.deepcopy(kwargs);edit(bad);faults.append(reject(label+':'+kind,lambda:runtime.runtime_deck(**bad)))
    assert len(positives)==4 and len(faults)==32
    return dict(status='PASS_FOUR_EXACT_PREPARED_RUNTIME_PATH_TRANSFORMS_NOT_NATIVE',positive_cases=positives,
      negative_controls=faults,actual_prepared_path_test_executed=True,native_executed=False,
      runtime_installed=False,zero_OP_accepted=False,transient_accepted=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
