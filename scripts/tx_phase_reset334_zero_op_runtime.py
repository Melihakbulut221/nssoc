#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only runtime-path binding and expanded zero-OP gate; no engine invocation."""
import re
from pathlib import Path
import tx_phase_reset334_loaded_native_adapter as initialization
import tx_phase_reset334_loaded_contract as bench
def runtime_deck(label,prepared_deck,contract,summary_raw,models,model_paths,model_directory,osdi):
    """Only six exact .lib/.include/pre_osdi card replacements before uniform OFF."""
    initialization.prepared_contract(label,prepared_deck,contract,summary_raw)
    bench.validate_paths(model_paths,model_directory,osdi)
    assert set(models)==set(model_paths)=={'p','n'}
    for sign in ('p','n'):assert bench.digest(models[sign])==bench.binding.MODELS[sign]
    old=prepared_deck.splitlines(keepends=True);records=[]
    libs=[(i,r)for i,r in enumerate(old)if r.startswith('.lib ')]
    incs=[(i,r)for i,r in enumerate(old)if r.startswith('.include ')]
    osdis=[(i,r)for i,r in enumerate(old)if r.startswith('pre_osdi ')]
    assert len(libs)==3 and len(incs)==2 and len(osdis)==1
    replacement=old.copy()
    for (i,line),(kind,corner) in zip(libs,[('HBT','hbt_typ'),('RES','res_typ'),('CAP','cap_typ')],strict=True):
        assert line=='.lib "/fixture/sg13g2-ngspice-models/corner'+kind+'.lib" '+corner+'\n'
        value='.lib "'+str(Path(model_directory)/('corner'+kind+'.lib'))+'" '+corner+'\n'
        replacement[i]=value;records.append(dict(line=i,old=line,new=value,role=kind))
    for (i,line),sign in zip(incs,('p','n'),strict=True):
        match=re.fullmatch(r'\.include "([^"\r\n]+)"\n',line);assert match
        assert match[1].endswith('/qualified-binding/qualified-rc/'+sign+'/composition/reset334-wire.spice')
        value='.include "'+str(model_paths[sign])+'"\n'
        replacement[i]=value;records.append(dict(line=i,old=line,new=value,role='model-'+sign,sha256=bench.binding.MODELS[sign]))
    i,line=osdis[0];assert line=='pre_osdi /fixture/r3_cmc.osdi\n'
    value='pre_osdi '+str(osdi)+'\n';replacement[i]=value;records.append(dict(line=i,old=line,new=value,role='OSDI'))
    assert len(records)==6 and len({r['line']for r in records})==6
    result=''.join(replacement);rev=replacement.copy()
    for r in records:assert rev[r['line']]==r['new'];rev[r['line']]=r['old']
    assert ''.join(rev)==prepared_deck
    assert [r for r in replacement if r.startswith('V')]==[r for r in old if r.startswith('V')]
    assert [r for r in replacement if r.startswith('save ')]==[r for r in old if r.startswith('save ')]
    assert [r for r in replacement if r.startswith(('xdut ','xloadm ','xloadq '))]==[r for r in old if r.startswith(('xdut ','xloadm ','xloadq '))]
    a=initialization.adapters();op=a.op_only(result,contract,True)
    assert not re.search(r'(?im)^\s*(?:\.tran\b|run\b|resume\b|tran\b|\.ic\b|\.nodeset\b)|\buic\b',op)
    assert op.count('\nop\n')==1 and op.count('write op.raw all')==1
    assert len([r for r in op.splitlines()if r.startswith('alter ')])==318
    return op,dict(prepared_deck_sha256=bench.digest(prepared_deck),runtime_base_sha256=bench.digest(result),
      OP_deck_sha256=bench.digest(op),six_path_cards=records,byte_exact_reversal=True,
      original_source_and_save_cards_unchanged=True,uniform_all318_OFF=1,
      OP_only_deck=True,transient_allowed=False)
def gate(row):
    """Fresh native zero OP only. Never infer full transient or phase acceptance."""
    checks=dict(returncode_zero=row.get('returncode')==0,no_numerical_diagnostics=row.get('diagnostics')==[],
      solver_readback=row.get('solver',{}).get('status')=='PASS_NATIVE_SOLVER_OPTION_READBACK',
      all318_native_flags=row.get('flags')==dict(actual_HBT_targets=318,uniform_OFF_value=1,all_native_flags_read_back=True),
      one_full_zero_OP=row.get('zero_source_op',{}).get('rows')==1 and
        row.get('zero_source_op',{}).get('columns')in(4726,4727)and
        row.get('zero_source_op',{}).get('all_saved_electrical_and_thermal_states_zero')is True,
      no_transient_file=row.get('wave_raw_exists')is False,
      source_and_runtime_unchanged=row.get('source_and_runtime_unchanged')is True,
      no_validation_errors=row.get('errors')==[])
    return dict(checks=checks,passed=all(checks.values()),electrical_phase_accepted=False,
      transient_accepted=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
