#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only synthetic boundary fixtures; never claim synthetic ODB bytes are native proof."""
import copy,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
import mainchip_repaired_postroute_admission as a
import mainchip_repaired_postroute_bridge as bridge
from cloud_chunked_results import pack,verify_parts
def encoded(value):return (json.dumps(value,indent=2)+'\n').encode()
def fixture():
    files={name:b'synthetic boundary fixture; not a native object\n'for name in a.SELECTED}
    files['work/guide-loaded.odb']=b'synthetic guide object\n'
    files['unselected-preserved.txt']=b'complete inventory must still hash this\n'
    def put(name,value):files[name]=encoded(value)
    gate=dict(clock_or_fixed_nets=1691,all_source_clock_and_fixed_records_preserved=True)
    for name in ('work/original-gate-after-repair/result.json','work/original-gate-after-final-drc/result.json'):put(name,gate)
    marker=encoded({a.drc.CATEGORY:dict(description='Synthetic empty DRT fixture',source='DRT',max_markers='1000')})
    files['work/initial-drc-markers.json']=marker
    files['work/initial-drc.rpt']=files['work/initial-drc-reread.rpt']=b''
    census=a.drc.serialized_marker_tree(marker)
    measurement=dict(census,all_categories_below_native_cap=True,zero_reported_DRT_markers=True,
        full_signoff_DRC=False,report_bytes=0,report_sha256=a.digest(b''))
    measurement['serialized_markers']=a.drc.bind_serialized_markers(measurement,marker)
    delta=dict(changed_signal_count=1,changed_signal_names=['fixture_signal'],
        changed_signal_names_sha256='a'*64,other_records_byte_exact=True,non_NETS_bytes_exact=True,accepted=False)
    via=dict(union_count=1,definitions_present_and_identical_in_both_databases=True,newly_generated_via_definitions_not_admitted=True)
    expected=b'synthetic original-class DEF bytes\n'
    for name in ('work/expected-original-class.def','work/repaired-audit.def','work/drc-before.def',
                 'work/drc-after.def','work/measured-audit.def'):files[name]=expected
    prior=dict(status='PASS_ORIGINAL_CLASS_SIGNAL_REPAIR_REQUIRES_COMPLETE_DRC',
        candidate_sha256=a.digest(files[a.CANDIDATE]),original1691_clock_gate_passed=True,native_invariants_passed=True,
        routing_delta=delta,via_proof=via,native_geometry=dict(sha256='b'*64,counts=dict(net=143820,instance=153130)),
        expected_def_sha256=a.digest(expected),
        original_gate=dict(result=gate,sha256=a.digest(files['work/original-gate-after-repair/result.json'])))
    put('work/unfix-audit-result.json',prior)
    final=dict(status='COMPLETE_SIGNAL_REPAIR_AND_ORIGINAL_CLASS_DRC_NOT_TIMING_OR_PHY_ACCEPTANCE',
        original1691_clock_gate_passed=True,native_invariants_passed=True,routing_delta=delta,final_DRT=measurement,
        original_gate=dict(result=gate,sha256=a.digest(files['work/original-gate-after-final-drc/result.json'])))
    final['next_stage']=a.repair.continuation_gate(final);put('work/drc-audit-result.json',final)
    put('work/prepare-result.json',dict(status='PREPARED_FIXED_CLOCK_SIGNAL_REPAIR',selected=1691,
        timing_contract=dict(clock_periods_ns=[20,4,8,8],derating_percent=5,new_RC_STA_required=True,accepted=False)))
    put('work/guide-audit-result.json',dict(status='PASS_EXACT_GUIDE_LOAD_BEFORE_ROUTING',
        guide_loaded_odb_sha256=a.digest(files['work/guide-loaded.odb']),
        guide_proof=dict(guides=10,in_range_guides=9,sha256='c'*64)))
    put('work/route-audit-result.json',dict(status='PASS_SIGNAL_ONLY_DELTA_WITH_CLOCKS_ENCODED_FIXED',
        native_invariants_passed=True,routing_delta=delta,via_proof=via))
    source=dict(complete_clock_archive_verified=True,clock_inputs=a.repair.CLOCK_INPUTS,global_inputs=a.repair.GLOBAL_INPUTS)
    put('source-admission.json',source)
    phases=[]
    for label in a.PHASES:
        record=dict(label=label,returncode=0,supervision_failure=None,process_group_cleanup=dict(remaining_live=[]))
        put('supervision/'+label+'.command.json',record)
        phases.append(dict(record,requested_timeout_seconds=14400 if label=='one-signal-routing-attempt'else 1200))
    r=dict(run_id=a.SPEC['run'],run_attempt=1,source_head=a.SPEC['source_head'],
        status='COMPLETE_BOUNDED_SIGNAL_REPAIR_NOT_RC_STA_OR_PHY_ACCEPTANCE',
        accepted=False,final_timing_complete=False,full_phy_accepted=False,automatic_retry=False,
        original_inputs_unchanged=True,native_routing_started=True,runtime_appimage_sha256=a.APP,
        phase_results=phases,native_result=final,next_stage=final['next_stage'],source_admission=source)
    return files,r
def bind(files,r):
    r['outputs']={n:a.digest(b)for n,b in files.items()if n!='result.json'}
    files['result.json']=encoded(r)
    inventory={n:dict(bytes=len(b),sha256=a.digest(b))for n,b in files.items()}
    pin=dict(summary=dict(bytes=len(files['result.json']),sha256=a.digest(files['result.json'])),
        parts=dict(bytes=1,sha256='d'*64),archive=dict(bytes=1,sha256='e'*64),assets=[],
        file_count=len(files),total_unpacked_bytes=sum(len(b)for b in files.values()),
        candidate_sha256=a.digest(files[a.CANDIDATE]))
    proof=dict(all_original_files=inventory,total_unpacked_bytes=pin['total_unpacked_bytes'],
        complete_original_inventory_verified_before_analysis=True,selected_files={n:inventory[n]for n in a.SELECTED})
    return pin,proof
def write(root,files):
    for name,raw in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
def change_json(files,name,change):
    value=json.loads(files[name]);change(value);files[name]=encoded(value)
def reject(label,call):
    try:call()
    except AssertionError:return label
    raise AssertionError('Boundary fault accepted: '+label)
def controls():
    positives=[];refusals=[]
    files,r=fixture();pin,proof=bind(files,r)
    assert a.summary(files['result.json'],pin)==r;positives.append('zero_summary')
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)/'selected';root.mkdir();write(root,files)
        admitted=a.restored(r,root,proof,pin)
        assert admitted['final_original_class_DRT_markers']==0 and admitted['candidate_sha256']==pin['candidate_sha256']
        assert admitted['input_package']==a.INPUT_PACKAGE;positives.append('actual_restored_boundary')
    def summary_case(change):
        files,r=fixture();change(r);pin,_=bind(files,r)
        a.summary(files['result.json'],pin)
    summary_faults=[
        ('wrong_run',lambda r:r.update(run_id=1)),
        ('rerun_attempt',lambda r:r.update(run_attempt=2)),
        ('wrong_source',lambda r:r.update(source_head='0'*40)),
        ('failed_status',lambda r:r.update(status='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR')),
        ('acceptance_claim',lambda r:r.update(accepted=True)),
        ('no_native_route',lambda r:r.update(native_routing_started=False)),
        ('changed_inputs',lambda r:r.update(original_inputs_unchanged=False)),
        ('changed_runtime',lambda r:r.update(runtime_appimage_sha256='0'*64)),
        ('missing_phase',lambda r:r['phase_results'].pop()),
        ('wrong_phase_order',lambda r:r['phase_results'].reverse()),
        ('failed_phase',lambda r:r['phase_results'][0].update(returncode=1)),
        ('surviving_process',lambda r:r['phase_results'][0]['process_group_cleanup'].update(remaining_live=[123])),
        ('changed_budget',lambda r:r['phase_results'][6].update(requested_timeout_seconds=1200)),
        ('bool_marker_count',lambda r:r['native_result']['final_DRT'].update(marker_count=False)),
        ('clock_gate_false',lambda r:r['native_result'].update(original1691_clock_gate_passed=False)),
        ('nonmarker_invariants_false',lambda r:r['native_result'].update(native_invariants_passed=False)),
        ('protected_record_changed',lambda r:r['native_result']['routing_delta'].update(other_records_byte_exact=False)),
        ('uncapped_claim_false',lambda r:r['native_result']['final_DRT'].update(all_categories_below_native_cap=False)),
        ('serialized_census_false',lambda r:r['native_result']['final_DRT']['serialized_markers'].update(complete_native_category_census_equal=False))]
    for label,change in summary_faults:refusals.append(reject(label,lambda change=change:summary_case(change)))
    def nonzero(r):
        x=r['native_result']['final_DRT'];x.update(marker_count=1,zero_reported_DRT_markers=False)
        x['serialized_markers']['marker_count']=1
        r['native_result']['next_stage']=r['next_stage']=a.repair.continuation_gate(r['native_result'])
    refusals.append(reject('nonzero_not_eligible',lambda:summary_case(nonzero)))
    def restored_case(name,change):
        files,r=fixture();change_json(files,name,change);pin,proof=bind(files,r)
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);write(root,files);a.restored(r,root,proof,pin)
    payload_faults=[
        ('candidate_link', 'work/unfix-audit-result.json',lambda v:v.update(candidate_sha256='0'*64)),
        ('unfix_status', 'work/unfix-audit-result.json',lambda v:v.update(status='RUNNING')),
        ('unfix_gate', 'work/unfix-audit-result.json',lambda v:v.update(original1691_clock_gate_passed=False)),
        ('unfix_native_invariant', 'work/unfix-audit-result.json',lambda v:v.update(native_invariants_passed=False)),
        ('wrong_DEF_link', 'work/unfix-audit-result.json',lambda v:v.update(expected_def_sha256='0'*64)),
        ('used_via_changed','work/unfix-audit-result.json',lambda v:v['via_proof'].update(definitions_present_and_identical_in_both_databases=False)),
        ('wrong_net_census','work/unfix-audit-result.json',lambda v:v['native_geometry']['counts'].update(net=143819)),
        ('wrong_instance_census','work/unfix-audit-result.json',lambda v:v['native_geometry']['counts'].update(instance=153129)),
        ('different_final_json','work/drc-audit-result.json',lambda v:v.update(status='RUNNING')),
        ('wrong_original_gate','work/original-gate-after-repair/result.json',lambda v:v.update(clock_or_fixed_nets=1690)),
        ('wrong_final_gate','work/original-gate-after-final-drc/result.json',lambda v:v.update(all_source_clock_and_fixed_records_preserved=False)),
        ('changed_clock_period','work/prepare-result.json',lambda v:v['timing_contract'].update(clock_periods_ns=[10,4,8,8])),
        ('changed_derating','work/prepare-result.json',lambda v:v['timing_contract'].update(derating_percent=0)),
        ('missing_guides','work/guide-audit-result.json',lambda v:v['guide_proof'].update(guides=0,in_range_guides=0)),
        ('guide_object_link','work/guide-audit-result.json',lambda v:v.update(guide_loaded_odb_sha256='0'*64)),
        ('routing_status','work/route-audit-result.json',lambda v:v.update(status='RUNNING')),
        ('routing_delta','work/route-audit-result.json',lambda v:v['routing_delta'].update(other_records_byte_exact=False)),
        ('wrong_source_admission','source-admission.json',lambda v:v.update(complete_clock_archive_verified=False)),
        ('different_command_record','supervision/prepare.command.json',lambda v:v.update(returncode=1)),
        ('serialized_missing_category','work/initial-drc-markers.json',lambda v:v.clear())]
    for label,name,change in payload_faults:
        refusals.append(reject(label,lambda name=name,change=change:restored_case(name,change)))
    for name in ('work/repaired-audit.def','work/drc-before.def','work/drc-after.def','work/measured-audit.def','work/initial-drc.rpt'):
        def body_case(name=name):
            files,r=fixture();files[name]+=b'changed';pin,proof=bind(files,r)
            with tempfile.TemporaryDirectory()as tmp:
                root=Path(tmp);write(root,files);a.restored(r,root,proof,pin)
        refusals.append(reject('changed_'+name,body_case))
    for label,change in [
        ('incomplete_inventory',lambda p:p.update(complete_original_inventory_verified_before_analysis=False)),
        ('missing_unselected_member',lambda p:p['all_original_files'].pop('unselected-preserved.txt')),
        ('changed_unselected_digest',lambda p:p['all_original_files']['unselected-preserved.txt'].update(sha256='0'*64)),
        ('wrong_full_size',lambda p:p.update(total_unpacked_bytes=p['total_unpacked_bytes']+1)),
        ('wrong_selection',lambda p:p['selected_files'].pop(a.CANDIDATE))]:
        def inventory_case(change=change):
            files,r=fixture();pin,proof=bind(files,r);change(proof)
            with tempfile.TemporaryDirectory()as tmp:
                root=Path(tmp);write(root,files);a.restored(r,root,proof,pin)
        refusals.append(reject(label,inventory_case))
    # The real qualified packer and complete-inventory reader run only on hosted synthetic files.
    with tempfile.TemporaryDirectory()as tmp:
        base=Path(tmp);source=base/'cloud-mainchip-fixed-clock-signal-repair';source.mkdir()
        files,r=fixture();pin,_=bind(files,r);write(source,files)
        parts=pack(source,'synthetic-postroute-bridge',base,257)
        verify_parts(parts,base) # A transport defect cannot qualify the member fault below.
        expected={n:a.digest(raw)for n,raw in files.items()}
        inventory=a.audit_extract(parts,base,base/'selected',expected,a.SELECTED)
        assert a.restored(r,base/'selected',inventory,pin)['complete_original_inventory_verified']
        positives.append('actual_pack_complete_inventory_roundtrip')
        bad=dict(expected);bad['unselected-preserved.txt']='0'*64
        refusals.append(reject('unselected_file_hash_must_match',
            lambda:a.audit_extract(parts,base,base/'bad-selected',bad,a.SELECTED)))
    old=(a.ROOT/bridge.GEOMETRY).read_bytes();post=(a.ROOT/bridge.POSTROUTE).read_bytes()
    derived,exact,proof=bridge.derive(old,post)
    assert exact==post and proof['exact_reversible_edits']==2
    assert b'log_proof((OUT/'not in derived and b'b,aproof=consume(ROOT,OUT)'in derived
    positives.append('exact_reversible_derivation')
    refusals.append(reject('changed_original_geometry',lambda:bridge.derive(old+b'\n',post)))
    refusals.append(reject('changed_original_numerical_program',lambda:bridge.derive(old,post+b'\n')))
    with patch.dict(os.environ,{},clear=True):
        with bridge.original_input_context():
            assert json.loads(os.environ['NSSOC_INPUT_PACKAGE'])==a.INPUT_PACKAGE
            assert json.loads(os.environ['NSSOC_COMPLETED_DRT'])==a.SPEC
        assert not os.environ;positives.append('exact_input_context_restored')
    def wrong_context(key,value):
        with patch.dict(os.environ,{key:json.dumps(value)},clear=True):
            with bridge.original_input_context():raise RuntimeError('Wrong context reached body')
    refusals.append(reject('old_input_package_substitution',lambda:wrong_context('NSSOC_INPUT_PACKAGE',dict(a.INPUT_PACKAGE,run=1))))
    refusals.append(reject('old_completed_route_substitution',lambda:wrong_context('NSSOC_COMPLETED_DRT',dict(a.SPEC,run=1))))
    refusals.append(reject('missing_actual_terminal_binding',lambda:a.require_terminal_binding(dict(terminal_binding=None))))
    assert len(positives)==5 and len(refusals)==56,(len(positives),len(refusals))
    return dict(status='PASS_REPAIRED_POSTROUTE_BOUNDARY_FIXTURES_NOT_NATIVE',
        positives=positives,refusals=refusals,fixtures_are_synthetic=True,
        actual_repair_or_RC_STA_executed=False,full_phy_accepted=False)
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert a.methods()['source_controls_authorized']is True
    print(json.dumps(controls(),indent=2))
