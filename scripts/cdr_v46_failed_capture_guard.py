#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read only the pinned complete v46 captures after a known postprocessing error."""
import copy,json
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
def gate(prior,case,variant):
    assert prior['source_head']=='aabb2abc5d427b5b81fcf80edf6f59e24f51790f'
    assert prior['status']=='FAIL_OR_ERROR' and prior['error']=="FileNotFoundError(2, 'No such file or directory')"
    assert "v41-n8-early-native-diagnosis.json" in prior['traceback'] and "clock_response" in prior['traceback']
    assert 'sources_unchanged' not in prior,'Do not invent or silently accept a different source end-state'
    assert prior['case']==case and prior['intrinsic_screen']['variant']==variant
    assert prior['returncode']==0 and not prior['diagnostics'] and prior['native_flags_verified']==120
    assert not prior['data_passed'] and not prior['phase_passed'] and not prior['accepted'] and not prior['full_phy_accepted']
    capture=prior['raw_capture']
    assert capture['header_rows']==113475 and capture['columns']==1104
    assert capture['start_s']==0 and abs(capture['end_s']-34.25e-9)<1e-20
    assert capture['max_step_s']<=.3125e-12+1e-23
    checks=prior['source_preflights']
    assert len(checks)==2
    for q in checks:
        assert q['status']=='PASS_EVERY_DISTINCT_READ_ONLY_SOURCE_VALIDATOR_ON_IMMUTABLE_INPUTS'
        assert q['every_distinct_validator_executed'] and q['all_read_files_unchanged'] and q['read_only_guard_enabled']
        assert not q['native_started'] and not q['full_phy_accepted']
    assert checks[0]['protected_read_files']==checks[1]['protected_read_files']
    return dict(original_status=prior['status'],original_error=prior['error'],
        original_source_end_assertion_reached=False,original_failure_preserved=True,
        original_readonly_source_preflights=2,
        scope='Postprocessing of a complete rejected native record only. Missing original end-of-screen assertion remains disclosed; no original run is promoted.')
def protected_files(prior,case,variant):
    prefix='/home/runner/work/nssoc/nssoc/cloud-cdr-v46-intrinsic-screen-'+variant+'-'+case+'/'
    result={}
    for name,h in prior['protected_inputs'].items():
        if name.startswith(prefix):
            relative=name[len(prefix):]
            assert Path(relative).as_posix()==relative and '..' not in Path(relative).parts
            assert prior['outputs'][relative]==h,('Original protected/archive digest mismatch',relative)
            result[relative]=h
    assert 'native/bench.cir' in result and 'native/original-bench.cir' in result
    assert 'exploratory-'+variant+'.spice' in result and 'source/source/runtime/patched-ngspice' in result
    assert result
    return result
def verify(prior,pin,root,case,variant):
    proof=gate(prior,case,variant)
    wanted=protected_files(prior,case,variant)
    assert wanted==pin['archived_protected_inputs']
    assert all(sha(root/p)==h for p,h in wanted.items()),'Archived runtime input differs from original protected bytes'
    # Source code guard remains separate from native acceptance. Original
    # read-only preflights passed before AND after the failed screen.
    proof['archived_protected_input_hashes_verified']=wanted
    proof['controls']=controls(prior,case,variant)
    return proof
def controls(prior,case,variant):
    gate(prior,case,variant);protected_files(prior,case,variant)
    rejected=[]
    for fault in ['wrong_source','wrong_error','missing_trace','native_failure','incomplete_capture',
                  'changed_vectors','changed_source_preflight','invented_end_assertion','promoted_data','changed_archived_model']:
        p=copy.deepcopy(prior)
        if fault=='wrong_source':p['source_head']='0'*40
        elif fault=='wrong_error':p['error']='unrelated error'
        elif fault=='missing_trace':p['traceback']='unrelated stack'
        elif fault=='native_failure':p['returncode']=1
        elif fault=='incomplete_capture':p['raw_capture']['end_s']=20e-9
        elif fault=='changed_vectors':p['raw_capture']['columns']=1103
        elif fault=='changed_source_preflight':p['source_preflights'][1]['protected_read_files']['corruption']='0'*64
        elif fault=='invented_end_assertion':p['sources_unchanged']=True
        elif fault=='promoted_data':p['data_passed']=True
        else:p['outputs']['native/bench.cir']='0'*64
        try:gate(p,case,variant);protected_files(p,case,variant)
        except (AssertionError,KeyError):rejected.append(fault)
        else:raise AssertionError('Accepted changed failed capture: '+fault)
    return rejected
