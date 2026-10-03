#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent one-target ablations; exact accepted single-delay parent, no adoption."""
import argparse
import csv
from functools import partial
import json
import os
from pathlib import Path
import re
import shutil
import sys

import run_cloud_pair_hold as pair
original, single = pair.original, pair.single
prior, parent, shared, common, eco, targeted = pair.prior, pair.parent, pair.shared, pair.common, pair.eco, pair.targeted
require = pair.require
LOCK='hw/soc/pnr/timing-hold-ablation-input.lock.json'
ENTRY='scripts/run_cloud_hold_ablation.py'
HELPER='hw/soc/pnr/timing_hold_ablation_helpers.tcl'
STEP='hw/soc/pnr/timing_hold_ablation_step.tcl'
CHILD='hw/soc/pnr/timing_hold_ablation_reload.tcl'
FIXTURE='sw/tests/timing_hold_ablation_native.tcl'
OWN=(LOCK,ENTRY,HELPER,STEP,CHILD,FIXTURE,'sw/tests/test_hold_ablation.py','.github/workflows/timing-hold-ablation.yml')
SOURCES=tuple(dict.fromkeys(pair.SOURCES+OWN))
STAGES=pair.STAGES
VARIANTS=('eth','npu')
TARGETS={v:dict(pair.INSERTIONS[i],buffer=f'nssoc_ablation_{v}_sd3',new_net=f'nssoc_ablation_{v}_net') for i,v in enumerate(VARIANTS)}


def variant_from_record(row):
    values={f'explicit_hold_ablation_{v}':v for v in VARIANTS}
    require(row.get('diagnostic_kind') in values,'Unknown source-bound ablation variant')
    return values[row['diagnostic_kind']]


def lock(root):
    row=json.loads((Path(root)/LOCK).read_text())
    require(row['schema']==1 and row['variants']==TARGETS,'Ablation target contract differs')
    require(set(row['reuse_method_pins'])==set(pair.SOURCES),'Reusable method closure differs')
    for n,pin in row['reuse_method_pins'].items():common.verify_file(Path(root)/n,pin)
    # Reuse exact parent contract independently from the rejected pair candidate.
    inherited=pair.lock(root)
    require({k:v for k,v in row.items() if k not in {'variants','reuse_method_pins'}}==inherited,
            'Ablation parent differs from the verified single-delay source')
    return row


def target_binding(netlist,placement,locked,variant):
    require(variant in VARIANTS,'Unknown ablation variant')
    raw=pair.target_binding(netlist,placement,locked)
    cells=original.logical_cell_census(Path(netlist).read_text())
    require(not any(n.startswith('nssoc_ablation_')for n in cells),'Ablation namespace exists in original source')
    target=dict(raw['targets'][VARIANTS.index(variant)])
    target['insertion']=TARGETS[variant]
    return dict(raw,variant=variant,targets=[target])


def baseline_script(locked,binding):
    variant=binding['variant'];require(variant in VARIANTS and len(binding['targets'])==1
        and binding['targets'][0]['insertion']==TARGETS[variant],'Ablation baseline selection changed')
    return pair.baseline_script(locked,binding).replace('nssoc_pair_targets','nssoc_ablation_targets')+f'set nssoc_ablation_expected_variant {{{variant}}}\n'


validate_parent_contract=pair.validate_parent_contract
download_producer=pair.download_producer


def prepare_overlay(output, record):
    require(os.environ.get('GITHUB_ACTIONS') == 'true','Actual candidate work is cloud-only')
    variant=variant_from_record(record);locked=lock(output/'methods');work=Path(record['work']);trial=locked['producer']
    archive=work/'producer.zip'; acquisition=download_producer(trial,archive)
    capture=work/'producer';extraction=eco.extract_zip(archive,capture)
    methods=eco.verify_producer_sources(capture,trial)
    require(eco.execute([sys.executable,capture/'methods'/trial['entrypoint'],'validate','--directory',capture,
        '--manifest',output/'source-manifest.json'],output,'original-capture-validation') == 0,
        'Original source-bound critical capture validation failed')
    common.verify_file(capture/'result.json',locked['producer_result'])
    producer=json.loads((capture/'result.json').read_text());validate_parent_contract(producer,locked)
    candidate=capture/trial['candidate_prefix'];shared.verify_evidence_files(candidate,locked['candidate_files'])
    binding=target_binding(candidate/'soc_top.v',capture/locked['source_placement_path'],locked,variant)
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
    variant=variant_from_record(record);locked=lock(output/'methods')
    require(record.get('original_capture_validation') == 'PASS' and record['producer'] == locked['producer'],
            'Original candidate replay missing')
    overlay=record['candidate_overlay'];candidate=Path(overlay['directory'])
    require(overlay['files'] == locked['candidate_files'],'Candidate input views changed')
    shared.verify_evidence_files(candidate,overlay['files'])
    binding=target_binding(candidate/'soc_top.v',output/'producer-records/target-source-placement.tsv',locked,variant)
    require(binding == record['target_binding'],'Source-bound target graph/placement changed')
    common.verify_file(output/'target-binding.json',record['target_binding_pin'])
    common.verify_file(output/'candidate-baseline.tcl',overlay['baseline_tcl'])
    require((output/'candidate-baseline.tcl').read_text() == baseline_script(locked,binding),'Generated native contract differs')
    return candidate


def native_environment(argv):
    require(argv.count('--force-run-dir')==1,'Exactly one isolated run directory is required')
    run=Path(argv[argv.index('--force-run-dir')+1]).resolve();output=run.parent
    require(run.name=='run','Unexpected isolated run directory')
    record=json.loads((output/'result.json').read_text())
    variant=variant_from_record(record);manifest=shared.verify_inputs(output,record,specification(variant))
    require(record.get('runtime_sha256')==targeted.RUNTIME_SHA,'Unexpected runtime for pinned native identity')
    base=json.loads((output/'native-controls/result.json').read_text())
    require(base['command'][0]==targeted.NATIVE_IDENTITY['launcher']['path']
            and base['native_executable_sha256']==targeted.NATIVE_IDENTITY['launcher']['sha256'],
            'Base control launcher differs from pinned native identity')
    methods=output/'methods'
    for name,digest in ((targeted.RECIPE,targeted.RECIPE_SHA),(targeted.FIXTURE,targeted.FIXTURE_SHA)):
        require(shared.common.sha(methods/name)==digest,'Existing targeted native methods changed')
    os.environ.update(NSSOC_TARGETED_METHOD_ROOT=str(methods),
        NSSOC_TARGETED_CONTROL_OUT=str(output/'native-controls/targeted'),
        NSSOC_TARGETED_PDK_ROOT=str(Path(record['work'])/'bundle'/manifest['pdk_root']))
    for name,pin in targeted.NATIVE_IDENTITY.items():
        for key,value in pin.items():
            os.environ[f'NSSOC_TARGETED_{name.upper()}_{key.upper()}']=str(value)
    candidate=verify_overlay(output,record)
    os.environ.update(NSSOC_HOLD_ABLATION_VARIANT=variant,
        NSSOC_ELECTRICAL_CANDIDATE_ODB=str(candidate/'soc_top.odb'),
        NSSOC_ELECTRICAL_CANDIDATE_SDC=str(candidate/'soc_top.sdc'),
        NSSOC_ELECTRICAL_ODB_SHA=record['candidate_overlay']['files']['soc_top.odb']['sha256'],
        NSSOC_ELECTRICAL_SDC_SHA=record['candidate_overlay']['files']['soc_top.sdc']['sha256'],
        NSSOC_ELECTRICAL_BASELINE_TCL=str(output/'candidate-baseline.tcl'))


def validate_capture(directory,manifest_path=None,spec=None):
    directory=Path(directory);variant=variant_from_record(json.loads((directory/'result.json').read_text()))
    row=shared.validate_capture(directory,manifest_path,specification(variant));locked=lock(directory/'methods')
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
    env=shared.clean_environment()
    for key in ('GH_TOKEN','GITHUB_TOKEN'):env.pop(key,None)
    return env

def specification(variant):
    require(variant in VARIANTS,'Unknown ablation variant')
    return shared.DiagnosticSpec(name='explicit_hold_ablation_'+variant,sources=SOURCES,entrypoint=ENTRY,
        step=STEP,validator=partial(validate_diagnostic,variant=variant))


def validate_identity_buffer(before,after,variant):
    target=TARGETS[variant];left=original.logical_cell_census(before);right=original.logical_cell_census(after)
    added=set(right)-set(left)
    require(set(left).issubset(right) and len(added)==1,'Ablation must add exactly one logical cell')
    name=added.pop();require(re.fullmatch(target['buffer']+r'[0-9]+',name),'Ablation buffer prefix differs')
    cell=right.pop(name);require(cell['master']==target['master'] and set(cell['ports'])=={'A','X'},'Ablation is not one identity sd3')
    ports=cell['ports'];old=target['verilog_net'];newnets=set(ports.values())-{old}
    require(len(set(ports.values()))==2 and len(newnets)==1,'Ablation net census differs')
    new=newnets.pop();require(re.fullmatch(target['new_net']+r'[0-9]+',new),'Ablation new net prefix differs')
    require(right[target['driver']]['ports']['Q']==ports['A'] and right[target['sink']]['ports']['D']==ports['X'],
        'Ablation delay is not on the exact selected branch')
    for row in right.values():row['ports']={p:old if v==new else v for p,v in row['ports'].items()}
    require(left==right,'One-buffer contraction changes original equations')
    return dict(original_logical_instances=len(left),added_master=target['master'],added_instances=1,
        original_logical_equations_preserved_after_identity_contraction=True,variant=variant)


def insertion_contract(rows,variant):
    require(type(rows)is list and len(rows)==1,'Exactly one native insertion identity required')
    row=rows[0];expected=TARGETS[variant]
    require(re.fullmatch(expected['buffer']+r'[0-9]+',row['buffer']) and re.fullmatch(expected['new_net']+r'[0-9]+',row['new_net'])
        and row['original_net']==expected['native_net'] and row['driver']==expected['driver'] and row['sink']==expected['sink']
        and row['master']==expected['master'] and row['orientation'] in ('R0','MX'),'Native ablation identity differs')
    fields=('initial_instances','initial_nets','distance_dbu','dbu_per_micron','radius_um')
    require(all(type(row[k])is int for k in fields) and row['dbu_per_micron']>0 and row['radius_um']==10
        and 0<=row['distance_dbu']<=10*row['dbu_per_micron'] and len(row['location_dbu'])==2
        and all(type(x)is int for x in row['location_dbu']),'Invalid ablation vacancy')
    return rows


def invariant_files(step,rows,variant):
    insertion_contract(rows,variant)
    graphs=['graph-before.tsv','graph-after-contracted.tsv','reload_first-graph-contracted.tsv','reload_repeat-graph-contracted.tsv']
    objects=['source-original-objects.tsv','candidate_source-original-objects.tsv','objects-before.tsv',
             'objects-after-contracted.tsv','after_insertion-original-objects.tsv','reload_first-original-objects.tsv','reload_repeat-original-objects.tsv']
    for group in (graphs,objects):
        require(all((step/p).is_file() and (step/p).stat().st_size>0 for p in group)
            and len({common.sha(step/p) for p in group})==1,'Original ablation graph/placement changed')
    return dict(graph_files={p:eco.file_pin(step/p) for p in graphs},original_object_files={p:eco.file_pin(step/p) for p in objects},
                all_original_cells_unmoved=True,full_native_graph_contraction=True)

def placement_contract(step,locked,rows,binding,variant):
    insertion_contract(rows,variant);cols=['instance','master','x_dbu','y_dbu','orientation','status']
    before=list(shared.read_rows(step/'candidate_before/placement.tsv',cols));source={r['instance']:r for r in before}
    require(len(source)==len(before)==rows[0]['initial_instances'] and common.sha(step/'candidate_before/placement.tsv')==locked['source_placement_pin']['sha256'],'Original placement census differs')
    expected={}
    for row in rows:
        x,y=row['location_dbu'];driver=source[row['driver']]
        require(abs(x-int(driver['x_dbu']))+abs(y-int(driver['y_dbu']))==row['distance_dbu'],'Pair vacancy distance differs')
        expected[row['buffer']]=dict(instance=row['buffer'],master=row['master'],x_dbu=str(x),y_dbu=str(y),orientation=row['orientation'],status='PLACED')
    for name in STAGES[1:]:
        values=list(shared.read_rows(step/name/'placement.tsv',cols));current={r['instance']:r for r in values}
        require(len(current)==len(values)==len(source)+1 and current==source|expected,'Original placement or selected pair vacancies changed')
    for target in binding['targets']:
        require(target['native_placement']=={n:source[n] for n in (target['insertion']['driver'],target['insertion']['sink'])},'Pair target binding differs')
    return dict(original_instances=len(source),added_instances=1,all_original_placements_and_statuses_equal=True)

guard=pair.guard


CONTROL_NEGATIVES=('missing_driver', 'wrong_target', 'changed_radius', 'wrong_source_placement', 'protected_branch', 'clock_branch', 'missing_endpoint', 'protected_driver', 'fixed_driver', 'driver_missing_VDD', 'driver_missing_VSS', 'protected_sink', 'fixed_sink', 'sink_missing_VDD', 'sink_missing_VSS', 'wrong_variant', 'unapproved_operation', 'cross_branch_endpoint', 'unplaced_old_sd3', 'physically_shared_branch', 'reserved_cell_prefix', 'reserved_net_prefix', 'adapter_omitted_row', 'adapter_duplicate_row', 'adapter_wrong_buffer', 'adapter_wrong_new_net', 'adapter_wrong_master', 'record_buffer', 'record_new_net', 'record_master', 'record_driver', 'record_sink', 'record_original_net', 'record_initial_instances', 'record_initial_nets', 'record_radius_um', 'moved_original_driver0', 'protected_original_driver0', 'moved_original_sink0', 'protected_original_sink0', 'moved_original_driver1', 'protected_original_driver1', 'moved_original_sink1', 'protected_original_sink1', 'moved_original_nssoc_explicit_sd31', 'protected_original_nssoc_explicit_sd31', 'old_sd3_orientation', 'old_sd3_status', 'old_sd3_graph', 'old_sd3_missing_VDD', 'old_sd3_missing_VSS', 'untouched_branch_graph', 'extra_net', 'extra_cell', 'new_missing_VDD', 'new_wrong_VDD', 'new_missing_VSS', 'new_wrong_VSS', 'reversed_new_branch', 'native_overlap', 'fixed_new', 'missing_actual_cell', 'missing_actual_net')

def validate_native_control(root,log_path,variant):
    root=Path(root);row=json.loads((root/'result.json').read_text())
    require(variant in VARIANTS and row['status']=='PASS_NATIVE_HOLD_ABLATION_CONTROL'
        and row['variant']==variant,'Actual selected ablation control missing')
    selected=VARIANTS.index(variant);untouched=1-selected
    require(row['selected_branch']==selected and row['untouched_branch']==untouched,'Tiny branch identity differs')
    require(set(row['negative_control_messages'])==set(CONTROL_NEGATIVES)
        and all(isinstance(v,str) and v for v in row['negative_control_messages'].values()),'Tiny native negatives omitted')
    require('DPL-0033' in row['negative_control_messages']['native_overlap'],'Actual native overlap not rejected')
    require(row['pre_sdc_sha256']==row['post_sdc_sha256']==common.sha(root/'before.sdc')==common.sha(root/'after.sdc'),
        'Tiny ablation changed constraints')
    for stem in ('graph','objects'):
        require(common.sha(root/(stem+'-before.tsv'))==common.sha(root/(stem+'-after-contracted.tsv')),'Tiny original contraction differs')
    require(Path(log_path).read_text().splitlines().count('PASS_NATIVE_HOLD_ABLATION_CONTROL_NO_CHIP_ACCEPTANCE')==1,
        'Actual native ablation traversal missing')
    require(all(row[k] is False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')),'Tiny control claims acceptance')
    flags=('independently_predicted_nearest_vacancy','untouched_branch_preserved','single_row_adapters_verified',
        'all_original_objects_preserved','all_original_placements_preserved','preserved_original_delay',
        'full_graph_contraction_preserved','exactly_one_new_cell_and_net','pg_bindings_preserved',
        'actual_global_route_before_and_after','all_three_corners_loaded_and_timed','no_detailed_placement_called',
        'constraints_preserved','estimated_global_route_tiny_control_only','tiny_native_control_only')
    require(all(row[k] is True for k in flags),'Tiny native invariant missing')
    ins=row['insertion'];prefix='nssoc_ablation_'+variant
    require(ins['master']=='sg13g2_dlygate4sd3_1' and ins['initial_instances']==5 and ins['initial_nets']==12
        and ins['driver']=='driver'+str(selected) and ins['sink']=='sink'+str(selected)
        and ins['original_net']=='target'+str(selected) and ins['location_dbu']==[50400,34020]
        and ins['orientation']=='MX' and ins['row_name']=='ROW_7' and ins['distance_dbu']==3780
        and ins['dbu_per_micron']==1000 and ins['radius_um']==10
        and re.fullmatch(prefix+r'_sd3[0-9]+',ins['buffer']) and re.fullmatch(prefix+r'_net[0-9]+',ins['new_net']),
        'Tiny deterministic single insertion differs')
    require((row['initial_instances'],row['final_instances'],row['initial_nets'],row['final_nets'])==(5,6,12,13)
        and row['selected_vacancy']=='3780 50400 34020 ROW_7 MX','Tiny complete cell/net/vacancy census differs')
    require(set(row['before_metrics'])==set(row['after_metrics'])=={'target0','target1'},'Tiny branch timing coverage differs')
    for branch in (0,1):
        key='target'+str(branch)
        require(set(row['before_metrics'][key])==set(row['after_metrics'][key])=={'fast','typical','slow'},'Tiny PVT coverage differs')
        for corner in ('fast','typical','slow'):
            for phase in ('before','after'):
                values=row[phase+'_metrics'][key][corner]
                require(set(values)=={'min_slack_ns','max_slack_ns'} and all(type(v)in(int,float)and -1000<v<1000 for v in values.values()),
                    'Tiny finite timing missing')
                text=(root/f'{phase}-branch{branch}-{corner}.rpt').read_text()
                paths=re.findall(r'Path Type: (min|max)\n(.*?)(?=Startpoint:|\Z)',text,re.S)
                require(len(paths)==2 and {k for k,_ in paths}=={'min','max'},'Tiny full min/max path coverage differs')
                for delay,path in paths:
                    require('Corner: '+corner in path and f'driver{branch}/Q (sg13g2_dfrbpq_1)' in path
                        and f'sink{branch}/D (sg13g2_dfrbpq_1)' in path,'Tiny raw branch identity differs')
                    slacks=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack \(MET\)',path)
                    require(len(slacks)==1 and float(format(float(slacks[0]),'.6f'))==values[delay+'_slack_ns'],
                        'Tiny raw reported slack differs from native property precision')
                    if phase=='after' and branch==selected:
                        require(ins['buffer']+'/X (sg13g2_dlygate4sd3_1)' in path,'Tiny selected delay path absent')
                    else:require('nssoc_ablation_' not in path,'Tiny untouched/before path contains ablation delay')
            if branch==selected:
                require(row['after_metrics'][key][corner]['min_slack_ns']>row['before_metrics'][key][corner]['min_slack_ns']
                    and row['after_metrics'][key][corner]['max_slack_ns']>0,'Tiny selected native timing response missing')
            else:require(row['before_metrics'][key][corner]==row['after_metrics'][key][corner],'Tiny untouched branch timing differs')
    return row



def validate_diagnostic(step,source_sdc_sha,expected_corners,variant):
    step=Path(step);output=step.parent.parent;locked=lock(output/'methods')
    targeted.validate_targeted_controls(output)
    control=validate_native_control(step/'ablation-control',step/'ablation-control.log',variant)
    row=json.loads((step/'hold-ablation.json').read_text())
    require(row['schema']==1 and row['variant']==variant and row['status']=='COMPLETE_DIAGNOSTIC_ONLY'
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
    insertions=row['insertions'];files=invariant_files(step,insertions,variant)
    require(metrics['candidate_before']['instance_count']==insertions[0]['initial_instances']
        and all(metrics[n]['instance_count']==insertions[0]['initial_instances']+1 for n in STAGES[1:]),'Native insertion growth differs')
    binding=target_binding(step/'candidate_before'/shared.FINGERPRINT_FILES['netlist'],output/'producer-records/target-source-placement.tsv',locked,variant)
    require(binding==json.loads((output/'target-binding.json').read_text()),'Captured source binding differs')
    placement=placement_contract(step,locked,insertions,binding,variant)
    logical=validate_identity_buffer((step/'candidate_before'/shared.FINGERPRINT_FILES['netlist']).read_text(),
                                   (step/'after_insertion'/shared.FINGERPRINT_FILES['netlist']).read_text(),variant)
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
        require((step/(name+'.log')).read_text().splitlines().count('NSSOC_ABLATION_INDEPENDENT_RELOAD_COMPLETE '+name)==1,'Fresh independent routing did not complete')
    observations={}
    for phase in ('before','inserted_before_fresh_route','after_insertion','reload_first','reload_repeat'):
        for i,target in enumerate([TARGETS[variant]]):
            name=phase+'-'+str(i);m=json.loads((step/(name+'-observation.json')).read_text());parent.measured(m);observations[name]=m
            for corner in expected_corners:
                for delay in ('min','max'):
                    for edge in ('rise','fall'):
                        text=(step/f'{name}-{corner}-{delay}-{edge}.rpt').read_text()
                        require('Corner: '+corner in text and target['driver']+'/Q (sg13g2_dfrbpq_1)' in text
                            and target['sink']+'/D (sg13g2_dfrbpq_1)' in text,'Missing pair Q slew/path observation')
    comparisons={n:parent.endpoints.compare(loaded[a],loaded[b]) for n,a,b in (
        ('in_process_insertion','candidate_before','after_insertion'),('export_reload','after_insertion','reload_first'),
        ('independent_reload_repeat','reload_first','reload_repeat'),('canonical_effect','candidate_before','reload_repeat'))}
    repeatable=(checked['reload_first']['fingerprints']==checked['reload_repeat']['fingerprints']
        and loaded['reload_first']['endpoints']==loaded['reload_repeat']['endpoints']
        and loaded['reload_first']['paths']==loaded['reload_repeat']['paths']
        and parent.measured(metrics['reload_first'])==parent.measured(metrics['reload_repeat'])
        and all(checked['after_insertion']['fingerprints'][k]==checked['reload_first']['fingerprints'][k] for k in ('constraints','netlist','placement')))
    log=(step/'openroad-resizertimingpostgrt.log').read_text().splitlines()
    markers=['NSSOC_ABLATION_NATIVE_CONTROL_PASS','NSSOC_ABLATION_SOURCE_BASELINE_EXACT','NSSOC_ABLATION_HOLD_COMPLETE_NO_ADOPTION']
    require(all(log.count(m)==1 for m in markers) and [log.index(m) for m in markers]==sorted(log.index(m) for m in markers),'Native explicit traversal differs')
    for item in checked.values():del item['endpoint_names']
    return dict(native=row,native_control=control,independently_checked_stages=checked,full_endpoint_comparisons=comparisons,
        exact_original_object_and_graph_files=files,placement_contract=placement,logical_one_identity_buffer=logical,
        protected_status=protected,timing_phase_observations=observations,
        aggregate_guard_assessment=guard(metrics,locked,repeatable,True),candidate_adopted=False,timing_accepted=False,
        manufacturing_approval=False,scope='One explicit identity sd3 cell in existing vacancies, no old-cell movement, complete hold endpoint census and all historical and single-parent/fresh guards, two independent global-route reloads. Limited ECO proofs are separately mandatory. No detailed routing, signoff RC, DRC/LVS, boot or manufacturing acceptance.')

def capture(output,destination):
    output,destination=Path(output),Path(destination)
    row=parent.capture(output,destination)
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/ablation-control/*')):
        if path.suffix not in {'.odb','.def'}:continue
        require(path.name in {'before.odb','before.def','after.odb','after.def'} and path.is_file() and not path.is_symlink(),
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

def logic_proofs(output, record, manifest, candidate, repaired):
    work = Path(record['work']); methods = output/'methods'; app = work/'runtime.AppImage'
    before, liberty, macro = eco.bundle_inputs(work/'bundle', manifest)
    proofs = {}
    for name, left, right in (('parent-logic', before, candidate/'soc_top.v'),
                             ('electrical-logic', candidate/'soc_top.v', repaired)):
        command = [app, 'python', methods/eco.CHECKER, left, right,
                   '--liberty', liberty, '--macro-verilog', macro, '--output', output/name]
        shared.execute(list(map(str, command)), output, record, name, clean_environment())
        proof = json.loads((output/name/'result.json').read_text())
        require(proof.get('status') == 'PASS within scope', 'Missing limited logical proof result')
        proofs[name] = dict(result=proof, files=shared.file_inventory(output/name),
                            before=eco.file_pin(left), after=eco.file_pin(right))
    return proofs


def worker(output, spec=None):
    output = Path(output); record = json.loads((output/'result.json').read_text()); variant=variant_from_record(record); spec = specification(variant)
    try:
        require(record['status'] == 'PREPARED', 'Electrical worker requires prepared original C10 inputs')
        manifest = shared.verify_inputs(output, record, spec)
        candidate = prepare_overlay(output, record)
        work, methods = Path(record['work']), output/'methods'; app = str(work/'runtime.AppImage')
        policy = common.load_policy(work/'bundle', manifest)
        original_pins = policy.state_pins(output/'prepared/state.json')
        env = clean_environment(); env['NSSOC_HOLD_DIAGNOSTIC_HELPER'] = str(methods/'hw/soc/pnr/timing_hold_reproducibility.tcl')
        controls = [app, 'python', str(methods/'sw/tests/hold_reproducibility_native.py'),
            str(output/'native-controls'), '--helper', str(methods/'hw/soc/pnr/timing_hold_reproducibility.tcl'),
            '--step', str(methods/'hw/soc/pnr/timing_hold_diagnostic_step.tcl'),
            '--fixture', str(methods/'sw/tests/timing_hold_reproducibility_native.tcl'),
            '--pdk-root', str(work/'bundle'/manifest['pdk_root'])]
        shared.execute(controls, output, record, 'native-controls', env)
        common.save(output/'native-control-validation.json', shared.validate_controls(output/'native-controls/result.json', record['method_files']))
        _, liberty, _ = eco.bundle_inputs(work/'bundle', manifest)
        shared.execute([app, 'python', str(methods/'sw/tests/eco_logic_native.py'), '--checker', str(methods/eco.CHECKER),
            '--liberty', str(liberty), '--output', str(output/'logic-controls')], output, record, 'logic-controls', env)
        require(json.loads((output/'logic-controls/result.json').read_text())['status'] == 'PASS_NATIVE_ECO_CONTROLS',
                'Native equation controls incomplete')
        shared.verify_inputs(output, record, spec); verify_overlay(output, record)
        command = [app, 'python', str(methods/ENTRY), '_native_flow', '--flow', 'HoldDiagnostics',
            '--manual-pdk', '--pdk-root', str(work/'bundle'/manifest['pdk_root']), '--pdk', manifest['pdk'],
            '--force-run-dir', str(output/'run'), '--from', 'OpenROAD.ResizerTimingPostGRT',
            '--to', 'OpenROAD.ResizerTimingPostGRT', '--with-initial-state', str(output/'prepared/state.json'),
            str(output/'prepared/config.json')]
        shared.execute(command, output, record, 'native-diagnostic', env)
        shared.verify_inputs(output, record, spec); verify_overlay(output, record); policy.verify_pins(original_pins)
        steps = list((output/'run').glob('*-openroad-resizertimingpostgrt'))
        require(len(steps) == 1, 'Missing unique electrical native step')
        source_sdc = Path(json.loads((output/'prepared/state.json').read_text())['sdc'])
        corners = json.loads((output/'source-config.json').read_text())['PNR_CORNERS']
        diagnostic = validate_diagnostic(steps[0], common.sha(source_sdc), corners,variant)
        record['diagnostic'] = diagnostic; common.save(output/'result.json', record)
        proofs = logic_proofs(output, record, manifest, candidate, steps[0]/'candidate/soc_top.v')
        shared.verify_inputs(output, record, spec); verify_overlay(output, record); policy.verify_pins(original_pins)
        record['logic_proofs'] = proofs
        prior.validate_proof_inputs(record, lock(output/'methods'), manifest)
        record.update(status='COMPLETE_DIAGNOSTIC_ONLY', completed=common.now(),
            sdc_sha256=common.sha(source_sdc), output_files=shared.file_inventory(output/'run'),
            control_output_files=shared.file_inventory(output/'native-controls'), logic_proofs=proofs,
            logic_control_files=shared.file_inventory(output/'logic-controls'))
        common.save(output/'result.json', record)
        return 0
    except BaseException as error:
        record.update(status='FAILED_PRESERVED', error=str(error), recorded=common.now())
        common.save(output/'result.json', record); print(str(error), file=sys.stderr); return 1

def main():
    if len(sys.argv)>1 and sys.argv[1]=='_native_flow':
        native_environment(sys.argv)
        output=Path(sys.argv[sys.argv.index('--force-run-dir')+1]).resolve().parent
        variant=variant_from_record(json.loads((output/'result.json').read_text()))
        return shared.native_flow(specification(variant))
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='mode',required=True)
    start=commands.add_parser('start');start.add_argument('--variant',choices=VARIANTS,required=True)
    for key in ('manifest','output','work'):start.add_argument('--'+key,type=Path,required=True)
    job=commands.add_parser('_worker');job.add_argument('--output',type=Path,required=True)
    wait=commands.add_parser('wait');wait.add_argument('--output',type=Path,required=True);wait.add_argument('--seconds',type=float);wait.add_argument('--github-output',type=Path)
    snap=commands.add_parser('capture');snap.add_argument('--output',type=Path,required=True);snap.add_argument('--destination',type=Path,required=True)
    check=commands.add_parser('validate');check.add_argument('--directory',type=Path,required=True);check.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='start':shared.prepare(args.manifest,args.output,args.work,specification(args.variant))
    elif args.mode=='_worker':return worker(args.output)
    elif args.mode=='wait':shared.wait(args.output,args.seconds,args.github_output)
    elif args.mode=='capture':capture(args.output,args.destination)
    else:validate_capture(args.directory,args.manifest)
    return 0


if __name__=='__main__':raise SystemExit(main())
