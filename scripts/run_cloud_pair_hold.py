#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Two sd3 identity delays in an existing vacancy, with immutable original objects."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import run_cloud_explicit_hold as single
original = single.original

prior = original.prior
parent, shared, common, eco, targeted = original.parent, original.shared, original.common, original.eco, original.targeted
require = original.require
LOCK = 'hw/soc/pnr/timing-pair-hold-input.lock.json'
ENTRY = 'scripts/run_cloud_pair_hold.py'
HELPER = 'hw/soc/pnr/timing_pair_hold_helpers.tcl'
STEP = 'hw/soc/pnr/timing_pair_hold_step.tcl'
CHILD = 'hw/soc/pnr/timing_pair_hold_reload.tcl'
FIXTURE = 'sw/tests/timing_pair_hold_native.tcl'
OWN = (LOCK, ENTRY, HELPER, STEP, CHILD, FIXTURE, 'sw/tests/test_pair_hold.py',
       '.github/workflows/timing-pair-hold.yml')
SOURCES = tuple(dict.fromkeys(single.SOURCES + OWN))
STAGES = ('candidate_before', 'after_insertion', 'reload_first', 'reload_repeat')
BASE_WORKER = prior.worker
BASE_VALIDATE = prior.BASE_VALIDATE
BASE_ENVIRONMENT = shared.clean_environment
INSERTIONS = (
    dict(driver='_134732_', driver_pin='Q', sink='_134733_', sink_pin='D',
         endpoint_master='sg13g2_dfrbpq_1', native_net='_062302_', verilog_net='_062302_',
         buffer='nssoc_pair0_sd3', new_net='nssoc_pair0_net', master='sg13g2_dlygate4sd3_1', radius_um=10),
    dict(driver='_135205_', driver_pin='Q', sink='_135206_', sink_pin='D',
         endpoint_master='sg13g2_dfrbpq_1', native_net='u_npu.u_node0.sck_s[0]',
         verilog_net=r'\u_npu.u_node0.sck_s [0]', buffer='nssoc_pair1_sd3',
         new_net='nssoc_pair1_net', master='sg13g2_dlygate4sd3_1', radius_um=10))


def lock(root):
    row=json.loads((Path(root)/LOCK).read_text())
    require(row['schema']==1 and row['runtime_sha256']==targeted.RUNTIME_SHA
        and row['manifest_sha256']==eco.MANIFEST_SHA, 'Original runtime/manifest differs')
    require(row['producer']['run_id']==37107650542
        and row['producer']['source_commit']=='0aeef622ccdb12d1c0feafa4d6cf34061880a8a0'
        and row['producer']['artifact_id']==11268859028
        and row['producer']['sha256']=='a0b89c24e222ab32ac07429730399843d4e7cb5a8d05e2adc204274061d1a18c', 'Exact single-delay producer differs')
    require(row['insertions']==list(INSERTIONS), 'Fixed pair contract differs')
    require(set(row['candidate_files'])==parent.VIEW_NAMES
        and set(row['frozen_method_pins'])==set(single.SOURCES), 'Original source/view closure differs')
    for name,pin in row['frozen_method_pins'].items(): common.verify_file(Path(root)/name,pin)
    require(set(row['historical_reference_metrics'])=={'selected_c10','matched_c10','combined_parent',
        'electrical_first','electrical_margin_parent','residual_parent','critical_parent','single_parent'}, 'Historical reference omitted')
    require(row['producer_guard']['aggregate_estimate_guard_passed'] is True
        and row['producer_guard']['candidate_adopted'] is False
        and row['producer_guard']['zero_violations'] is False, 'Original limited improvement scope concealed')
    return row


def native_expression(expr):
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',expr):return expr
    if re.fullmatch(r'\\[A-Za-z_][A-Za-z0-9_.$]*',expr):return expr[1:]
    match=re.fullmatch(r'\\([A-Za-z_][A-Za-z0-9_.$]*) \[(0|[1-9][0-9]*)\]',expr)
    require(match is not None,'Unsupported source-bound signal expression')
    return match[1]+'['+match[2]+']'


def target_binding(netlist,placement,locked):
    common.verify_file(netlist,locked['candidate_files']['soc_top.v'])
    common.verify_file(placement,locked['source_placement_pin'])
    cells=original.logical_cell_census(Path(netlist).read_text())
    require(locked['insertions']==list(INSERTIONS),'Pair targets changed')
    require(not any(name.startswith('nssoc_pair0_') or name.startswith('nssoc_pair1_') for name in cells), 'Pair namespace exists in source')
    old=locked['preserved_original_delay']
    require(cells[old['buffer']]['master']==old['master'] and set(cells[old['buffer']]['ports'])=={'A','X'},'Original delay missing')
    with Path(placement).open() as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        require(reader.fieldnames==['instance','master','x_dbu','y_dbu','orientation','status'],'Source placement schema differs')
        rows=list(reader)
    require(len({r['instance'] for r in rows})==len(rows),'Duplicate source placement instance')
    places={r['instance']:r for r in rows};bound=[]
    for insertion,witness in zip(INSERTIONS,locked['target_witnesses'],strict=True):
        wanted={insertion['driver'],insertion['sink']};terms=[]
        for name,cell in cells.items():
            for pin,expr in cell['ports'].items():
                if expr==insertion['verilog_net']:terms.append([name,cell['master'],pin])
        expected=sorted([[insertion['driver'],insertion['endpoint_master'],'Q'],[insertion['sink'],insertion['endpoint_master'],'D']])
        require(sorted(terms)==expected,'Pair source signal is not exact sole Q to D')
        for name in wanted:
            cell=cells[name];native=witness['native_cell_witnesses'][name]
            require(cell['master']==insertion['endpoint_master'] and set(cell['ports'])=={'CLK','RESET_B','D','Q'},'Source DFF functional ports differ')
            require({k:native_expression(v) for k,v in cell['ports'].items()}=={k:native['pins'][k]['net'] for k in cell['ports']},'Source DFF equations differ from independently captured graph')
            require(places[name]==native['placement'],'Source native placement witness differs')
        bound.append(dict(insertion=insertion,terminals=expected,native_placement={n:places[n] for n in sorted(wanted)},functional_ports={n:cells[n]['ports'] for n in sorted(wanted)}))
    return dict(targets=bound,netlist=locked['candidate_files']['soc_top.v'],placement=locked['source_placement_pin'],preserved_original_delay=old)


def baseline_script(locked,binding):
    def atom(value):
        value=str(value);require(re.fullmatch(r'[A-Za-z0-9_./\[\]-]+',value),'Unsafe bound Tcl atom');return '{'+value+'}'
    lines=['# Exact single-delay parent; every historical guard remains mandatory.',
        'set nssoc_electrical_expected_metrics [dict create \\']
    lines += [f'    {k} {v!r} \\' for k,v in locked['baseline_metrics'].items()]
    lines += [']','set nssoc_electrical_expected_files [dict create \\']
    lines += [f'    {shared.FINGERPRINT_FILES[k]} {v} \\' for k,v in locked['baseline_fingerprints'].items()]
    lines += [']','set nssoc_pair_targets {}']
    for target in binding['targets']:
        row=target['insertion'];places=' '.join(atom(n)+' [list '+' '.join(atom(p[k]) for k in ('x_dbu','y_dbu','orientation','status'))+']' for n,p in target['native_placement'].items())
        lines.append('lappend nssoc_pair_targets [dict create driver '+atom(row['driver'])+' sink '+atom(row['sink'])+' net '+atom(row['native_net'])+' places [dict create '+places+']]')
    return '\n'.join(lines+[''])


def validate_parent_contract(producer,locked):
    require(producer['status']=='COMPLETE_DIAGNOSTIC_ONLY' and producer['github_source_commit']==locked['producer']['source_commit']
        and producer['method_files']==locked['frozen_method_pins']
        and producer['diagnostic']['native']['candidate_files']==locked['candidate_files'],'Single-delay provenance differs')
    prior.equal_metrics(producer['diagnostic']['native']['timing_metrics']['reload_repeat'],locked['baseline_metrics'])
    require(producer['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints']==locked['baseline_fingerprints'],'Exact single-delay fingerprints differ')
    assessment=producer['diagnostic']['aggregate_guard_assessment'];require(assessment==locked['producer_guard'],'Original guard changed')
    refs={**{k:v for k,v in assessment['reference_metrics'].items() if k!='candidate_before'},
          'critical_parent':assessment['reference_metrics']['candidate_before'],'single_parent':assessment['canonical_reloaded']}
    require(refs==locked['historical_reference_metrics'],'Historical chain changed')


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
    return shared.DiagnosticSpec(name='explicit_two_sd3_hold_trial',sources=SOURCES,entrypoint=ENTRY,
                                 step=STEP,validator=validate_diagnostic)


def validate_pair_buffers(before,after):
    left=original.logical_cell_census(before);right=original.logical_cell_census(after)
    added=set(right)-set(left)
    require(set(left).issubset(right) and len(added)==2,'Pair must add exactly two logical instances')
    renames={}
    for insertion in INSERTIONS:
        matches=[n for n in added if re.fullmatch(insertion['buffer']+r'[0-9]+',n)]
        require(len(matches)==1,'Pair inserted instance prefix differs')
        cell=right.pop(matches[0]);require(cell['master']==insertion['master'] and set(cell['ports'])=={'A','X'},'Pair cell is not identity sd3')
        ports=cell['ports'];old=insertion['verilog_net'];newnets=set(ports.values())-{old}
        require(len(set(ports.values()))==2 and len(newnets)==1,'Pair branch nets differ')
        new=newnets.pop();require(re.fullmatch(insertion['new_net']+r'[0-9]+',new) and new not in renames,'Pair net prefix/census differs')
        require(right[insertion['driver']]['ports']['Q']==ports['A'] and right[insertion['sink']]['ports']['D']==ports['X'],'Pair delay is not on exact branch')
        renames[new]=old
    for row in right.values():row['ports']={p:renames.get(v,v) for p,v in row['ports'].items()}
    require(left==right,'Two-buffer contraction changes original equations')
    return dict(original_logical_instances=len(left),added_master='sg13g2_dlygate4sd3_1',added_instances=2,
                original_logical_equations_preserved_after_identity_contraction=True)


def insertion_contract(rows):
    require(type(rows) is list and len(rows)==2,'Exactly two native insertion identities required')
    for i,(row,expected) in enumerate(zip(rows,INSERTIONS,strict=True)):
        require(re.fullmatch(expected['buffer']+r'[0-9]+',row['buffer']) and re.fullmatch(expected['new_net']+r'[0-9]+',row['new_net'])
            and row['original_net']==expected['native_net'] and row['driver']==expected['driver']
            and row['sink']==expected['sink'] and row['master']==expected['master'] and row['orientation'] in ('R0','MX'), 'Native pair identity differs')
        fields=('initial_instances','initial_nets','distance_dbu','dbu_per_micron','radius_um')
        require(all(type(row[k]) is int for k in fields) and row['dbu_per_micron']>0 and row['radius_um']==10
            and 0<=row['distance_dbu']<=10*row['dbu_per_micron'] and len(row['location_dbu'])==2
            and all(type(x) is int for x in row['location_dbu']),'Invalid pair vacancy fields')
        for key in ('initial_instances','initial_nets'):require(row[key]==rows[0][key]+i,'Sequential pair census differs')
    return rows


def invariant_files(step,rows):
    insertion_contract(rows)
    graphs=['graph-before.tsv','graph-after-contracted.tsv','reload_first-graph-contracted.tsv','reload_repeat-graph-contracted.tsv']
    objects=['source-original-objects.tsv','candidate_source-original-objects.tsv','objects-before.tsv',
             'objects-after-contracted.tsv','after_insertion-original-objects.tsv','reload_first-original-objects.tsv','reload_repeat-original-objects.tsv']
    for group in (graphs,objects):
        require(all((step/p).is_file() and (step/p).stat().st_size>0 for p in group)
            and len({common.sha(step/p) for p in group})==1,'Original pair graph/placement changed')
    return dict(graph_files={p:eco.file_pin(step/p) for p in graphs},original_object_files={p:eco.file_pin(step/p) for p in objects},
                all_original_cells_unmoved=True,full_native_graph_contraction=True)


def placement_contract(step,locked,rows,binding):
    insertion_contract(rows);cols=['instance','master','x_dbu','y_dbu','orientation','status']
    before=list(shared.read_rows(step/'candidate_before/placement.tsv',cols));source={r['instance']:r for r in before}
    require(len(source)==len(before)==rows[0]['initial_instances'] and common.sha(step/'candidate_before/placement.tsv')==locked['source_placement_pin']['sha256'],'Original placement census differs')
    expected={}
    for row in rows:
        x,y=row['location_dbu'];driver=source[row['driver']]
        require(abs(x-int(driver['x_dbu']))+abs(y-int(driver['y_dbu']))==row['distance_dbu'],'Pair vacancy distance differs')
        expected[row['buffer']]=dict(instance=row['buffer'],master=row['master'],x_dbu=str(x),y_dbu=str(y),orientation=row['orientation'],status='PLACED')
    for name in STAGES[1:]:
        values=list(shared.read_rows(step/name/'placement.tsv',cols));current={r['instance']:r for r in values}
        require(len(current)==len(values)==len(source)+2 and current==source|expected,'Original placement or selected pair vacancies changed')
    for target in binding['targets']:
        require(target['native_placement']=={n:source[n] for n in (target['insertion']['driver'],target['insertion']['sink'])},'Pair target binding differs')
    return dict(original_instances=len(source),added_instances=2,all_original_placements_and_statuses_equal=True)


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
    require(row['status']=='PASS_NATIVE_PAIR_HOLD_CONTROL','Actual pair native control missing')
    require(set(row['negative_control_messages'])==set(CONTROL_NEGATIVES)
        and all(isinstance(v,str) and v for v in row['negative_control_messages'].values()),'Pair native negatives omitted')
    require(row['pre_sdc_sha256']==row['post_sdc_sha256']==common.sha(root/'before.sdc')==common.sha(root/'after.sdc'),'Pair control changed constraints')
    for stem in ('graph','objects'):require(common.sha(root/(stem+'-before.tsv'))==common.sha(root/(stem+'-after-contracted.tsv')),'Tiny pair contraction differs')
    require(Path(log_path).read_text().splitlines().count('PASS_NATIVE_PAIR_HOLD_CONTROL_NO_CHIP_ACCEPTANCE')==1,'Actual pair native traversal missing')
    require(all(row[k] is False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')),'Tiny pair claims chip acceptance')
    flags=('full_graph_contraction_preserved','all_original_placements_preserved','first_insertion_is_second_obstacle',
           'preserved_original_delay','no_detailed_placement_called','pg_bindings_preserved','all_three_corners_loaded_and_timed',
           'constraints_preserved','estimated_global_route_tiny_control_only')
    require(all(row[k] is True for k in flags),'Pair native invariant omitted')
    require(len(row['insertions'])==2,'Tiny pair incomplete')
    for i,insertion in enumerate(row['insertions']):
        require(insertion['master']=='sg13g2_dlygate4sd3_1' and insertion['initial_instances']==5+i
            and insertion['driver']=='driver'+str(i) and insertion['sink']=='sink'+str(i)
            and insertion['original_net']=='target'+str(i) and insertion['location_dbu']==[50400,34020+7560*i]
            and insertion['orientation']=='MX' and insertion['distance_dbu']==3780
            and insertion['dbu_per_micron']==1000 and insertion['radius_um']==10
            and re.fullmatch('nssoc_pair'+str(i)+r'_sd3[0-9]+',insertion['buffer'])
            and re.fullmatch('nssoc_pair'+str(i)+r'_net[0-9]+',insertion['new_net']),'Tiny deterministic pair geometry differs')
    require((row['initial_instances'],row['final_instances'],row['initial_nets'],row['final_nets'])==(5,7,12,14),'Tiny complete cell/net census differs')
    require(row['first_vacancy']==row['second_original_vacancy']=='3780 50400 34020 ROW_7 MX'
        and row['second_actual_vacancy']=='3780 50400 41580 ROW_9 MX','Tiny first-insertion obstacle witness differs')
    require(set(row['before_metrics'])==set(row['after_metrics'])=={'target0','target1'},'Tiny branch timing coverage differs')
    for i,ins in enumerate(row['insertions']):
        require(ins['initial_nets']==12+i,'Tiny sequential net census differs')
        key='target'+str(i)
        require(set(row['before_metrics'][key])==set(row['after_metrics'][key])=={'fast','typical','slow'},'Tiny PVT coverage differs')
        for corner in ('fast','typical','slow'):
            for value in (row['before_metrics'][key][corner],row['after_metrics'][key][corner]):
                require(set(value)=={'min_slack_ns','max_slack_ns'} and all(type(v) in (int,float) and -1000<v<1000 for v in value.values()),'Tiny finite timing missing')
            require(row['after_metrics'][key][corner]['min_slack_ns']>row['before_metrics'][key][corner]['min_slack_ns'],'Tiny pair hold failed to improve')
            raw=(root/f'after-branch{i}-{corner}.rpt').read_text()
            require('Corner: '+corner in raw and ins['buffer']+'/X (sg13g2_dlygate4sd3_1)' in raw,'Tiny sd3 native path absent')
        require('DPL-0033' in row['negative_control_messages']['native_overlap_'+str(i)],'Actual native overlap not rejected')
    return row


# Frozen with the native fixture before publication.
CONTROL_NEGATIVES=(
    'missing_driver_0',
    'wrong_target_0',
    'changed_radius_0',
    'protected_branch_0',
    'missing_endpoint_0',
    'protected_driver0',
    'fixed_driver0',
    'driver0_missing_VDD',
    'driver0_missing_VSS',
    'protected_sink0',
    'fixed_sink0',
    'sink0_missing_VDD',
    'sink0_missing_VSS',
    'missing_driver_1',
    'wrong_target_1',
    'changed_radius_1',
    'protected_branch_1',
    'missing_endpoint_1',
    'protected_driver1',
    'fixed_driver1',
    'driver1_missing_VDD',
    'driver1_missing_VSS',
    'protected_sink1',
    'fixed_sink1',
    'sink1_missing_VDD',
    'sink1_missing_VSS',
    'wrong_namespace',
    'unapproved_operation',
    'cross_branch_endpoint',
    'unplaced_old_sd3',
    'physically_shared_branch',
    'omitted_branch',
    'omitted_both',
    'duplicate_branch',
    'reversed_branch_order',
    'duplicate_driver',
    'duplicate_sink',
    'duplicate_original_net',
    'duplicate_new_net',
    'duplicate_buffer',
    'wrong_second_initial_instances',
    'wrong_second_initial_nets',
    'wrong_recorded_master',
    'moved_original_driver0',
    'protected_original_driver0',
    'moved_original_sink0',
    'protected_original_sink0',
    'moved_original_driver1',
    'protected_original_driver1',
    'moved_original_sink1',
    'protected_original_sink1',
    'moved_original_nssoc_explicit_sd31',
    'protected_original_nssoc_explicit_sd31',
    'old_sd3_orientation',
    'old_sd3_status',
    'old_sd3_graph',
    'old_sd3_missing_VDD',
    'old_sd3_missing_VSS',
    'extra_net',
    'extra_cell',
    'new0_missing_VDD',
    'new0_wrong_VDD',
    'new0_missing_VSS',
    'new0_wrong_VSS',
    'new0_reversed_branch',
    'native_overlap_0',
    'fixed_new_0',
    'new1_missing_VDD',
    'new1_wrong_VDD',
    'new1_missing_VSS',
    'new1_wrong_VSS',
    'new1_reversed_branch',
    'native_overlap_1',
    'fixed_new_1',
)


def validate_diagnostic(step,source_sdc_sha,expected_corners):
    step=Path(step);output=step.parent.parent;locked=lock(output/'methods')
    targeted.validate_targeted_controls(output)
    control=validate_native_control(step/'pair-control',step/'pair-control.log')
    row=json.loads((step/'pair-hold.json').read_text())
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
    insertions=row['insertions'];files=invariant_files(step,insertions)
    require(metrics['candidate_before']['instance_count']==insertions[0]['initial_instances']
        and all(metrics[n]['instance_count']==insertions[0]['initial_instances']+2 for n in STAGES[1:]),'Native insertion growth differs')
    binding=target_binding(step/'candidate_before'/shared.FINGERPRINT_FILES['netlist'],output/'producer-records/target-source-placement.tsv',locked)
    require(binding==json.loads((output/'target-binding.json').read_text()),'Captured source binding differs')
    placement=placement_contract(step,locked,insertions,binding)
    logical=validate_pair_buffers((step/'candidate_before'/shared.FINGERPRINT_FILES['netlist']).read_text(),
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
        require((step/(name+'.log')).read_text().splitlines().count('NSSOC_PAIR_INDEPENDENT_RELOAD_COMPLETE '+name)==1,'Fresh independent routing did not complete')
    observations={}
    for phase in ('before','inserted_before_fresh_route','after_insertion','reload_first','reload_repeat'):
        for i,target in enumerate(INSERTIONS):
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
    markers=['NSSOC_PAIR_NATIVE_CONTROL_PASS','NSSOC_PAIR_SOURCE_BASELINE_EXACT','NSSOC_PAIR_HOLD_COMPLETE_NO_ADOPTION']
    require(all(log.count(m)==1 for m in markers) and [log.index(m) for m in markers]==sorted(log.index(m) for m in markers),'Native explicit traversal differs')
    for item in checked.values():del item['endpoint_names']
    return dict(native=row,native_control=control,independently_checked_stages=checked,full_endpoint_comparisons=comparisons,
        exact_original_object_and_graph_files=files,placement_contract=placement,logical_two_identity_buffers=logical,
        protected_status=protected,timing_phase_observations=observations,
        aggregate_guard_assessment=guard(metrics,locked,repeatable,True),candidate_adopted=False,timing_accepted=False,
        manufacturing_approval=False,scope='Two explicit identity sd3 cells in existing vacancies, no old-cell movement, complete hold endpoint census and all historical and single-parent/fresh guards, two independent global-route reloads. Limited ECO proofs are separately mandatory. No detailed routing, signoff RC, DRC/LVS, boot or manufacturing acceptance.')


def capture(output,destination):
    output,destination=Path(output),Path(destination)
    row=parent.capture(output,destination)
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/pair-control/*')):
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
