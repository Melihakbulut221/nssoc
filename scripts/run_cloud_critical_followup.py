#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated hold-journal diagnosis and an independent one-buffer sizing trial."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import run_cloud_residual_repair as prior

parent, shared, common, eco, targeted = prior.parent, prior.shared, prior.common, prior.eco, prior.targeted
require = prior.require
ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/timing-critical-followup-input.lock.json'
ENTRY = 'scripts/run_cloud_critical_followup.py'
HELPER = 'hw/soc/pnr/timing_critical_followup_helpers.tcl'
STEP = 'hw/soc/pnr/timing_critical_followup_step.tcl'
CHILD = 'hw/soc/pnr/timing_critical_hold_child.tcl'
FIXTURE = 'sw/tests/timing_critical_followup_native.tcl'
OWN = (LOCK, ENTRY, HELPER, STEP, CHILD, FIXTURE, 'sw/tests/test_cloud_critical_followup.py',
       '.github/workflows/timing-critical-followup.yml')
SOURCES = tuple(dict.fromkeys(prior.SOURCES+OWN))
STAGES = ('candidate_before', 'after_sizing', 'reload_first', 'reload_repeat')
BASE_WORKER = prior.worker
BASE_VALIDATE = prior.BASE_VALIDATE
BASE_ENVIRONMENT = shared.clean_environment


def lock(root):
    row = json.loads((Path(root)/LOCK).read_text())
    require(row['schema'] == 1 and row['runtime_sha256'] == targeted.RUNTIME_SHA
            and row['manifest_sha256'] == eco.MANIFEST_SHA, 'Original runtime/manifest differs')
    require(row['producer']['run_id'] == 37032282750
            and row['producer']['source_commit'] == '90a545bce08500e72e1b0dcaf9b4d3491c4e56d5'
            and row['producer']['artifact_id'] == 11240586806
            and row['producer']['sha256'] == '1349d706ef331eff73c2466fc5442266f87e487d152d86a16a5d58723588c271',
            'Residual producer differs')
    require(row['hold_endpoint'] == '_135215_/D' and row['hold_target']['master'] == 'sg13g2_dfrbpq_1'
            and row['hold_global_slack_seconds'] < 0 and row['hold_policy'] == dict(
                setup_margin_seconds=1e-10, hold_margin_seconds=2e-11,
                allow_setup_violations=False, max_passes=1, max_added_cells=32), 'Hold contract differs')
    require(row['native_api_source']['commit']=='dcf36133a369abc8f3c5e5738cd4d82e4903c0e0', 'Native API source differs')
    require(row['sizing_target'] == dict(instance='fanout639', input_pin='A', output_pin='X',
        before_master='sg13g2_buf_4', after_master='sg13g2_buf_8', output_net='net639'), 'Sizing scope differs')
    require(set(row['candidate_files']) == parent.VIEW_NAMES
            and set(row['frozen_method_pins']) == set(prior.SOURCES), 'Original method/view closure differs')
    for name, pin in row['frozen_method_pins'].items(): common.verify_file(Path(root)/name, pin)
    require(set(row['historical_reference_metrics']) == {'selected_c10','matched_c10','combined_parent',
        'electrical_first','electrical_margin_parent','residual_parent'}, 'Historical guard omitted')
    return row


def target_binding(netlist, placement, locked):
    """Derive the full target neighborhood from the pinned export and native census."""
    common.verify_file(netlist, locked['candidate_files']['soc_top.v'])
    common.verify_file(placement, locked['source_placement_pin'])
    text = Path(netlist).read_text()
    require(text.count(locked['hold_target']['body']) == 1, 'Exact hold endpoint cell changed')
    cells = {}
    for match in re.finditer(r'^[ \t]*(sg13g2_\w+|SP6TSRAM512x64|DP8TSRAMDP256x16) (\\\S+|[A-Za-z_]\w*)\s+\((.*?)\);', text, re.M|re.S):
        name = match[2].removeprefix('\\')
        require(name not in cells, 'Duplicate exported instance')
        pairs = re.findall(r'\.([A-Za-z_]\w*)\(([^()]+)\)', match[3])
        require(len(pairs) == len(dict(pairs)), 'Duplicate exported terminal')
        cells[name] = dict(master=match[1], ports={p:v.strip() for p,v in pairs})
    selected = locked['sizing_target']; name = selected['instance']; driver = cells.get(name)
    require(driver is not None and driver['master'] == selected['before_master']
        and driver['ports'].get('X') == selected['output_net'] and set(driver['ports']) == {'A','X'},
        'Exported sizing target master or functional ports differ')
    require(re.fullmatch(r'[A-Za-z_]\w*', driver['ports']['A']), 'Input net needs a separately proven native-name mapping')
    terms = sorted((instance, cell['master'], port) for instance, cell in cells.items()
                   for port, expression in cell['ports'].items() if expression == selected['output_net'])
    require(len(terms) == 9 and (name, selected['before_master'], 'X') in terms,
            'Expected measured eight-load buffer neighborhood')
    with Path(placement).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        require(reader.fieldnames == ['instance','master','x_dbu','y_dbu','orientation','status'],
                'Unexpected original placement census')
        located = {r['instance']:r for r in reader if r['instance'] in {t[0] for t in terms}}
    require(set(located) == {t[0] for t in terms}, 'No native placement witness for target terminal')
    for instance, master, _ in terms:
        require(located[instance]['master'] == master and re.fullmatch(r'[A-Za-z_]\w*', instance),
                'Unproven Verilog/OpenDB instance identity')
    return dict(target=selected, input_net=driver['ports']['A'], terminals=[list(t) for t in terms],
                native_placement=located[name], netlist=locked['candidate_files']['soc_top.v'],
                placement=locked['source_placement_pin'])


def baseline_script(locked, binding):
    def atom(value):
        require(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_./\[\]-]+',value), 'Unsafe bound Tcl atom')
        return '{'+value+'}'
    lines = ['# Derived from the exact verified residual export; no acceptance substitution.',
             'set nssoc_electrical_expected_metrics [dict create \\']
    lines += [f'    {k} {v!r} \\' for k,v in locked['baseline_metrics'].items()]
    lines += [']','set nssoc_electrical_expected_files [dict create \\']
    lines += [f'    {shared.FINGERPRINT_FILES[k]} {v} \\' for k,v in locked['baseline_fingerprints'].items()]
    lines += [']','set nssoc_critical_terms [list '+' '.join('[list '+' '.join(atom(x) for x in term)+']' for term in binding['terminals'])+']']
    place = binding['native_placement']
    lines += ['set nssoc_critical_place [list '+' '.join(atom(place[k]) for k in ('x_dbu','y_dbu','orientation','status'))+']',
              'set nssoc_critical_input '+atom(binding['input_net']),
              'set nssoc_critical_hold_slack '+repr(locked['hold_global_slack_seconds'])]
    return '\n'.join(lines+[''])


def validate_parent_contract(producer, locked):
    require(producer['status'] == 'COMPLETE_DIAGNOSTIC_ONLY'
        and producer['github_source_commit'] == locked['producer']['source_commit']
        and producer['method_files'] == locked['frozen_method_pins']
        and producer['diagnostic']['native']['candidate_files'] == locked['candidate_files'], 'Residual candidate provenance differs')
    prior.equal_metrics(producer['diagnostic']['native']['timing_metrics']['reload_repeat'], locked['baseline_metrics'])
    require(producer['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints'] == locked['baseline_fingerprints'],
            'Residual canonical fingerprints differ')
    refs = dict(producer['diagnostic']['aggregate_guard_assessment']['reference_metrics'])
    refs['electrical_margin_parent'] = refs.pop('candidate_before')
    refs['residual_parent'] = producer['diagnostic']['aggregate_guard_assessment']['canonical_reloaded']
    require(refs == locked['historical_reference_metrics'], 'Historical guard chain differs')


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
        'Original source-bound residual capture validation failed')
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


def guard(metrics, locked, repeatable, preserved):
    before,after=parent.measured(metrics[STAGES[0]]),parent.measured(metrics[STAGES[-1]])
    references=dict(locked['historical_reference_metrics'],candidate_before=before)
    guards={k:parent.policy.no_regression(v,after) for k,v in references.items()}
    gain=after['setup_wns_ns'] > before['setup_wns_ns'] or after['setup_tns_ns'] > before['setup_tns_ns']
    passed=all(guards.values()) and gain and repeatable and preserved
    return dict(reference_metrics=references,canonical_reloaded=after,no_regression=guards,
        setup_improved=gain,exact_reload_repeatable=repeatable,protected_physical_objects_preserved=preserved,
        aggregate_estimate_guard_passed=passed,disposition='ISOLATED_IMPROVEMENT_REQUIRES_SIGNOFF' if passed else 'REJECTED_ISOLATED_CANDIDATE',
        zero_violations=all(after[k] == 0 for k in parent.policy.COUNTS),candidate_adopted=False,timing_accepted=False,manufacturing_approval=False)


def specification():
    return shared.DiagnosticSpec(name='critical_hold_and_size_trial',sources=SOURCES,entrypoint=ENTRY,step=STEP,validator=validate_diagnostic)


def native_environment(argv):
    targeted.specification=specification;targeted.configure_native_environment(argv)
    output=Path(argv[argv.index('--force-run-dir')+1]).resolve().parent
    record=json.loads((output/'result.json').read_text());candidate=verify_overlay(output,record)
    os.environ.update(NSSOC_ELECTRICAL_CANDIDATE_ODB=str(candidate/'soc_top.odb'),
        NSSOC_ELECTRICAL_CANDIDATE_SDC=str(candidate/'soc_top.sdc'),
        NSSOC_ELECTRICAL_ODB_SHA=record['candidate_overlay']['files']['soc_top.odb']['sha256'],
        NSSOC_ELECTRICAL_SDC_SHA=record['candidate_overlay']['files']['soc_top.sdc']['sha256'],
        NSSOC_ELECTRICAL_BASELINE_TCL=str(output/'candidate-baseline.tcl'))


def capture(output,destination):
    output,destination=Path(output),Path(destination)
    row=parent.capture(output,destination)
    physical=[]
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/hold-debug/candidate/*')):
        require(path.name in parent.VIEW_NAMES and path.is_file() and not path.is_symlink(),'Unexpected hold diagnostic view')
        if path.suffix in {'.odb','.def'}:physical.append(path)
    # The original generic capture omits physical views outside native-controls.
    # These three four-cell fixtures are necessary for complete native evidence.
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/sizing-control/*')):
        if path.suffix not in {'.odb','.def'}:continue
        require(path.name in {'before.odb','after.odb','overlapping-after-swap.def'}
            and path.is_file() and not path.is_symlink(),'Unexpected tiny physical view')
        physical.append(path)
    for path in physical:
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


def stage_evidence(root, names, sdc, corners):
    checked={};loaded={};metrics={};macros=None;endpoint_names=None
    for name in names:
        stage=json.loads((root/(name+'-stage.json')).read_text())
        require(stage['name']==name,'Stage name differs')
        checked[name]=shared.validate_stage(root/name,stage,sdc)
        loaded[name]=parent.endpoints.load_stage(root,stage,corners,sdc)
        metrics[name]=json.loads((root/(name+'-metrics.json')).read_text());parent.measured(metrics[name])
        rows=list(shared.read_rows(root/name/'placement.tsv',['instance','master','x_dbu','y_dbu','orientation','status']))
        current={r['instance']:{k:r[k] for k in ('master','x_dbu','y_dbu','orientation')} for r in rows
                 if r['master'] in {'SP6TSRAM512x64','DP8TSRAMDP256x16'}}
        require(len(current)==32 and len(rows)==metrics[name]['instance_count'],'Native SRAM/instance census differs')
        if macros is None:macros=current;endpoint_names=checked[name]['endpoint_names']
        require(current==macros and checked[name]['endpoint_names']==endpoint_names
            and checked[name]['corner_names']==sorted(corners)
            and metrics[name]['hold_violating_endpoints']==checked[name]['negative_vertex_endpoints'],
            'Macro/endpoint/corner identities or negative census changed')
    return checked,loaded,metrics


def check_headroom(path):
    row=json.loads(path.read_text());targeted.integers(row,('available_kib','parent_rss_kib','required_kib'))
    require(row['required_kib']==max(2097152,(5*row['parent_rss_kib']+3)//4)
        and row['available_kib']>=row['required_kib'],'Native child resource reserve differs')
    return row


def check_process(row, odb, sdc, parent_pid=None):
    require(row['pid']!=row['parent_pid'] and row['repair_invocations']==0
        and row['odb_sha256']==odb and row['sdc_sha256']==sdc
        and row['executable_sha256']==targeted.NATIVE_IDENTITY['actual_elf']['sha256']
        and (parent_pid is None or row['parent_pid']==parent_pid),'Native reload identity differs')
    return row


def hold_debug_evidence(step,locked,sdc,corners):
    root=step/'hold-debug';row=json.loads((root/'hold-debug.json').read_text())
    require(row['status']=='COMPLETE_ISOLATED_HOLD_DEBUG'
        and all(row[k] is False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')),
        'Hold child is incomplete or claims acceptance')
    require(row['input_odb_sha256']==locked['candidate_files']['soc_top.odb']['sha256']
        and row['input_sdc_sha256']==sdc,'Hold child input candidate differs')
    process=check_process(json.loads((root/'reload_first-process.json').read_text()),row['input_odb_sha256'],sdc)
    checked,loaded,metrics=stage_evidence(root,('reload_first','after_hold_debug'),sdc,corners)
    prior.equal_metrics(metrics['reload_first'],locked['baseline_metrics'])
    require(checked['reload_first']['fingerprints']==locked['baseline_fingerprints'],'Independent hold baseline differs')
    call=row['call'];require(call['endpoint']==locked['hold_endpoint'] and call['master']=='sg13g2_dfrbpq_1'
        and call['native_calls']==1 and call['status']=='ONE_NATIVE_PASS_COMPLETE'
        and call['initial_slack_seconds']==locked['hold_global_slack_seconds']
        and all(call[k]==v for k,v in locked['hold_policy'].items())
        and call['initial_instance_count']==metrics['reload_first']['instance_count']
        and call['actual_instance_count']==metrics['after_hold_debug']['instance_count']
        and 0<=call['actual_instance_count']-call['initial_instance_count']<=32,'Hold child policy/growth differs')
    eligibility=row['eligibility']
    require(eligibility['endpoint']=='_135215_/D' and eligibility['driver']=='_135214_/Q'
        and eligibility['source_bound_nontristate_driver'] is True
        and eligibility['hold_slack_seconds']==locked['hold_global_slack_seconds']
        and eligibility['source_predicate_ok_to_buffer']==int(not any(eligibility[k] for k in
            ('is_special','connected_by_abutment','dont_touch'))),'Hold eligibility witness differs')
    protected=prior.verify_protected(prior.protected_status(root/'before-status.tsv'),prior.protected_status(root/'after-status.tsv'))
    require(set(row['candidate_files'])==set(shared.file_inventory(root/'candidate'))==parent.VIEW_NAMES,'Hold export inventory differs')
    shared.verify_evidence_files(root/'candidate',row['candidate_files'])
    require(row['candidate_files']['soc_top.sdc']['sha256']==sdc
        and row['candidate_files']['soc_top.v']['sha256']==checked['after_hold_debug']['fingerprints']['netlist'],
        'Hold diagnostic export differs')
    require(row['after_metrics']==metrics['after_hold_debug'],'Hold post-metrics receipt differs')
    log=(root/'native.log').read_text();lines=log.splitlines()
    markers=['NSSOC_CRITICAL_HOLD_BUFFER_SELECTION_BEGIN','NSSOC_CRITICAL_HOLD_BUFFER_SELECTION_END',
             'NSSOC_CRITICAL_HOLD_CALL_BEGIN','NSSOC_CRITICAL_HOLD_CALL_END','NSSOC_CRITICAL_HOLD_DEBUG_COMPLETE']
    require(all(lines.count(m)==1 for m in markers) and [lines.index(m) for m in markers]==sorted(lines.index(m) for m in markers),
            'Missing/reordered native hold debug traversal')
    chosen=re.findall(r'^(\S+) is the buffer chosen for hold fixing$',log,re.M)
    require(len(chosen)==1 and chosen[0].startswith('sg13g2_'),'Native selected hold buffer missing')
    native_call=log.split(markers[2],1)[1].split(markers[3],1)[0]
    require('repair end _135215_/D' in native_call and 'Hold violations' in native_call,'Actual level-3 hold endpoint debug missing')
    for stage in ('before','after'):
        for corner in corners:
            for delay in ('min','max'):
                for edge in ('rise','fall'):
                    require((root/f'{stage}-{corner}-{delay}-{edge}.rpt').stat().st_size>0,'Missing transition-specific native path')
            require((root/f'{stage}-{corner}-driver-electrical.rpt').is_file(),'Missing native electrical observation')
    analysis=dict(selected_hold_buffer=chosen[0],journal_begin_count=native_call.count('journal begin'),
        journal_restore_count=native_call.count('journal restore starts >>>'),journal_commit_count=native_call.count('journal end'),
        native_inserted_driver_lines=[x for x in native_call.splitlines() if 'hold_slack=' in x or 'journal ' in x or 'inserted ' in x],
        transient_rollback_predicate_observed=False,diagnostic_did_not_feed_sizing=True)
    for item in checked.values():del item['endpoint_names']
    return dict(native=row,process=process,headroom=check_headroom(root/'headroom.json'),stages=checked,
        full_endpoint_comparison=parent.endpoints.compare(loaded['reload_first'],loaded['after_hold_debug']),
        protected_status=protected,debug_analysis=analysis)


def logical_cell_census(text):
    rows={}
    for match in re.finditer(r'^[ \t]*(sg13g2_\w+|SP6TSRAM512x64|DP8TSRAMDP256x16) (\\\S+|[A-Za-z_]\w*)\s+\((.*?)\);',text,re.M|re.S):
        name=match[2].removeprefix('\\');pairs=re.findall(r'\.([A-Za-z_]\w*)\(([^()]+)\)',match[3])
        require(name not in rows and len(pairs)==len(dict(pairs)),'Duplicate logical cell/terminal')
        rows[name]=dict(master=match[1],ports={k:' '.join(v.split()) for k,v in pairs})
    require(rows,'Empty logical cell census')
    return rows


def validate_only_size(before,after):
    left,right=logical_cell_census(before),logical_cell_census(after)
    require('fanout639' in left and left['fanout639']['master']=='sg13g2_buf_4','Original sizing cell missing')
    left['fanout639']['master']='sg13g2_buf_8'
    require(left==right,'Sizing changed another logical master, instance or terminal')
    return dict(retained_logical_instances=len(left),only_master_changed='fanout639:sg13g2_buf_4->sg13g2_buf_8',all_terminal_expressions_preserved=True)


SIZE_NEGATIVES = ('wrong_input','wrong_graph','wrong_place','clock_net','protected_net','protected_driver',
    'protected_load','protected_input','fixed_driver','unplaced_driver','missing_VDD','missing_VSS',
    'incompatible_width_guard','incompatible_height_guard','incompatible_site_guard',
    'incompatible_site_width_guard','incompatible_site_height_guard','incompatible_pinmap_guard')


def validate_native_binding(call,binding):
    place=binding['native_placement']
    require(call['observed_input_net']==binding['input_net'] and call['observed_output_net']=='net639'
        and call['observed_output_terminals']==binding['terminals']
        and call['observed_placement']==[place[k] for k in ('x_dbu','y_dbu','orientation','status')],
        'Native observed sizing graph or placement differs')
    pins=call['observed_all_pin_nets']
    require(set(pins)=={'A','X','VDD','VSS'} and pins['A']==binding['input_net'] and pins['X']=='net639'
        and all(pins[k] and pins[k]!='NULL' for k in ('VDD','VSS')), 'Native sizing terminal/PG witness differs')


def validate_native_sizing_control(root,log_path):
    root=Path(root);gate=json.loads((root/'result.json').read_text())
    require(gate['status']=='PASS_NATIVE_CRITICAL_SIZE_CONTROL','Native sizing gate failed')
    require(set(gate['negative_control_messages'])==set(SIZE_NEGATIVES)
        and all(gate[k+'_rejected'] is True and isinstance(gate['negative_control_messages'][k],str)
                and gate['negative_control_messages'][k] for k in SIZE_NEGATIVES),'Native negative sizing gate incomplete')
    for key in ('native_overlap_detected','native_overlap_repaired','all_three_corners_loaded_and_timed',
                'constraints_preserved','pg_bindings_preserved','all_instance_connections_preserved',
                'debug_hold_resizer_journal_api_called','native_report_buffers_called','native_report_buffers_cmd_zero_called'):
        require(gate[key] is True,'Native sizing invariant missing: '+key)
    require(all(gate[k] is False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')),
        'Tiny control claims chip acceptance')
    call=gate['call']
    require(call['instance']=='driver' and call['original_master']=='sg13g2_buf_4'
        and call['replacement_master']=='sg13g2_buf_8' and call['native_calls']==1 and call['instance_count']==4
        and call['original_width']==3840 and call['replacement_width']==6240 and call['site_width']==480
        and call['connectivity_preserved'] is True and call['immediate_placement_preserved'] is True,
        'Native tiny sizing call differs')
    require(gate['pre_sdc_sha256']==gate['post_sdc_sha256']==common.sha(root/'before.sdc')==common.sha(root/'after.sdc'),
        'Tiny sizing changed actual constraints')
    require(gate['native_overlap_error']=='DPL-0033','Tiny overlap was not native placement rejection')
    for corner in ('fast','slow','typical'):
        report=(root/f'after-{corner}.rpt').read_text()
        require('Corner: '+corner in report and 'driver/X (sg13g2_buf_8)' in report,
                'Native tiny corner did not time the actual replacement')
    log=Path(log_path).read_text()
    require(log.splitlines().count('PASS_NATIVE_CRITICAL_SIZE_CONTROL_NO_CHIP_ACCEPTANCE')==1
        and 'DPL-0033' in log and log.count('Hold Buffer Report:')==2,'Native sizing/API traversal missing')
    return gate


def validate_diagnostic(step,source_sdc_sha,expected_corners):
    step=Path(step);output=step.parent.parent;locked=lock(output/'methods')
    targeted.validate_targeted_controls(output)
    gate=validate_native_sizing_control(step/'sizing-control',step/'sizing-control.log')
    hold_gate=json.loads((step/'residual-control/result.json').read_text())
    require(hold_gate['status']=='PASS_NATIVE_RESIDUAL_CONTROL' and hold_gate['after_hold_seconds']>hold_gate['before_hold_seconds']
        and hold_gate['native_setup_guard_preserved'] is True and hold_gate['constraints_preserved'] is True,
        'Frozen real hold/setup control failed')
    for field in ('call','setup_blocked_call'):
        require(all(hold_gate[field][k]==v for k,v in locked['hold_policy'].items()),'Native control margins/permission differ')
    require(hold_gate['setup_blocked_call']['actual_instance_count']==hold_gate['setup_blocked_call']['initial_instance_count'],
            'Native setup-blocked control inserted a cell')
    row=json.loads((step/'critical-followup.json').read_text())
    require(row['status']=='COMPLETE_DIAGNOSTIC_ONLY' and all(row[k] is False for k in
        ('candidate_adopted','timing_accepted','manufacturing_approval','thresholds_changed','hold_mutation_used_for_sizing')),
        'Unsafe or incomplete followup receipt')
    require(row['sizing_input_odb_sha256']==locked['candidate_files']['soc_top.odb']['sha256']
        and row['sizing_input_sdc_sha256']==source_sdc_sha and row['sram_macro_count']==32
        and row['sram_placement_preserved'] is True and row['source_checkpoint_preserved'] is True
        and row['estimated_global_route_only'] is True,'Sizing source/scope changed')
    debug=hold_debug_evidence(step,locked,source_sdc_sha,expected_corners)
    require(row['hold_debug']==debug['native'],'Raw hold child receipt differs')
    checked,loaded,metrics=stage_evidence(step,STAGES,source_sdc_sha,expected_corners)
    require(tuple(s['name'] for s in row['stages'])==STAGES and row['timing_metrics']==metrics,'Stage traversal differs')
    for stage in row['stages']:require(stage==json.loads((step/(stage['name']+'-stage.json')).read_text()),'Raw stage receipt differs')
    prior.equal_metrics(metrics['candidate_before'],locked['baseline_metrics'])
    require(checked['candidate_before']['fingerprints']==locked['baseline_fingerprints'],'Independent sizing baseline differs')
    call=row['sizing_call'];require(call['instance']=='fanout639' and call['original_master']=='sg13g2_buf_4'
        and call['replacement_master']=='sg13g2_buf_8' and call['native_calls']==1
        and call['connectivity_preserved'] is True and call['immediate_placement_preserved'] is True
        and call['original_width']==8*call['site_width'] and call['replacement_width']==13*call['site_width']
        and all(m['instance_count']==call['instance_count'] for m in metrics.values()),'Sizing scope/census changed')
    binding=target_binding(step/'candidate_before'/shared.FINGERPRINT_FILES['netlist'],
        output/'producer-records/target-source-placement.tsv',locked)
    require(binding==json.loads((output/'target-binding.json').read_text()),'Captured source target binding differs')
    validate_native_binding(call,binding)
    logical=validate_only_size((step/'candidate_before'/shared.FINGERPRINT_FILES['netlist']).read_text(),(step/'after_sizing'/shared.FINGERPRINT_FILES['netlist']).read_text())
    protected=prior.verify_protected(prior.protected_status(step/'before-status.tsv'),prior.protected_status(step/'after-status.tsv'))
    require(set(row['candidate_files'])==set(shared.file_inventory(step/'candidate'))==parent.VIEW_NAMES,'Sizing view closure differs')
    shared.verify_evidence_files(step/'candidate',row['candidate_files'])
    require(row['candidate_files']['soc_top.sdc']['sha256']==source_sdc_sha
        and row['candidate_files']['soc_top.v']['sha256']==checked['after_sizing']['fingerprints']['netlist'],'Sizing export differs')
    processes=row['independent_reload_processes']
    require(len(processes)==2 and len({p['pid'] for p in processes}|{debug['process']['pid']})==3,'Independent process identities repeated')
    for name,process in zip(STAGES[-2:],processes,strict=True):
        check_process(process,row['candidate_files']['soc_top.odb']['sha256'],source_sdc_sha,debug['process']['parent_pid'])
        require(process==json.loads((step/(name+'-process.json')).read_text()),'Raw reload process differs')
        check_headroom(step/(name+'-headroom.json'))
        require((step/(name+'.log')).read_text().splitlines().count('NSSOC_COMBINED_INDEPENDENT_RELOAD_COMPLETE '+name)==1,'Incomplete fresh reload')
    comparisons={name:parent.endpoints.compare(loaded[a],loaded[b]) for name,a,b in (
        ('in_process_sizing','candidate_before','after_sizing'),('export_reload','after_sizing','reload_first'),
        ('independent_reload_repeat','reload_first','reload_repeat'),('canonical_effect','candidate_before','reload_repeat'))}
    repeatable=(checked['reload_first']['fingerprints']==checked['reload_repeat']['fingerprints']
        and loaded['reload_first']['endpoints']==loaded['reload_repeat']['endpoints']
        and loaded['reload_first']['paths']==loaded['reload_repeat']['paths']
        and parent.measured(metrics['reload_first'])==parent.measured(metrics['reload_repeat'])
        and all(checked['after_sizing']['fingerprints'][k]==checked['reload_first']['fingerprints'][k]
                for k in ('constraints','netlist','placement')))
    log=(step/'openroad-resizertimingpostgrt.log').read_text().splitlines()
    markers=['NSSOC_CRITICAL_NATIVE_CONTROLS_PASS','NSSOC_CRITICAL_HOLD_CHILD_EXITED_BEFORE_SIZING',
             'NSSOC_CRITICAL_INDEPENDENT_SIZING_BASELINE_EXACT','NSSOC_CRITICAL_FOLLOWUP_COMPLETE_NO_ADOPTION']
    require(all(log.count(m)==1 for m in markers) and [log.index(m) for m in markers]==sorted(log.index(m) for m in markers),'Native isolation order missing')
    for item in checked.values():del item['endpoint_names']
    return dict(native=row,native_sizing_control=gate,native_hold_control=hold_gate,hold_debug=debug,
        independently_checked_stages=checked,full_endpoint_comparisons=comparisons,logical_size_only=logical,
        protected_status=protected,aggregate_guard_assessment=guard(metrics,locked,repeatable,True),
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
        scope='Independent one-endpoint hold diagnosis, then source-reset one-buffer sizing. All historical guards, full endpoint census, SRAM/protected status and two fresh replays retained; limited ECO equations remain separately mandatory. No final routing, signoff RC, physical LVS/DRC or production acceptance.')


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


def configure():
    # Reuse the immutable orchestration function, with explicit new input,
    # native step and validator hooks. The saved old producer is validated in
    # a separate interpreter using only its exact archived methods.
    prior.ENTRY=ENTRY;prior.specification=specification;prior.lock=lock
    prior.prepare_overlay=prepare_overlay;prior.verify_overlay=verify_overlay
    prior.validate_diagnostic=validate_diagnostic
    shared.worker=BASE_WORKER;shared.capture=capture;shared.validate_capture=validate_capture
    shared.clean_environment=clean_environment


def main():
    configure()
    if len(sys.argv)>1 and sys.argv[1]=='_native_flow':native_environment(sys.argv)
    return shared.main(specification())


if __name__=='__main__':raise SystemExit(main())
