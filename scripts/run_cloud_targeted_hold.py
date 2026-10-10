#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One guarded 16-endpoint hold diagnostic; never adopt or export a checkpoint."""
import json
import os
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode = True
import compare_full_hold_endpoints as endpoints
import run_cloud_hold_diagnostic as shared
import run_timing_experiments as policy

STAGES = ('matched_before','after_repair_native','after_hold','after_full_update')
BEGIN = 'NSSOC_TARGETED_HOLD_PROBE_REPAIR_BEGIN'
END = 'NSSOC_TARGETED_HOLD_PROBE_REPAIR_END'
COMPLETE = 'NSSOC_TARGETED_HOLD_PROBE_COMPLETE_NO_ADOPTION'
GATE = 'NSSOC_TARGETED_NATIVE_GATE_PASS_BEFORE_C10_LOAD'
RECIPE = 'hw/soc/pnr/timing_repair_experiment.tcl'
FIXTURE = 'sw/tests/timing_hold_targeted_native.tcl'
RECIPE_SHA = '77a9d94391285d9ca5e7fe0cab70517353213d62c3040ed46dd9fe4302a366bb'
FIXTURE_SHA = '066982c820626c0690ae8bcb3e0893189054e264dc1845f27982fa8a532fa3ac'
RUNTIME_SHA = 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
# Read-only hashes from that exact AppImage. Nix has two binary wrappers:
# PATH launcher -> native entry (Tcl argv0) -> actual /proc/self/exe ELF.
NATIVE_IDENTITY = {
    'launcher': dict(path='/nix/store/jgrv88sgsa97cvxdk0jz9rnxss19vw1p-devshell-dir/bin/openroad',
        bytes=16032,sha256='e41c3de2e496258357b41e9e9bdc8d9036cff6f53ffda2c2f61daef5bc827afc'),
    'native_entry': dict(path='/nix/store/qqz49dx8dpx4q9i5wriif091n7iaa0ld-openroad-2026-02-17/bin/openroad',
        bytes=16088,sha256='b1daf182a2702687868c777a722924afeb45f85fc125029357b28a5f73ba8860'),
    'actual_elf': dict(path='/nix/store/qqz49dx8dpx4q9i5wriif091n7iaa0ld-openroad-2026-02-17/bin/.openroad-wrapped',
        bytes=103633024,sha256='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'),
}
SOURCES = shared.SOURCES + ('.github/workflows/timing-targeted-hold.yml',
    'scripts/run_cloud_targeted_hold.py','scripts/compare_full_hold_endpoints.py',
    'scripts/run_timing_experiments.py','scripts/timing_process_guard.py',
    'hw/soc/pnr/timing_targeted_hold_probe_step.tcl',
    'hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl',RECIPE,FIXTURE)
CONTROL_MARKERS = ('PASS_NATIVE_BATCH_GLOBAL_BUDGET_EXHAUSTION_PREVENTS_SECOND_CALL',
    'PASS_NATIVE_SETUP_GUARD_REJECTS_UNSAFE_DELAY_INSERTION',
    'PASS_REAL_NATIVE_BUDGET_OVERRUN_REJECTED',
    'PASS_REAL_NATIVE_TARGETED_HOLD_SMALL_FIXTURE_NOT_CHIP_SIGNOFF')
# These are the exact PNR_CORNERS in the pinned C10 source configuration.
# The separate tiny native fixture deliberately uses fast/slow/typical aliases.
BASELINE_CENSUS = dict(endpoint_count=23527,negative_vertex_endpoints=113,
    corners=['nom_fast_1p32V_m40C','nom_slow_1p08V_125C','nom_typ_1p20V_25C'])


def require(condition,message):
    if not condition:raise ValueError(message)


def integers(row,keys):
    return {name:shared.exact_count(row.get(name)) for name in keys}


def validate_baseline(checked,receipt):
    census=dict(endpoint_count=len(checked['endpoint_names']),
        negative_vertex_endpoints=checked['negative_vertex_endpoints'],corners=sorted(checked['corner_names']))
    require(census==receipt==BASELINE_CENSUS,'Matched-before census differs from the known C10 source')
    return census


def native_property_slack_ns(seconds):
    # OpenSTA 857316ff: StaTclTypes.i PropertyValue calls Unit::asString(...,6).
    # Units.cc uses FLOAT division, clamps abs(UI)<1e-6 to zero, then %.6f.
    # Reproduce that lossy presentation exactly; never add a timing tolerance.
    scaled=struct.unpack('!f',struct.pack('!f',seconds/shared.NATIVE_NS_SCALE_SECONDS))[0]
    return float(format(0.0 if abs(scaled)<1e-6 else scaled,'.6f'))


def validate_targeted_controls(output):
    output=Path(output);root=output/'native-controls/targeted'
    row=json.loads((root/'gate.json').read_text())
    require(row.get('status')=='PASS_TARGETED_NATIVE_GATE' and type(row.get('returncode')) is int
            and row['returncode']==0,'Tiny targeted native gate did not pass')
    require(row.get('recipe_sha256')==RECIPE_SHA and row.get('fixture_sha256')==FIXTURE_SHA,
            'Targeted gate used different native methods')
    base=json.loads((output/'native-controls/result.json').read_text())
    require(json.loads((output/'result.json').read_text()).get('runtime_sha256')==RUNTIME_SHA,
            'Targeted native identity requires the exact pinned runtime')
    require(row.get('native_identity')==NATIVE_IDENTITY,'Targeted native launcher/entry/ELF identity differs')
    require(base['native_executable_sha256']==NATIVE_IDENTITY['launcher']['sha256']
            and base['command'][0]==NATIVE_IDENTITY['launcher']['path']
            and row.get('executable_sha256')==NATIVE_IDENTITY['native_entry']['sha256'],
            'Native control launcher or targeted entry differs from pinned chain')
    for wrapper,target in (('launcher','native_entry'),('native_entry','actual_elf')):
        path=root/f'runtime-{wrapper}.bin';shared.common.verify_file(path,NATIVE_IDENTITY[wrapper])
        require(("makeCWrapper '"+NATIVE_IDENTITY[target]['path']+"'").encode() in path.read_bytes(),
                'Pinned native wrapper target is absent')
    for name,digest in ((RECIPE,RECIPE_SHA),(FIXTURE,FIXTURE_SHA)):
        require(shared.common.sha(output/'methods'/name)==digest,'Staged targeted native source changed')
    shared.verify_evidence_files(root,row.get('files'))
    require(set(shared.file_inventory(root))==set(row['files'])|{'gate.json'},'Targeted native output closure differs')
    require(all(row.get(k) is False for k in ('timing_accepted','candidate_adopted','manufacturing_approval')),
            'Tiny native controls cannot accept timing')
    log=(root/'native.log').read_text()
    for marker in CONTROL_MARKERS:
        require(sum(line==marker or line.startswith(marker+' ') for line in log.splitlines())==1,
                'Missing or repeated targeted native control marker')
    for name in ('before.sdc','blocked-setup/before.sdc'):
        require((root/name).read_bytes()==(root/name.replace('before.sdc','after.sdc')).read_bytes(),
                'Tiny targeted native fixture changed constraints')
    selection,result=row['selection'],row['result']
    require(selection['corners']==['fast','slow','typical'] and selection['selected_count']==2
            and [r['endpoint'] for r in selection['targets']]==['q_bad1','q_bad2'],
            'Native tiny target selection differs')
    require(selection['setup_margin_ns']==0.1 and selection['hold_margin_ns']==0.15
            and selection['allow_setup_violations']==0 and selection['max_passes_per_endpoint']==1,
            'Tiny native guard/margin changed')
    require(selection['initial_instance_count']==3 and selection['global_buffer_budget']==1
            and result['actual_instance_growth']==1 and result['remaining_buffer_budget']==0
            and result['calls'][1]['status']=='GLOBAL_BUFFER_BUDGET_EXHAUSTED',
            'Tiny fixture did not enforce one shared insertion budget')
    overrun=integers(row['overrun'],('initial_instance_count','global_buffer_budget','actual_instance_count','actual_instance_growth'))
    require(overrun['global_buffer_budget']==overrun['initial_instance_count']*2//5
            and overrun['actual_instance_growth']==overrun['actual_instance_count']-overrun['initial_instance_count']
            and overrun['actual_instance_growth']>overrun['global_buffer_budget'],
            'Native budget overrun negative control not substantiated')
    return row


def validate_selection(invocation,before,after,step,expected_corners):
    require(invocation.get('profile')=='hold_guarded_targeted' and invocation.get('call_count')==1,
            'Only one exact targeted profile invocation is supported')
    for key,value in {'endpoint_limit':16,'max_passes_per_endpoint':1,'setup_margin_ns':0.1,
                      'hold_margin_ns':0.15,'allow_setup_violations':False,'remaining_margin_repair_required':True}.items():
        require(invocation.get(key)==value and type(invocation.get(key)) is type(value), 'Targeted invocation bounds changed: '+key)
    counts=integers(invocation,('initial_instance_count','actual_instance_count','global_instance_growth_budget','actual_instance_growth','started_ms','finished_ms','elapsed_ms'))
    initial=counts['initial_instance_count'];budget=initial*2//5
    require(initial>=32 and counts['global_instance_growth_budget']==budget
            and counts['actual_instance_growth']==counts['actual_instance_count']-initial
            and counts['actual_instance_growth']<=budget,'Invalid targeted batch growth budget')
    require(counts['finished_ms']>=counts['started_ms'] and counts['elapsed_ms']==counts['finished_ms']-counts['started_ms'],
            'Invalid targeted invocation interval')
    for kind in ('selection','result'):
        require(shared.common.sha(Path(step)/f'hold-targeted-{kind}.tcldict')==invocation.get(kind+'_sha256'),
                'Raw targeted receipt pin differs')
    selection,result=invocation['selection'],invocation['result']
    require(selection.get('profile')=='hold_guarded_targeted' and selection.get('corners')==sorted(expected_corners),
            'Targeted selection corner/profile mismatch')
    for key,value in {'setup_margin_ns':0.1,'hold_margin_ns':0.15,'allow_setup_violations':0,
                      'max_buffer_fraction':0.4,'max_passes_per_endpoint':1,'endpoint_limit':16,
                      'initial_instance_count':initial,'global_buffer_budget':budget,
                      'remaining_margin_repair_required':True,'signoff':False}.items():
        require(selection.get(key)==value,'Selection bound differs: '+key)
    negative={n:v for n,v in before['endpoints'].items() if v is not None and v<0}
    presented={n:min((native_property_slack_ns(before['paths'][c][n][2]),c)
        for c in expected_corners if before['paths'][c][n][2] is not None) for n in negative}
    ranked=sorted((n for n in negative if presented[n][0]<0),key=lambda n:(presented[n][0],n))[:16]
    targets=selection.get('targets',[])
    require(selection.get('selected_count')==len(targets)==len(ranked)
            and selection.get('negative_endpoints_all_corners_before')==len(negative)
            and [r.get('endpoint') for r in targets]==ranked,'Target selection omits or reorders worst negative endpoints')
    for row in targets:
        name,corner=row['endpoint'],row['worst_corner']
        require(corner in expected_corners and corner==presented[name][1],
                'Selected target worst corner not supported by full export')
        value=shared.seconds(row['initial_slack_ns'])
        require(value is not None and value<0,'Selected target is not negative')
        require(value==presented[name][0],'Selected target slack differs from exact native six-decimal representation')
    calls=result.get('calls',[])
    require([r.get('endpoint') for r in calls]==ranked,'Missing or duplicated targeted endpoint calls')
    for call in calls:
        require(call.get('status') in {'ONE_NATIVE_PASS_COMPLETE','NO_LONGER_NEGATIVE','GLOBAL_BUFFER_BUDGET_EXHAUSTED'},
                'Unknown targeted endpoint result')
        if call['status']!='NO_LONGER_NEGATIVE':
            c=integers(call,('actual_instance_count','actual_instance_growth'))
            require(c['actual_instance_growth']==c['actual_instance_count']-initial
                    and c['actual_instance_growth']<=budget,'Per-call global growth guard failed')
            if call['status']=='ONE_NATIVE_PASS_COMPLETE':
                require(call.get('remaining_buffer_budget')==budget-c['actual_instance_growth'],'Per-call remaining budget differs')
            else:require(c['actual_instance_growth']==budget,'Target skipped without actual budget exhaustion')
    require(result.get('initial_instance_count')==initial and result.get('global_buffer_budget')==budget
            and result.get('actual_instance_count')==counts['actual_instance_count']
            and result.get('actual_instance_growth')==counts['actual_instance_growth']
            and result.get('remaining_buffer_budget')==budget-counts['actual_instance_growth']
            and result.get('remaining_margin_repair_required') is True and result.get('signoff') is False,
            'Targeted result does not preserve global budget/remaining margin obligation')
    require(result.get('negative_endpoints_all_corners_after')==sum(v is not None and v<0 for v in after['endpoints'].values()),
            'Targeted post-call negative count differs from full native stage')
    return invocation


def measured_policy(metrics,source):
    values={}
    for name,row in metrics.items():
        values[name]={key[:-8]+'_ns':row[key]*1e9 for key in
            ('setup_wns_seconds','hold_wns_seconds','setup_tns_seconds','hold_tns_seconds')}
        values[name].update({key:row[key] for key in policy.COUNTS})
    before,after=values[STAGES[0]],values[STAGES[-1]]
    return dict(source_selected_metrics=source,matched_before=before,after_full_update=after,
        no_regression_from_matched_before=policy.no_regression(before,after),
        no_regression_from_selected_c10=policy.no_regression(source,after),
        hold_improved=policy.improved(before,after,'hold'),
        aggregate_estimate_guard_passed=policy.eligible(before,after,source,'hold'),
        negative_hold_endpoint_count_reduced=after['hold_violating_endpoints']<before['hold_violating_endpoints'],
        candidate_adopted=False,timing_accepted=False,source_checkpoint_preserved=True,
        note='Unchanged aggregate guards are reported only. Diagnostic output is not a resumable checkpoint or accepted candidate.')


def validate_diagnostic(step,source_sdc_sha,expected_corners):
    step=Path(step);output=step.parent.parent
    gate=validate_targeted_controls(output)
    row=json.loads((step/'targeted-hold-probe.json').read_text())
    require(row.get('schema')==1 and row.get('status')=='COMPLETE_DIAGNOSTIC_ONLY','Incomplete targeted hold diagnostic')
    require(all(row.get(k) is False for k in ('timing_accepted','candidate_adopted','manufacturing_approval','thresholds_changed')),
            'Targeted diagnostic cannot accept a candidate')
    require(row.get('sram_macro_count')==32 and row.get('sram_placement_preserved') is True,'Source32 SRAM placements differ')
    require(row.get('provisional_stages')==['after_repair_native'],'Provisional native stage must be labelled')
    stages=row.get('stages',[])
    require(tuple(s['name'] for s in stages)==STAGES,'Missing or reordered targeted stage')
    log=(step/'openroad-resizertimingpostgrt.log').read_text()
    for marker in (GATE,BEGIN,END,COMPLETE):require(log.splitlines().count(marker)==1,'Missing or repeated targeted marker')
    require(log.index(GATE)<log.index(BEGIN)<log.index(END)<log.index(COMPLETE),'Targeted markers reordered')
    checked={s['name']:shared.validate_stage(step/s['name'],s,source_sdc_sha) for s in stages}
    loaded={s['name']:endpoints.load_stage(step,s,expected_corners,source_sdc_sha) for s in stages}
    first=checked[STAGES[0]]
    validate_baseline(first,row.get('matched_before_census'))
    require(all(r['endpoint_names']==first['endpoint_names'] and r['corner_names']==first['corner_names'] for r in checked.values()),
            'Endpoint or corner identities changed')
    require(checked['after_hold']['fingerprints']==checked['after_full_update']['fingerprints'],
            'Full timing update changed physical state')
    invocation=row['repair_invocation']
    require(json.loads((step/'repair-invocation.json').read_text())==invocation,'Standalone repair receipt differs')
    validate_selection(invocation,loaded['matched_before'],loaded['after_repair_native'],step,expected_corners)
    metrics=row.get('timing_metrics',{})
    require(set(metrics)==set(STAGES),'Missing setup/electrical stage metrics')
    macro_inventory=None
    for name,data in metrics.items():
        for key in ('setup_wns_seconds','hold_wns_seconds','setup_tns_seconds','hold_tns_seconds'):
            require(shared.seconds(data.get(key)) is not None,'Missing finite timing metric')
        integers(data,('recorded_ms','setup_violating_endpoints','hold_violating_endpoints','slew_violations','capacitance_violations','instance_count'))
        placement=list(shared.read_rows(step/name/'placement.tsv',['instance','master','x_dbu','y_dbu','orientation','status']))
        require(len({r['instance'] for r in placement})==len(placement)==data['instance_count'],'Instance census differs')
        macros={r['instance']:{k:r[k] for k in ('master','x_dbu','y_dbu','orientation')}
                for r in placement if r['master'] in {'SP6TSRAM512x64','DP8TSRAMDP256x16'}}
        require(len(macros)==32,'Full placement export does not contain exactly32 SRAMs')
        if macro_inventory is None:macro_inventory=macros
        require(macros==macro_inventory,'Native SRAM master/location/orientation changed between stages')
        require(data['hold_violating_endpoints']==checked[name]['negative_vertex_endpoints'],'Hold metric count differs from complete export')
        growth=data['instance_count']-invocation['initial_instance_count']
        require(0<=growth<=invocation['global_instance_growth_budget'],'Stage growth exceeds fixed global budget')
    require(metrics['matched_before']['instance_count']==invocation['initial_instance_count']
            and metrics['after_repair_native']['instance_count']==invocation['actual_instance_count'],'Invocation instance counts differ')
    budget=dict(initial_instance_count=invocation['initial_instance_count'],global_buffer_budget=invocation['global_instance_growth_budget'],
        after_repair_instance_count=invocation['actual_instance_count'],final_instance_count=metrics['after_full_update']['instance_count'],
        maximum_observed_growth=max(invocation['actual_instance_growth'],metrics['after_full_update']['instance_count']-invocation['initial_instance_count']),within_budget=True)
    require(row.get('buffer_budget')==budget,'Final budget receipt differs')
    comparisons={name:endpoints.compare(loaded[a],loaded[b]) for name,a,b in (
        ('native_repair_effect','matched_before','after_repair_native'),
        ('legalization_and_rc_effect','after_repair_native','after_hold'),
        ('hold_effect','matched_before','after_hold'),('cache_update_effect','after_hold','after_full_update'),
        ('hold_effect_after_cache_update','matched_before','after_full_update'))}
    for data in checked.values():del data['endpoint_names']
    source=json.loads((output/'source-manifest.json').read_text())['selected_source_metrics']
    return dict(native=row,targeted_native_gate=gate,independently_checked_stages=checked,
        full_endpoint_comparisons=comparisons,aggregate_guard_assessment=measured_policy(metrics,source),
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,thresholds_changed=False,
        resumable_checkpoint=False,scope='Existing16-endpoint hold profile, complete four-stage evidence only; originalC10 and all acceptance guards preserved.')


def specification():
    return shared.DiagnosticSpec(name='targeted_hold_probe',sources=SOURCES,
        entrypoint='scripts/run_cloud_targeted_hold.py',step='hw/soc/pnr/timing_targeted_hold_probe_step.tcl',validator=validate_diagnostic)


def configure_native_environment(argv):
    require(argv.count('--force-run-dir')==1,'Exactly one isolated run directory is required')
    run=Path(argv[argv.index('--force-run-dir')+1]).resolve();output=run.parent
    require(run.name=='run','Unexpected isolated run directory')
    record=json.loads((output/'result.json').read_text())
    manifest=shared.verify_inputs(output,record,specification())
    require(record.get('runtime_sha256')==RUNTIME_SHA,'Unexpected runtime for pinned native identity')
    base=json.loads((output/'native-controls/result.json').read_text())
    require(base['command'][0]==NATIVE_IDENTITY['launcher']['path']
            and base['native_executable_sha256']==NATIVE_IDENTITY['launcher']['sha256'],
            'Base control launcher differs from pinned native identity')
    methods=output/'methods'
    for name,digest in ((RECIPE,RECIPE_SHA),(FIXTURE,FIXTURE_SHA)):
        require(shared.common.sha(methods/name)==digest,'Existing targeted native methods changed')
    os.environ.update(NSSOC_TARGETED_METHOD_ROOT=str(methods),
        NSSOC_TARGETED_CONTROL_OUT=str(output/'native-controls/targeted'),
        NSSOC_TARGETED_PDK_ROOT=str(Path(record['work'])/'bundle'/manifest['pdk_root']))
    for name,pin in NATIVE_IDENTITY.items():
        for key,value in pin.items():
            os.environ[f'NSSOC_TARGETED_{name.upper()}_{key.upper()}']=str(value)


def main():
    if len(sys.argv)>1 and sys.argv[1]=='_native_flow':configure_native_environment(sys.argv)
    return shared.main(specification())


if __name__=='__main__':
    raise SystemExit(main())
