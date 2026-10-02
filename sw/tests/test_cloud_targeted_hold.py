# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure schema/lifecycle controls; real tiny and full-chip execution is cloud-only."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_targeted_hold as probe
from test_cloud_hold_diagnostic import stage_fixture,repin_stage,write,native_control_fixture


def f32(number):return struct.unpack('!f',struct.pack('!f',number))[0]


def invocation_fixture(step,count=20):
    corners=['fast','slow','typical']
    slacks={f'p{i:02d}':f32(-(count-i)*1e-10) for i in range(count)}
    before=dict(endpoints=slacks,paths={c:{n:(v,v,v) for n,v in slacks.items()} for c in corners})
    targets=[dict(endpoint=n,worst_corner='fast',initial_slack_ns=probe.native_property_slack_ns(v))
             for n,v in list(slacks.items())[:16]]
    selection=dict(profile='hold_guarded_targeted',corners=corners,setup_margin_ns=0.1,hold_margin_ns=0.15,
        allow_setup_violations=0,max_buffer_fraction=0.4,initial_instance_count=50,global_buffer_budget=20,
        max_passes_per_endpoint=1,endpoint_limit=16,negative_endpoints_all_corners_before=count,
        selected_count=len(targets),targets=targets,remaining_margin_repair_required=True,signoff=False)
    calls=[dict(endpoint=r['endpoint'],status='ONE_NATIVE_PASS_COMPLETE',actual_instance_count=50,
        actual_instance_growth=0,remaining_buffer_budget=20) for r in targets]
    result=dict(initial_instance_count=50,global_buffer_budget=20,actual_instance_count=50,
        actual_instance_growth=0,remaining_buffer_budget=20,negative_endpoints_all_corners_after=count,
        remaining_margin_repair_required=True,signoff=False,calls=calls)
    invocation=dict(profile='hold_guarded_targeted',call_count=1,endpoint_limit=16,max_passes_per_endpoint=1,
        setup_margin_ns=0.1,hold_margin_ns=0.15,allow_setup_violations=False,remaining_margin_repair_required=True,
        initial_instance_count=50,actual_instance_count=50,global_instance_growth_budget=20,actual_instance_growth=0,
        started_ms=1000,finished_ms=1200,elapsed_ms=200,selection=selection,result=result)
    for kind in ('selection','result'):
        path=step/f'hold-targeted-{kind}.tcldict';path.write_text('synthetic raw '+kind)
        invocation[kind+'_sha256']=probe.shared.common.sha(path)
    return invocation,before,before,corners


@pytest.mark.parametrize('fault',[None,'unselected-negative','positive','order','corner','slack','margin','setup-permission',
 'passes','limit','global-budget','call-missing','calls-excess','call-budget','post-count','raw-pin','closure-waiver','interval'])
def test_complete_census_constrains_exact_negative_batch_and_bounds(tmp_path,fault):
    row,before,after,corners=invocation_fixture(tmp_path)
    selection=row['selection'];result=row['result']
    if fault=='unselected-negative':selection['targets'][-1]['endpoint']='p19'
    if fault=='positive':selection['targets'][0]['initial_slack_ns']=0.1
    if fault=='order':selection['targets'].reverse()
    if fault=='corner':selection['targets'][0]['worst_corner']='absent'
    if fault=='slack':selection['targets'][0]['initial_slack_ns']-=0.01
    if fault=='margin':row['hold_margin_ns']=0
    if fault=='setup-permission':row['allow_setup_violations']=True
    if fault=='passes':row['max_passes_per_endpoint']=2
    if fault=='limit':row['endpoint_limit']=32
    if fault=='global-budget':row['global_instance_growth_budget']=21
    if fault=='call-missing':result['calls'].pop()
    if fault=='calls-excess':result['calls'].append(result['calls'][0])
    if fault=='call-budget':result['calls'][0]['actual_instance_count']=71;result['calls'][0]['actual_instance_growth']=21
    if fault=='post-count':result['negative_endpoints_all_corners_after']=0
    if fault=='raw-pin':row['selection_sha256']='0'*64
    if fault=='closure-waiver':result['remaining_margin_repair_required']=False
    if fault=='interval':row['elapsed_ms']=201
    if fault is None:probe.validate_selection(row,before,after,tmp_path,corners)
    else:
        with pytest.raises(ValueError):probe.validate_selection(row,before,after,tmp_path,corners)


def fixture(output,monkeypatch):
    step=output/'run/01-openroad-resizertimingpostgrt';step.mkdir(parents=True)
    invocation,_,_,_=invocation_fixture(step,count=2)
    stages=[]
    for name in probe.STAGES:
        stage=stage_fixture(step/name,name)
        stage['vertex_path_semantics_match']=True
        stage['native_global_tns_seconds_before']=min(c['native_tns_seconds_before'] for c in stage['corners'])
        stage['native_global_tns_seconds_after']=min(c['native_tns_seconds_after'] for c in stage['corners'])
        (step/name/'placement.tsv').write_text('instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus\n'+''.join(
            f'cell{i}\t'+('SP6TSRAM512x64' if i<32 else 'INV')+f'\t{i}\t0\tR0\tPLACED\n' for i in range(50)))
        write(step/name/'native.json',{k:v for k,v in stage.items() if k not in ('files','fingerprints')})
        repin_stage(step/name,stage);stages.append(stage)
    metrics={name:dict(recorded_ms=1300,setup_wns_seconds=-5e-9,hold_wns_seconds=-5e-10,
        setup_tns_seconds=-10e-9,hold_tns_seconds=-7.5e-10,setup_violating_endpoints=2,
        hold_violating_endpoints=2,slew_violations=0,capacitance_violations=0,instance_count=50) for name in probe.STAGES}
    row=dict(schema=1,status='COMPLETE_DIAGNOSTIC_ONLY',timing_accepted=False,candidate_adopted=False,
        manufacturing_approval=False,thresholds_changed=False,sram_macro_count=32,sram_placement_preserved=True,
        provisional_stages=['after_repair_native'],stages=stages,repair_invocation=invocation,timing_metrics=metrics,
        buffer_budget=dict(initial_instance_count=50,global_buffer_budget=20,after_repair_instance_count=50,
            final_instance_count=50,maximum_observed_growth=0,within_budget=True))
    write(step/'targeted-hold-probe.json',row);write(step/'repair-invocation.json',invocation)
    write(output/'source-manifest.json',dict(selected_source_metrics=dict(setup_wns_ns=-4.710829,hold_wns_ns=-1.840329)))
    (step/'openroad-resizertimingpostgrt.log').write_text('\n'.join((probe.GATE,probe.BEGIN,probe.END,probe.COMPLETE))+'\n')
    # Full-stage table/schema tests remain real; gate/selection have independent
    # positive and mutation tests below and above, without native tool loading.
    monkeypatch.setattr(probe,'validate_targeted_controls',lambda _:{'status':'isolated schema fixture'})
    monkeypatch.setattr(probe,'validate_selection',lambda *args:invocation)
    monkeypatch.setattr(probe,'validate_baseline',lambda *args:dict(probe.BASELINE_CENSUS))
    return step,row


@pytest.mark.parametrize('fault',[None,'marker','stages','cache-route','macro','count','growth','acceptance','raw-receipt'])
def test_four_stage_full_coverage_and_physical_guards(tmp_path,monkeypatch,fault):
    step,row=fixture(tmp_path,monkeypatch)
    if fault=='marker':(step/'openroad-resizertimingpostgrt.log').write_text(probe.COMPLETE)
    if fault=='stages':row['stages'].reverse()
    if fault=='count':row['timing_metrics']['after_hold']['hold_violating_endpoints']=0
    if fault=='growth':row['timing_metrics']['after_hold']['instance_count']=100
    if fault=='acceptance':row['timing_accepted']=True
    if fault=='raw-receipt':write(step/'repair-invocation.json',{})
    if fault in ('cache-route','macro'):
        stage=row['stages'][-1 if fault=='cache-route' else 1]
        name='routes.txt' if fault=='cache-route' else 'placement.tsv'
        p=step/stage['name']/name
        p.write_text('changed routing' if fault=='cache-route' else p.read_text().replace('cell0\tSP6TSRAM512x64\t0','cell0\tSP6TSRAM512x64\t99'))
        repin_stage(step/stage['name'],stage)
    write(step/'targeted-hold-probe.json',row)
    if fault is not None:
        with pytest.raises(ValueError):probe.validate_diagnostic(step,row['stages'][0]['files']['constraints.sdc']['sha256'],['fast','slow'])
    else:
        checked=probe.validate_diagnostic(step,row['stages'][0]['files']['constraints.sdc']['sha256'],['fast','slow'])
        assert len(checked['full_endpoint_comparisons'])==5
        assert checked['candidate_adopted'] is False and checked['resumable_checkpoint'] is False
        assert checked['aggregate_guard_assessment']['no_regression_from_selected_c10'] is False
        assert json.loads(json.dumps(checked))==checked


def test_original_c10_guard_is_not_replaced_by_fresh_before():
    metrics={name:dict(setup_wns_seconds=(-4.909516 if name=='matched_before' else -4.738764)*1e-9,
        setup_tns_seconds=-4e-6,hold_wns_seconds=(-1.840965 if name=='matched_before' else -1.5)*1e-9,
        hold_tns_seconds=-20e-9,setup_violating_endpoints=1384,hold_violating_endpoints=113,
        slew_violations=0,capacitance_violations=1) for name in probe.STAGES}
    row=probe.measured_policy(metrics,dict(setup_wns_ns=-4.710829,hold_wns_ns=-1.840329))
    assert row['hold_improved'] and row['no_regression_from_matched_before']
    assert row['no_regression_from_selected_c10'] is False and row['aggregate_estimate_guard_passed'] is False
    assert row['candidate_adopted'] is False


def test_native_gate_failure_precedes_c10_loading(tmp_path):
    methods=tmp_path/'methods';(methods/'hw/soc/pnr').mkdir(parents=True);(methods/'sw/tests').mkdir(parents=True)
    for name in (probe.RECIPE,probe.FIXTURE,'hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl'):
        (methods/name).write_bytes((ROOT/name).read_bytes())
    env=dict(os.environ,NSSOC_TARGETED_METHOD_ROOT=str(methods),NSSOC_TARGETED_CONTROL_OUT=str(tmp_path/'native-controls/targeted'),
        NSSOC_TARGETED_PDK_ROOT=str(tmp_path/'pdk'),NSSOC_HOLD_DIAGNOSTIC_HELPER=str(ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl'),
        STEP_DIR=str(tmp_path),SCRIPTS_DIR=str(tmp_path/'must-not-be-read'))
    script='''
rename exec real_exec
proc exec {args} {
 if {[lindex $args 0] eq [info nameofexecutable]} {
   return -code error -errorcode {CHILDSTATUS 123 7} "simulated native gate failure"
 }
 return [real_exec {*}$args]
}
proc read_current_odb {} {error "C10_LOAD_MUST_NOT_HAPPEN"}
set code [catch {source [lindex $argv 0]} message]
if {!$code || ![string match {*failed before C10 load*} $message]} {error "wrong failure: $message"}
puts PASS_GATE_FAILED_BEFORE_C10
'''
    control=tmp_path/'gate-control.tcl';control.write_text(script)
    result=subprocess.run(['tclsh',str(control),str(ROOT/'hw/soc/pnr/timing_targeted_hold_probe_step.tcl')],env=env,capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert 'PASS_GATE_FAILED_BEFORE_C10' in result.stdout
    row=json.loads((tmp_path/'native-controls/targeted-failure.json').read_text())
    assert row['returncode']==7 and row['status']=='FAIL_TARGETED_NATIVE_GATE'


def test_exact_existing_native_sources_and_additive_spec():
    assert probe.shared.common.sha(ROOT/probe.RECIPE)==probe.RECIPE_SHA
    assert probe.shared.common.sha(ROOT/probe.FIXTURE)==probe.FIXTURE_SHA
    spec=probe.specification();assert set(probe.shared.SOURCES)<set(spec.sources)
    assert probe.shared.diagnostic_spec().step=='hw/soc/pnr/timing_hold_diagnostic_step.tcl'
    tcl=(ROOT/spec.step).read_text()
    assert tcl.index('nssoc_targeted_native_gate')<tcl.index('read_current_odb')
    assert tcl.count('nssoc_timing_experiment hold_guarded_targeted')==1
    assert 'write_views' not in tcl and 'write_db' not in tcl


def test_shared_capture_retains_targeted_tiny_databases_and_rejects_partial(tmp_path,monkeypatch):
    output=tmp_path/'out';(output/'native-controls/targeted').mkdir(parents=True)
    (output/'native-controls/targeted/tiny-after.odb').write_bytes(b'tiny native fixture only')
    (output/'run').mkdir();(output/'run/full-chip.odb').write_bytes(b'never a restart checkpoint')
    write(output/'result.json',dict(status='RUNNING'))
    monkeypatch.setattr(probe.shared,'observation',lambda _:dict(status='RUNNING',terminal=False))
    snap=tmp_path/'snapshot';row=probe.shared.capture(output,snap)
    assert 'native-controls/targeted/tiny-after.odb' in row['files']
    assert 'run/full-chip.odb' not in row['files']
    assert row['complete_diagnostic_evidence'] is False and row['restart_checkpoint_accepted'] is False
    with pytest.raises(ValueError,match='Partial'):probe.shared.validate_capture(snap,spec=probe.specification())


def test_workflow_has_single_opt_in_and_no_native_elapsed_watchdog():
    import yaml
    w=yaml.load((ROOT/'.github/workflows/timing-targeted-hold.yml').read_text(),Loader=yaml.BaseLoader)
    assert w['permissions']=={'contents':'read'} and w['concurrency']['cancel-in-progress']=='false'
    assert w['on']['push']['paths']==['.github/workflows/timing-targeted-hold.yml']
    job=w['jobs']['diagnose'];assert job['timeout-minutes']=='360'
    commands='\n'.join(s.get('run','') for s in job['steps'])
    assert commands.count(' start ')==1 and 'run_cloud_targeted_hold.py' in commands
    assert '--seconds 9000' in commands and '--seconds 7200' in commands and 'timeout ' not in commands
    uploads=[s for s in job['steps'] if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(uploads)==4 and all(s['with']['include-hidden-files']=='true' for s in uploads)


def targeted_control_fixture(output):
    root=output/'native-controls/targeted';root.mkdir(parents=True)
    for name in (probe.RECIPE,probe.FIXTURE):
        path=output/'methods'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
    write(output/'native-controls/result.json',dict(native_executable_sha256='a'*64))
    for name in ('before.sdc','after.sdc','blocked-setup/before.sdc','blocked-setup/after.sdc'):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixed original constraints\n')
    (root/'native.log').write_text('\n'.join(probe.CONTROL_MARKERS)+'\n')
    (root/'tiny-after.odb').write_bytes(b'tiny fixture database')
    row=dict(status='PASS_TARGETED_NATIVE_GATE',returncode=0,recipe_sha256=probe.RECIPE_SHA,fixture_sha256=probe.FIXTURE_SHA,
        executable_sha256='a'*64,timing_accepted=False,candidate_adopted=False,manufacturing_approval=False,
        selection=dict(corners=['fast','slow','typical'],selected_count=2,targets=[{'endpoint':'q_bad1'},{'endpoint':'q_bad2'}],
            setup_margin_ns=0.1,hold_margin_ns=0.15,allow_setup_violations=0,max_passes_per_endpoint=1,
            initial_instance_count=3,global_buffer_budget=1),
        result=dict(actual_instance_growth=1,remaining_buffer_budget=0,calls=[dict(status='ONE_NATIVE_PASS_COMPLETE'),
            dict(status='GLOBAL_BUFFER_BUDGET_EXHAUSTED')]),
        overrun=dict(initial_instance_count=4,global_buffer_budget=1,actual_instance_count=6,actual_instance_growth=2))
    row['files']=probe.shared.file_inventory(root);write(root/'gate.json',row)
    return root,row


@pytest.mark.parametrize('fault',[None,'exit','recipe','fixture','executable','method-bytes','output-bytes','extra-output',
    'marker','constraints','selection','margin','budget','overrun','adoption'])
def test_targeted_native_gate_requires_pinned_complete_real_control_evidence(tmp_path,fault):
    root,row=targeted_control_fixture(tmp_path)
    if fault=='exit':row['returncode']=1
    if fault=='recipe':row['recipe_sha256']='0'*64
    if fault=='fixture':row['fixture_sha256']='0'*64
    if fault=='executable':row['executable_sha256']='0'*64
    if fault=='method-bytes':(tmp_path/'methods'/probe.RECIPE).write_text('changed source')
    if fault=='output-bytes':(root/'tiny-after.odb').write_bytes(b'changed output')
    if fault=='extra-output':(root/'undeclared').write_text('missing from inventory')
    if fault=='marker':(root/'native.log').write_text('\n'.join(probe.CONTROL_MARKERS[1:]))
    if fault=='constraints':(root/'blocked-setup/after.sdc').write_text('changed constraints')
    if fault=='selection':row['selection']['targets'].reverse()
    if fault=='margin':row['selection']['hold_margin_ns']=0
    if fault=='budget':row['result']['remaining_buffer_budget']=1
    if fault=='overrun':row['overrun']['actual_instance_count']=5;row['overrun']['actual_instance_growth']=1
    if fault=='adoption':row['candidate_adopted']=True
    if fault in ('marker','constraints'):
        row['files']={k:v for k,v in probe.shared.file_inventory(root).items() if k!='gate.json'}
    write(root/'gate.json',row)
    if fault is None:assert probe.validate_targeted_controls(tmp_path)==row
    else:
        with pytest.raises(ValueError):probe.validate_targeted_controls(tmp_path)


@pytest.mark.parametrize('fault',[None,'endpoint-count','negative-count','corner','receipt'])
def test_known_c10_baseline_rejects_changed_census(tmp_path,fault):
    row=dict(endpoint_names=[f'e{i}' for i in range(23527)],negative_vertex_endpoints=113,corner_names=['typical','fast','slow'])
    receipt=dict(probe.BASELINE_CENSUS)
    if fault=='endpoint-count':row['endpoint_names'].pop()
    if fault=='negative-count':row['negative_vertex_endpoints']=112
    if fault=='corner':row['corner_names']=['fast','slow']
    if fault=='receipt':receipt['negative_vertex_endpoints']=112
    if fault is None:assert probe.validate_baseline(row,receipt)==probe.BASELINE_CENSUS
    else:
        with pytest.raises(ValueError,match='known C10'):probe.validate_baseline(row,receipt)
    # Native early gate consumes the actual engine census, without a chip load.
    script=tmp_path/'baseline.tcl'
    script.write_text('source [lindex $argv 0]\nset code [catch {nssoc_targeted_assert_baseline [lindex $argv 1] [lindex $argv 2] [lindex $argv 3]} message]\nputs $code\n')
    result=subprocess.run(['tclsh',str(script),str(ROOT/'hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl'),
        str(len(row['endpoint_names'])),str(row['negative_vertex_endpoints']),' '.join(row['corner_names'])],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()==('1' if fault in ('endpoint-count','negative-count','corner') else '0')
    step=(ROOT/probe.specification().step).read_text()
    assert step.index('nssoc_targeted_assert_baseline')<step.index('NSSOC_TARGETED_HOLD_PROBE_REPAIR_BEGIN')


def test_pure_tcl_json_adapters_preserve_receipts_and_native_numeric_precision(tmp_path):
    script=tmp_path/'adapters.tcl'
    script.write_text('''
source [lindex $argv 0]
source [lindex $argv 1]
set selection [dict create profile hold_guarded_targeted setup_margin_ns 0.1 hold_margin_ns 0.15 \
 allow_setup_violations 0 max_buffer_fraction 0.4 initial_instance_count 3 global_buffer_budget 1 \
 max_passes_per_endpoint 1 endpoint_limit 2 negative_endpoints_all_corners_before 2 selected_count 2 \
 remaining_margin_repair_required true signoff false corners {fast slow typical} \
 targets {{-0.6830402556313132 q_bad1 fast} {-0.47864624751482554 q_bad2 fast}}]
set result [dict create initial_instance_count 3 global_buffer_budget 1 actual_instance_count 4 \
 actual_instance_growth 1 remaining_buffer_budget 0 negative_endpoints_all_corners_after 2 \
 remaining_margin_repair_required true signoff false calls [list \
 [dict create endpoint q_bad1 status ONE_NATIVE_PASS_COMPLETE actual_instance_count 4 actual_instance_growth 1 remaining_buffer_budget 0] \
 [dict create endpoint q_bad2 status GLOBAL_BUFFER_BUDGET_EXHAUSTED actual_instance_count 4 actual_instance_growth 1]]]
puts [nssoc_targeted_selection_json $selection]
puts [nssoc_targeted_result_json $result]
''')
    result=subprocess.run(['tclsh',str(script),str(ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl'),
        str(ROOT/'hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl')],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    selection,receipt=map(json.loads,result.stdout.splitlines())
    assert selection['targets'][0]==dict(initial_slack_ns=-0.6830402556313132,endpoint='q_bad1',worst_corner='fast')
    assert selection['corners']==['fast','slow','typical'] and selection['remaining_margin_repair_required'] is True
    assert selection['signoff'] is False and receipt['signoff'] is False
    assert receipt['calls'][1]['status']=='GLOBAL_BUFFER_BUDGET_EXHAUSTED' and receipt['actual_instance_growth']==1


@pytest.mark.parametrize('fault',[None,'recipe','fixture','duplicate-run','wrong-run'])
def test_native_environment_is_authoritative_and_pins_existing_profile(tmp_path,monkeypatch,fault):
    targeted_control_fixture(tmp_path)
    write(tmp_path/'result.json',dict(work=str(tmp_path/'work')))
    calls=[]
    def verify(output,record,spec):
        calls.append((output,record,spec));return dict(pdk_root='pdk')
    monkeypatch.setattr(probe.shared,'verify_inputs',verify)
    for key in ('NSSOC_TARGETED_METHOD_ROOT','NSSOC_TARGETED_CONTROL_OUT','NSSOC_TARGETED_PDK_ROOT'):
        monkeypatch.setenv(key,'untrusted inherited value')
    if fault in ('recipe','fixture'):(tmp_path/'methods'/(probe.RECIPE if fault=='recipe' else probe.FIXTURE)).write_text('changed')
    args=['_native_flow','--force-run-dir',str(tmp_path/('wrong' if fault=='wrong-run' else 'run'))]
    if fault=='duplicate-run':args+=['--force-run-dir',str(tmp_path/'run')]
    if fault is not None:
        with pytest.raises(ValueError):probe.configure_native_environment(args)
    else:
        probe.configure_native_environment(args)
        assert len(calls)==1 and calls[0][2].name=='targeted_hold_probe'
        assert os.environ['NSSOC_TARGETED_METHOD_ROOT']==str(tmp_path/'methods')
        assert os.environ['NSSOC_TARGETED_CONTROL_OUT']==str(tmp_path/'native-controls/targeted')
        assert os.environ['NSSOC_TARGETED_PDK_ROOT']==str(tmp_path/'work/bundle/pdk')


def test_existing_base_control_validator_and_capture_preserve_additional_targeted_directory(tmp_path):
    output=tmp_path/'output';output.mkdir()
    pins={name:dict(sha256='a'*64,bytes=1) for name in probe.SOURCES}
    row=native_control_fixture(output/'native-controls',pins)
    write(output/'native-controls/result.json',row)
    target=output/'native-controls/targeted';target.mkdir();(target/'tiny-after.odb').write_bytes(b'tiny')
    assert probe.shared.validate_controls(output/'native-controls/result.json',pins)==row
    all_pins=probe.shared.file_inventory(output/'native-controls')
    assert all_pins['targeted/tiny-after.odb']['sha256']==probe.shared.common.sha(target/'tiny-after.odb')
    write(output/'result.json',dict(status='RUNNING'))
    receipt=probe.shared.capture(output,tmp_path/'snapshot')
    captured=receipt['files']['native-controls/targeted/tiny-after.odb']
    assert all(captured[k]==v for k,v in all_pins['targeted/tiny-after.odb'].items())
    assert captured['source_truncated_during_copy'] is False


def test_native_property_six_decimal_loss_is_reproduced_without_relaxing_raw_timing(tmp_path):
    # Pinned Unit::asString(float,int) and PropertyValue formatting, including
    # its pre-existing small-UI clamp, not a new acceptance tolerance.
    values=[f32(-0.6830402556313132e-9),f32(-0.47864624751482554e-9),f32(-9.9e-16),f32(-1.1e-15)]
    assert [probe.native_property_slack_ns(v) for v in values]==[-0.683040,-0.478646,0.,-0.000001]
    # Losing six-digit UI precision must not change the full SI endpoint table.
    raw=values[0]
    assert f32(probe.native_property_slack_ns(raw)*probe.shared.NATIVE_NS_SCALE_SECONDS)!=raw
    row,before,after,corners=invocation_fixture(tmp_path,count=2)
    # Both native printed slacks tie; source recipe breaks that tie by name.
    before['endpoints']['p00']=f32(-1.0000001e-9)
    before['endpoints']['p01']=f32(-1.0000002e-9)
    for corner in corners:
        for name,value in before['endpoints'].items():before['paths'][corner][name]=(value,value,value)
    for target in row['selection']['targets']:target['initial_slack_ns']=-1.0
    probe.validate_selection(row,before,after,tmp_path,corners)
    row['selection']['targets'].reverse()
    with pytest.raises(ValueError,match='reorders'):probe.validate_selection(row,before,after,tmp_path,corners)
