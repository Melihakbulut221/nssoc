#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One sd3 identity delay in an existing vacancy, with immutable original objects."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import run_cloud_critical_followup as original

prior = original.prior
parent, shared, common, eco, targeted = original.parent, original.shared, original.common, original.eco, original.targeted
require = original.require
LOCK = 'hw/soc/pnr/timing-explicit-hold-input.lock.json'
ENTRY = 'scripts/run_cloud_explicit_hold.py'
HELPER = 'hw/soc/pnr/timing_explicit_hold_helpers.tcl'
STEP = 'hw/soc/pnr/timing_explicit_hold_step.tcl'
CHILD = 'hw/soc/pnr/timing_explicit_hold_reload.tcl'
FIXTURE = 'sw/tests/timing_explicit_hold_native.tcl'
OWN = (LOCK, ENTRY, HELPER, STEP, CHILD, FIXTURE, 'sw/tests/test_explicit_hold.py',
       '.github/workflows/timing-explicit-hold.yml')
SOURCES = tuple(dict.fromkeys(original.SOURCES + OWN))
STAGES = ('candidate_before', 'after_insertion', 'reload_first', 'reload_repeat')
BASE_WORKER = prior.worker
BASE_VALIDATE = prior.BASE_VALIDATE
BASE_ENVIRONMENT = shared.clean_environment
INSERTION = dict(driver='_135214_', driver_pin='Q', sink='_135215_', sink_pin='D',
    endpoint_master='sg13g2_dfrbpq_1', native_net='u_npu.u_node0.mosi_s[0]',
    verilog_net=r'\u_npu.u_node0.mosi_s [0]', buffer='nssoc_explicit_sd3',
    new_net='nssoc_explicit_holdnet', master='sg13g2_dlygate4sd3_1', radius_um=10)


def lock(root):
    row=json.loads((Path(root)/LOCK).read_text())
    require(row['schema']==1 and row['runtime_sha256']==targeted.RUNTIME_SHA
        and row['manifest_sha256']==eco.MANIFEST_SHA, 'Original runtime/manifest differs')
    require(row['producer']['run_id']==37102104480
        and row['producer']['source_commit']=='4882cfe2cf9c39123dcef4f0cef7edac4c1d80a1'
        and row['producer']['artifact_id']==11267076249
        and row['producer']['sha256']=='9f7e215fa0b43ff7552b1b8427f778b74022c7443adb3476c2c33acfc19e74ae',
        'Corrected final critical producer differs')
    require(row['insertion']==INSERTION, 'Explicit insertion contract differs')
    require(set(row['candidate_files'])==parent.VIEW_NAMES
        and set(row['frozen_method_pins'])==set(original.SOURCES), 'Original source/view closure differs')
    for name,pin in row['frozen_method_pins'].items(): common.verify_file(Path(root)/name,pin)
    require(set(row['historical_reference_metrics'])=={'selected_c10','matched_c10','combined_parent',
        'electrical_first','electrical_margin_parent','residual_parent'}, 'Historical reference omitted')
    require(row['producer_rejected_guard']['aggregate_estimate_guard_passed'] is False
        and row['producer_rejected_guard']['no_regression']['combined_parent'] is False
        and row['producer_rejected_guard']['candidate_adopted'] is False, 'Rejected parent context concealed')
    return row


def target_binding(netlist,placement,locked):
    common.verify_file(netlist,locked['candidate_files']['soc_top.v'])
    common.verify_file(placement,locked['source_placement_pin'])
    text=Path(netlist).read_text(); cells=original.logical_cell_census(text)
    require(text.count(locked['hold_target']['body'])==1, 'Exact source hold endpoint body differs')
    insertion=locked['insertion']; wanted={insertion['driver'],insertion['sink']}
    require(not any(name.startswith(insertion['buffer']) for name in cells), 'Insertion name exists in source')
    terms=[]
    for name,cell in cells.items():
        for pin,expr in cell['ports'].items():
            if expr==insertion['verilog_net']:terms.append([name,cell['master'],pin])
    expected=sorted([[insertion['driver'],insertion['endpoint_master'],'Q'],[insertion['sink'],insertion['endpoint_master'],'D']])
    require(sorted(terms)==expected, 'Source signal is not exact sole Q to D branch')
    for name in wanted:
        require(cells[name]['master']==insertion['endpoint_master']
            and set(cells[name]['ports'])=={'CLK','RESET_B','D','Q'}, 'Source DFF functional ports differ')
    with Path(placement).open() as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        require(reader.fieldnames==['instance','master','x_dbu','y_dbu','orientation','status'], 'Source placement census schema differs')
        rows=list(reader)
    require(len({r['instance'] for r in rows})==len(rows), 'Duplicate source placement instance')
    located={r['instance']:r for r in rows if r['instance'] in wanted}
    require(set(located)==wanted and all(r['master']==insertion['endpoint_master'] for r in located.values()), 'Source endpoint placement differs')
    return dict(insertion=insertion,terminals=expected,native_placement=located,
        functional_ports={k:cells[k]['ports'] for k in sorted(wanted)},
        netlist=locked['candidate_files']['soc_top.v'],placement=locked['source_placement_pin'])


def baseline_script(locked,binding):
    def atom(value):
        value=str(value)
        require(re.fullmatch(r'[A-Za-z0-9_./\[\]-]+',value), 'Unsafe bound Tcl atom')
        return '{'+value+'}'
    lines=['# Exact unadopted corrected sized parent; no historical guard is replaced.',
        'set nssoc_electrical_expected_metrics [dict create \\']
    lines += [f'    {k} {v!r} \\' for k,v in locked['baseline_metrics'].items()]
    lines += [']','set nssoc_electrical_expected_files [dict create \\']
    lines += [f'    {shared.FINGERPRINT_FILES[k]} {v} \\' for k,v in locked['baseline_fingerprints'].items()]
    lines += [']','set nssoc_explicit_places [dict create \\']
    for name,row in binding['native_placement'].items():
        lines.append('    '+atom(name)+' [list '+' '.join(atom(row[k]) for k in ('x_dbu','y_dbu','orientation','status'))+'] \\')
    lines += [']','set nssoc_explicit_net '+atom(binding['insertion']['native_net'])]
    return '\n'.join(lines+[''])


def validate_parent_contract(producer,locked):
    require(producer['status']=='COMPLETE_DIAGNOSTIC_ONLY'
        and producer['github_source_commit']==locked['producer']['source_commit']
        and producer['method_files']==locked['frozen_method_pins']
        and producer['diagnostic']['native']['candidate_files']==locked['candidate_files'], 'Corrected sized candidate provenance differs')
    prior.equal_metrics(producer['diagnostic']['native']['timing_metrics']['reload_repeat'],locked['baseline_metrics'])
    require(producer['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints']==locked['baseline_fingerprints'], 'Canonical source fingerprints differ')
    assessment=producer['diagnostic']['aggregate_guard_assessment']
    require(assessment==locked['producer_rejected_guard'], 'Original rejected guard result changed')
    require({k:v for k,v in assessment['reference_metrics'].items() if k!='candidate_before'}==locked['historical_reference_metrics'], 'Historical reference chain changed')


def download_producer(trial, archive):
    run = eco.github_json('actions/runs/'+str(trial['run_id']))
    require(run['id'] == trial['run_id'] and run['head_sha'] == trial['source_commit'] and run['status'] == 'completed'
        and run['conclusion'] == 'success' and run['run_attempt'] == 1
        and run['repository']['full_name'] == eco.REPOSITORY,
        'Original residual workflow identity differs')
    try:meta = eco.github_json('actions/artifacts/'+str(trial['artifact_id']))
    except subprocess.CalledProcessError:meta = None
    if meta is not None:
        require(meta['id'] == trial['artifact_id'] and meta['workflow_run']['id'] == trial['run_id']
            and meta['workflow_run']['head_sha'] == trial['source_commit'] and meta['name'] == trial['artifact_name']
            and meta['size_in_bytes'] == trial['bytes'] and meta['digest'] == 'sha256:'+trial['sha256'],
            'Available original artifact metadata differs')
    # The independently archived ZIP has the same exact bytes. Artifact expiry
    # does not invalidate it; the run and every embedded Git source remain checked.
    common.download(trial,archive)
    return dict(run=run,artifact=meta,artifact_metadata_available=meta is not None,
                download_source='verified_permanent_release',verified_zip=eco.file_pin(archive))



def prepare_overlay(output, record):
    require(os.environ.get('GITHUB_ACTIONS') == 'true','Actual candidate work is cloud-only')
    locked=lock(output/'methods');work=Path(record['work']);trial=locked['producer']
    archive=work/'producer.zip'; acquisition=download_producer(trial,archive)
    capture=work/'producer';extraction=eco.extract_zip(archive,capture)
    methods=eco.verify_producer_sources(capture,trial)
    require(eco.execute([sys.executable,capture/'methods'/trial['entrypoint'],'validate','--directory',capture,
        '--manifest',output/'source-manifest.json'],output,'original-capture-validation') == 0,
        'Original source-bound critical capture validation failed')
    common.verify_file(capture/'result.json',locked['producer_result'])
    producer=json.loads((capture/'result.json').read_text());validate_parent_contract(producer,locked)
    candidate=capture/trial['candidate_prefix'];shared.verify_evidence_files(candidate,locked['candidate_files'])
    binding=target_binding(candidate/'soc_top.v',capture/locked['source_placement_path'],locked)
    records=output/'producer-records';records.mkdir()
    for name in ('capture.json','result.json','source-manifest.json','source-config.json','source-state.json'):
        shutil.copyfile(capture/name,records/name)
    shutil.copyfile(capture/locked['source_placement_path'],records/'target-source-placement.tsv')
    for name,pin in locked['native_api_source']['files'].items():
        source_path=records/'native-api'/common.safe_relative(name)
        source_path.parent.mkdir(parents=True,exist_ok=True)
        common.download(pin,source_path)
    common.save(output/'target-binding.json',binding)
    baseline=output/'candidate-baseline.tcl';baseline.write_text(baseline_script(locked,binding))
    record.update(original_capture_validation='PASS',producer=trial,producer_methods=methods,
        producer_acquisition=acquisition,producer_extraction=extraction,producer_record_files=shared.file_inventory(records),
        candidate_overlay=dict(directory=str(candidate),files=locked['candidate_files'],baseline_tcl=eco.file_pin(baseline)),
        target_binding=binding,target_binding_pin=eco.file_pin(output/'target-binding.json'))
    common.save(output/'result.json',record)
    return candidate



def verify_overlay(output, record):
    locked=lock(output/'methods')
    require(record.get('original_capture_validation') == 'PASS' and record['producer'] == locked['producer'],
            'Original candidate replay missing')
    overlay=record['candidate_overlay'];candidate=Path(overlay['directory'])
    require(overlay['files'] == locked['candidate_files'],'Candidate input views changed')
    shared.verify_evidence_files(candidate,overlay['files'])
    binding=target_binding(candidate/'soc_top.v',output/'producer-records/target-source-placement.tsv',locked)
    require(binding == record['target_binding'],'Source-bound target graph/placement changed')
    common.verify_file(output/'target-binding.json',record['target_binding_pin'])
    common.verify_file(output/'candidate-baseline.tcl',overlay['baseline_tcl'])
    require((output/'candidate-baseline.tcl').read_text() == baseline_script(locked,binding),'Generated native contract differs')
    return candidate



def native_environment(argv):
    targeted.specification=specification;targeted.configure_native_environment(argv)
    output=Path(argv[argv.index('--force-run-dir')+1]).resolve().parent
    record=json.loads((output/'result.json').read_text());candidate=verify_overlay(output,record)
    os.environ.update(NSSOC_ELECTRICAL_CANDIDATE_ODB=str(candidate/'soc_top.odb'),
        NSSOC_ELECTRICAL_CANDIDATE_SDC=str(candidate/'soc_top.sdc'),
        NSSOC_ELECTRICAL_ODB_SHA=record['candidate_overlay']['files']['soc_top.odb']['sha256'],
        NSSOC_ELECTRICAL_SDC_SHA=record['candidate_overlay']['files']['soc_top.sdc']['sha256'],
        NSSOC_ELECTRICAL_BASELINE_TCL=str(output/'candidate-baseline.tcl'))



def validate_capture(directory,manifest_path=None,spec=None):
    directory=Path(directory);row=BASE_VALIDATE(directory,manifest_path,specification());locked=lock(directory/'methods')
    require(row['producer']==locked['producer'] and row['original_capture_validation']=='PASS','Original full capture replay missing')
    shared.verify_evidence_files(directory/'producer-records',row['producer_record_files'])
    common.verify_file(directory/'producer-records/result.json',locked['producer_result'])
    validate_parent_contract(json.loads((directory/'producer-records/result.json').read_text()),locked)
    for name,pin in locked['native_api_source']['files'].items():
        common.verify_file(directory/'producer-records/native-api'/common.safe_relative(name),pin)
    require(row['candidate_overlay']['files']==locked['candidate_files'],'Original overlay differs')
    common.verify_file(directory/'target-binding.json',row['target_binding_pin'])
    require(json.loads((directory/'target-binding.json').read_text())==row['target_binding'],'Captured binding differs')
    common.verify_file(directory/'candidate-baseline.tcl',row['candidate_overlay']['baseline_tcl'])
    require((directory/'candidate-baseline.tcl').read_text()==baseline_script(locked,row['target_binding']),'Captured native baseline contract differs')
    shared.verify_evidence_files(directory/'logic-controls',row['logic_control_files'])
    require(set(row['logic_proofs'])=={'parent-logic','electrical-logic'},'Both actual limited ECO proofs required')
    for name,proof in row['logic_proofs'].items():
        shared.verify_evidence_files(directory/name,proof['files'])
        require(json.loads((directory/name/'result.json').read_text())==proof['result']
            and row['native_runs'][name]['returncode']==0,'Raw logical proof differs')
    prior.validate_proof_inputs(row,locked,json.loads((directory/'source-manifest.json').read_text()))
    return row



def clean_environment():
    env=BASE_ENVIRONMENT()
    for key in ('GH_TOKEN','GITHUB_TOKEN'):env.pop(key,None)
    return env



def specification():
    return shared.DiagnosticSpec(name='explicit_single_sd3_hold_trial',sources=SOURCES,entrypoint=ENTRY,
                                 step=STEP,validator=validate_diagnostic)


def validate_single_buffer(before,after):
    left=original.logical_cell_census(before);right=original.logical_cell_census(after)
    added=set(right)-set(left)
    require(set(left).issubset(right) and len(added)==1, 'Explicit trial must add exactly one logical instance')
    name=added.pop()
    require(re.fullmatch(r'nssoc_explicit_sd3[0-9]+',name), 'Unapproved native inserted-cell identity')
    cell=right.pop(name)
    require(cell['master']=='sg13g2_dlygate4sd3_1' and set(cell['ports'])=={'A','X'}, 'Added cell is not the fixed identity delay')
    ports=cell['ports']; old=INSERTION['verilog_net']
    newnets=set(ports.values())-{old}
    require(len(set(ports.values()))==2 and len(newnets)==1, 'Added delay signal nets differ')
    new=newnets.pop()
    require(re.fullmatch(r'nssoc_explicit_holdnet[0-9]+',new), 'Unapproved native inserted-net identity')
    require(right[INSERTION['driver']]['ports']['Q']==ports['A']
        and right[INSERTION['sink']]['ports']['D']==ports['X'], 'Delay is not on the exact driver/sink branch')
    for row in right.values():
        row['ports']={key:old if expr==new else expr for key,expr in row['ports'].items()}
    require(left==right,'Contracted delay changed an original master/port expression')
    return dict(original_logical_instances=len(left),added_master=cell['master'],added_instances=1,
                original_logical_equations_preserved_after_identity_contraction=True)


def invariant_files(step,insertion):
    require(re.fullmatch(r'nssoc_explicit_sd3[0-9]+',insertion['buffer']) and re.fullmatch(r'nssoc_explicit_holdnet[0-9]+',insertion['new_net'])
        and insertion['original_net']==INSERTION['native_net'] and insertion['driver']==INSERTION['driver']
        and insertion['sink']==INSERTION['sink'] and insertion['master']==INSERTION['master']
        and insertion['radius_um']==10 and insertion['orientation'] in ('R0','MX'), 'Native insertion identity differs')
    fields=('initial_instances','initial_nets','distance_dbu','dbu_per_micron','radius_um')
    require(all(type(insertion[k]) is int for k in fields) and insertion['dbu_per_micron']>0
        and 0<=insertion['distance_dbu']<=10*insertion['dbu_per_micron']
        and len(insertion['location_dbu'])==2 and all(type(x) is int for x in insertion['location_dbu']),
        'Native bounded vacancy fields differ')
    graphs=['graph-before.tsv','graph-after-contracted.tsv','reload_first-graph-contracted.tsv','reload_repeat-graph-contracted.tsv']
    objects=['source-original-objects.tsv','candidate_source-original-objects.tsv','objects-before.tsv',
        'objects-after-contracted.tsv','after_insertion-original-objects.tsv','reload_first-original-objects.tsv','reload_repeat-original-objects.tsv']
    for group in (graphs,objects):
        require(all((step/p).is_file() and (step/p).stat().st_size>0 for p in group)
            and len({common.sha(step/p) for p in group})==1, 'An original full graph/placement object changed')
    return dict(graph_files={p:eco.file_pin(step/p) for p in graphs},original_object_files={p:eco.file_pin(step/p) for p in objects},
                all_original_cells_unmoved=True,full_native_graph_contraction=True)


def placement_contract(step,locked,insertion,binding):
    cols=['instance','master','x_dbu','y_dbu','orientation','status']
    source={r['instance']:r for r in shared.read_rows(step/'candidate_before/placement.tsv',cols)}
    require(common.sha(step/'candidate_before/placement.tsv')==locked['source_placement_pin']['sha256']
        and len(source)==insertion['initial_instances'], 'Exact original placement census differs')
    driver=source[insertion['driver']]
    x,y=insertion['location_dbu']
    require(abs(x-int(driver['x_dbu']))+abs(y-int(driver['y_dbu']))==insertion['distance_dbu'], 'Vacancy distance differs from source-bound driver')
    for name in STAGES[1:]:
        rows=list(shared.read_rows(step/name/'placement.tsv',cols)); current={r['instance']:r for r in rows}
        require(len(current)==len(rows)==len(source)+1 and set(current)==set(source)|{insertion['buffer']}, 'Placement census changed')
        added=current.pop(insertion['buffer'])
        require(current==source,'An original placement/master/status changed')
        require(added==dict(instance=insertion['buffer'],master=insertion['master'],x_dbu=str(x),y_dbu=str(y),orientation=insertion['orientation'],status='PLACED'), 'New delay left the selected legal vacancy')
    require(binding['native_placement']=={k:source[k] for k in (insertion['driver'],insertion['sink'])}, 'Native/source endpoint placement binding differs')
    return dict(original_instances=len(source),added_instances=1,all_original_placements_and_statuses_equal=True)


def guard(metrics,locked,repeatable,preserved):
    before,after=parent.measured(metrics[STAGES[0]]),parent.measured(metrics[STAGES[-1]])
    refs=dict(locked['historical_reference_metrics'],candidate_before=before)
    guards={k:parent.policy.no_regression(v,after) for k,v in refs.items()}
    gain=after['hold_wns_ns']>before['hold_wns_ns'] or after['hold_tns_ns']>before['hold_tns_ns'] or after['hold_violating_endpoints']<before['hold_violating_endpoints']
    passed=all(guards.values()) and gain and repeatable and preserved
    return dict(reference_metrics=refs,canonical_reloaded=after,no_regression=guards,hold_improved=gain,
        exact_reload_repeatable=repeatable,all_original_physical_objects_preserved=preserved,
        aggregate_estimate_guard_passed=passed,disposition='ISOLATED_IMPROVEMENT_REQUIRES_SIGNOFF' if passed else 'REJECTED_ISOLATED_CANDIDATE',
        zero_violations=all(after[k]==0 for k in parent.policy.COUNTS),candidate_adopted=False,timing_accepted=False,manufacturing_approval=False)


def validate_native_control(root,log_path):
    root=Path(root);row=json.loads((root/'result.json').read_text())
    require(row['status']=='PASS_NATIVE_EXPLICIT_HOLD_CONTROL','Actual small insertion control missing')
    # Exact native negative inventory is part of the new method, never inferred
    # from a workflow colour. Each must have an observed rejection message.
    require(set(row['negative_control_messages'])==set(CONTROL_NEGATIVES)
        and all(isinstance(v,str) and v for v in row['negative_control_messages'].values()), 'Native negative controls omitted')
    require(row['pre_sdc_sha256']==row['post_sdc_sha256']==common.sha(root/'before.sdc')==common.sha(root/'after.sdc'), 'Tiny control changed its constraints')
    require(common.sha(root/'graph-before.tsv')==common.sha(root/'graph-after-contracted.tsv')
        and common.sha(root/'objects-before.tsv')==common.sha(root/'objects-after-contracted.tsv'), 'Tiny native graph/placement contraction differs')
    require(Path(log_path).read_text().splitlines().count('PASS_NATIVE_EXPLICIT_HOLD_CONTROL_NO_CHIP_ACCEPTANCE')==1,'Actual native fixture traversal missing')
    require(all(row[k] is False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')),'Small fixture claims chip acceptance')
    flags=('independently_predicted_nearest_vacancy','deterministic_vacancy','full_graph_contraction_preserved',
        'all_original_placements_preserved','no_detailed_placement_called','pg_bindings_preserved',
        'all_three_corners_loaded_and_timed','constraints_preserved','placement_parasitic_tiny_control_only')
    require(all(row[k] is True for k in flags),'Missing actual tiny invariant')
    insertion=row['insertion']
    require(insertion['master']=='sg13g2_dlygate4sd3_1' and insertion['initial_instances']==3
        and insertion['driver']=='driver' and insertion['sink']=='sink' and insertion['original_net']=='target'
        and re.fullmatch(r'nssoc_explicit_sd3[0-9]+',insertion['buffer'])
        and re.fullmatch(r'nssoc_explicit_holdnet[0-9]+',insertion['new_net'])
        and insertion['location_dbu']==[50400,34020] and insertion['orientation']=='MX'
        and insertion['distance_dbu']==3780 and insertion['dbu_per_micron']==1000 and insertion['radius_um']==10,
        'Tiny native vacancy/identity does not match independently predicted source geometry')
    require(set(row['before_metrics'])==set(row['after_metrics'])=={'fast','typical','slow'},'Tiny PVT coverage incomplete')
    for corner in ('fast','typical','slow'):
        for metrics in (row['before_metrics'][corner],row['after_metrics'][corner]):
            require(set(metrics)=={'min_slack_ns','max_slack_ns'} and all(type(v) in (int,float) and -1000<v<1000 for v in metrics.values()), 'Tiny native finite timing missing')
        require(row['after_metrics'][corner]['min_slack_ns']>row['before_metrics'][corner]['min_slack_ns'], 'Tiny delay did not improve measured hold')
        text=(root/f'after-{corner}.rpt').read_text()
        require('Corner: '+corner in text and insertion['buffer']+'/X (sg13g2_dlygate4sd3_1)' in text,
                'Actual sd3 is absent from a native PVT path')
    require('DPL-0033' in row['negative_control_messages']['native_overlap'], 'Actual placement engine did not reject overlap')
    return row


CONTROL_NEGATIVES=(
    'missing_driver','wrong_driver_master','wrong_sink','wrong_net','missing_net','source_placement',
    'missing_endpoint','extra_endpoint','clock_net','protected_net','protected_driver','fixed_driver',
    'unplaced_driver','driver_missing_VDD','driver_missing_VSS','protected_sink','fixed_sink',
    'unplaced_sink','sink_missing_VDD','sink_missing_VSS','changed_radius','unplaced_other_object',
    'no_legal_vacancy','preexisting_reserved_net','moved_original_cell','changed_original_orientation',
    'changed_original_status','changed_original_protection','changed_original_graph','extra_new_net',
    'extra_new_cell','native_overlap','moved_delay_cell','changed_delay_orientation','fixed_delay_cell',
    'delay_missing_VDD','delay_missing_VSS','reversed_delay_topology','wrong_delay_master')


def validate_diagnostic(step,source_sdc_sha,expected_corners):
    step=Path(step);output=step.parent.parent;locked=lock(output/'methods')
    targeted.validate_targeted_controls(output)
    control=validate_native_control(step/'explicit-control',step/'explicit-control.log')
    row=json.loads((step/'explicit-hold.json').read_text())
    require(row['schema']==1 and row['status']=='COMPLETE_DIAGNOSTIC_ONLY'
        and all(row[k] is False for k in ('candidate_adopted','timing_accepted','manufacturing_approval','thresholds_changed'))
        and row['detailed_placement_calls']==row['repair_timing_calls']==0, 'Unsafe/incomplete explicit trial receipt')
    require(row['source_odb_sha256']==locked['candidate_files']['soc_top.odb']['sha256'] and row['source_sdc_sha256']==source_sdc_sha
        and row['sram_macro_count']==32 and all(row[k] is True for k in ('sram_placement_preserved','source_checkpoint_preserved',
            'estimated_global_route_only','original_objects_preserved','full_graph_contraction_preserved')), 'Explicit source/scope differs')
    checked,loaded,metrics=original.stage_evidence(step,STAGES,source_sdc_sha,expected_corners)
    require(tuple(s['name'] for s in row['stages'])==STAGES and row['timing_metrics']==metrics,'Native stage traversal differs')
    for stage in row['stages']:require(stage==json.loads((step/(stage['name']+'-stage.json')).read_text()),'Raw stage receipt differs')
    prior.equal_metrics(metrics['candidate_before'],locked['baseline_metrics'])
    require(checked['candidate_before']['fingerprints']==locked['baseline_fingerprints'],'Exact source baseline not reproduced')
    insertion=row['insertion'];files=invariant_files(step,insertion)
    require(metrics['candidate_before']['instance_count']==insertion['initial_instances']
        and all(metrics[n]['instance_count']==insertion['initial_instances']+1 for n in STAGES[1:]),'Native insertion growth differs')
    binding=target_binding(step/'candidate_before'/shared.FINGERPRINT_FILES['netlist'],output/'producer-records/target-source-placement.tsv',locked)
    require(binding==json.loads((output/'target-binding.json').read_text()),'Captured source binding differs')
    placement=placement_contract(step,locked,insertion,binding)
    logical=validate_single_buffer((step/'candidate_before'/shared.FINGERPRINT_FILES['netlist']).read_text(),
                                   (step/'after_insertion'/shared.FINGERPRINT_FILES['netlist']).read_text())
    protected=prior.verify_protected(prior.protected_status(step/'before-status.tsv'),prior.protected_status(step/'after-status.tsv'))
    require(set(row['candidate_files'])==set(shared.file_inventory(step/'candidate'))==parent.VIEW_NAMES,'Candidate export census differs')
    shared.verify_evidence_files(step/'candidate',row['candidate_files'])
    require(row['candidate_files']['soc_top.sdc']['sha256']==source_sdc_sha
        and row['candidate_files']['soc_top.v']['sha256']==checked['after_insertion']['fingerprints']['netlist'],'Candidate source equations/constraints differ')
    processes=row['independent_reload_processes']
    require(len(processes)==2 and len({p['pid'] for p in processes})==2 and len({p['parent_pid'] for p in processes})==1,'Independent reload process identities differ')
    for name,process in zip(STAGES[-2:],processes,strict=True):
        original.check_process(process,row['candidate_files']['soc_top.odb']['sha256'],source_sdc_sha)
        require(process['detailed_placement_invocations']==0 and process==json.loads((step/(name+'-process.json')).read_text()),'Fresh reload altered placement or raw identity')
        original.check_headroom(step/(name+'-headroom.json'))
        require((step/(name+'.log')).read_text().splitlines().count('NSSOC_EXPLICIT_INDEPENDENT_RELOAD_COMPLETE '+name)==1,'Fresh independent routing did not complete')
    observations={}
    for name in ('before','inserted_before_fresh_route','after_insertion','reload_first','reload_repeat'):
        m=json.loads((step/(name+'-observation.json')).read_text());parent.measured(m);observations[name]=m
        for corner in expected_corners:
            for delay in ('min','max'):
                for edge in ('rise','fall'):
                    text=(step/f'{name}-{corner}-{delay}-{edge}.rpt').read_text()
                    require('Corner: '+corner in text and '_135214_/Q (sg13g2_dfrbpq_1)' in text
                        and '_135215_/D (sg13g2_dfrbpq_1)' in text,'Missing actual Q slew/endpoint path observation')
    comparisons={n:parent.endpoints.compare(loaded[a],loaded[b]) for n,a,b in (
        ('in_process_insertion','candidate_before','after_insertion'),('export_reload','after_insertion','reload_first'),
        ('independent_reload_repeat','reload_first','reload_repeat'),('canonical_effect','candidate_before','reload_repeat'))}
    repeatable=(checked['reload_first']['fingerprints']==checked['reload_repeat']['fingerprints']
        and loaded['reload_first']['endpoints']==loaded['reload_repeat']['endpoints']
        and loaded['reload_first']['paths']==loaded['reload_repeat']['paths']
        and parent.measured(metrics['reload_first'])==parent.measured(metrics['reload_repeat'])
        and all(checked['after_insertion']['fingerprints'][k]==checked['reload_first']['fingerprints'][k] for k in ('constraints','netlist','placement')))
    log=(step/'openroad-resizertimingpostgrt.log').read_text().splitlines()
    markers=['NSSOC_EXPLICIT_NATIVE_CONTROL_PASS','NSSOC_EXPLICIT_SOURCE_BASELINE_EXACT','NSSOC_EXPLICIT_HOLD_COMPLETE_NO_ADOPTION']
    require(all(log.count(m)==1 for m in markers) and [log.index(m) for m in markers]==sorted(log.index(m) for m in markers),'Native explicit traversal differs')
    for item in checked.values():del item['endpoint_names']
    return dict(native=row,native_control=control,independently_checked_stages=checked,full_endpoint_comparisons=comparisons,
        exact_original_object_and_graph_files=files,placement_contract=placement,logical_single_identity_buffer=logical,
        protected_status=protected,timing_phase_observations=observations,
        aggregate_guard_assessment=guard(metrics,locked,repeatable,True),candidate_adopted=False,timing_accepted=False,
        manufacturing_approval=False,scope='One explicit identity sd3 in an existing vacancy, no old-cell movement, complete hold endpoint census and six historical/fresh guards, two independent global-route reloads. Limited ECO proofs are separately mandatory. No detailed routing, signoff RC, DRC/LVS, boot or manufacturing acceptance.')


def capture(output,destination):
    output,destination=Path(output),Path(destination)
    row=parent.capture(output,destination)
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/explicit-control/*')):
        if path.suffix not in {'.odb','.def'}:continue
        require(path.name in {'before.odb','after.odb','after.def'} and path.is_file() and not path.is_symlink(),
                'Unexpected tiny physical evidence')
        target=destination/path.relative_to(output);target.parent.mkdir(parents=True,exist_ok=True)
        with path.open('rb') as source,target.open('xb') as sink:
            size=os.fstat(source.fileno()).st_size;remaining=size
            while remaining:
                data=source.read(min(1024**2,remaining))
                if not data:break
                sink.write(data);remaining-=len(data)
        row['files'][str(path.relative_to(output))]=dict(bytes=target.stat().st_size,sha256=common.sha(target),
            observed_source_bytes=size,source_truncated_during_copy=bool(remaining))
    common.save(destination/'capture.json',row)
    return row


def configure():
    prior.ENTRY=ENTRY;prior.specification=specification;prior.lock=lock
    prior.prepare_overlay=prepare_overlay;prior.verify_overlay=verify_overlay;prior.validate_diagnostic=validate_diagnostic
    shared.worker=BASE_WORKER;shared.capture=capture;shared.validate_capture=validate_capture
    shared.clean_environment=clean_environment


def main():
    configure()
    if len(sys.argv)>1 and sys.argv[1]=='_native_flow':native_environment(sys.argv)
    return shared.main(specification())


if __name__=='__main__':raise SystemExit(main())
