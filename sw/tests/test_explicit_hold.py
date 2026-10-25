# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed identity-delay, source and placement gates without chip execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_explicit_hold as m  # noqa: E402


def locked():
    return json.loads((ROOT/m.LOCK).read_text())


def fixture(tmp_path,fault=None):
    row=locked()
    driver='sg13g2_dfrbpq_1 _135214_ (.RESET_B(net6187), .D(upstream), .Q(\\u_npu.u_node0.mosi_s [0]), .CLK(clknet_leaf_9_clk_npu));'
    sink=row['hold_target']['body']
    rest='sg13g2_buf_8 unrelated (.A(upstream), .X(out));'
    if fault=='wrong_driver_master':driver=driver.replace('dfrbpq','dfsbp')
    if fault=='wrong_driver_pin':driver=driver.replace('.Q(','.DUMMY(')
    if fault=='wrong_source_net':driver=driver.replace('mosi_s [0]','mosi_s [2]')
    if fault=='wrong_sink_body':sink=sink.replace('.RESET_B(net6187)','.RESET_B(other)')
    if fault=='extra_sink':rest+='\nsg13g2_inv_1 extra (.A(\\u_npu.u_node0.mosi_s [0]), .Y(other));'
    if fault=='duplicate_driver':rest+='\n'+driver
    if fault=='missing_driver':driver=''
    if fault=='existing_buffer':rest+='\nsg13g2_dlygate4sd3_1 nssoc_explicit_sd31 (.A(x),.X(y));'
    netlist=tmp_path/'soc_top.v';netlist.write_text('module soc_top;\n '+driver+'\n '+sink+'\n '+rest+'\nendmodule\n')
    rows=['instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus',
        '_135214_\tsg13g2_dfrbpq_1\t50400\t30240\tR0\tPLACED',
        '_135215_\tsg13g2_dfrbpq_1\t90000\t30240\tR0\tPLACED',
        'unrelated\tsg13g2_buf_8\t100000\t30240\tR0\tPLACED']
    if fault=='missing_placement':rows.pop(1)
    if fault=='duplicate_placement':rows.append(rows[1])
    if fault=='wrong_placement_master':rows[1]=rows[1].replace('dfrbpq','dfsbp')
    if fault=='wrong_header':rows[0]=rows[0].replace('x_dbu','x_um')
    place=tmp_path/'placement.tsv';place.write_text('\n'.join(rows)+'\n')
    row['candidate_files']['soc_top.v']=m.eco.file_pin(netlist);row['source_placement_pin']=m.eco.file_pin(place)
    if fault=='netlist_pin':netlist.write_text(netlist.read_text()+'//changed')
    if fault=='placement_pin':place.write_text(place.read_text()+'changed')
    return row,netlist,place


def test_frozen_chain_preserves_rejected_parent_and_all_six_guards():
    row=m.lock(ROOT)
    assert len(row['frozen_method_pins'])==56
    assert row['producer_rejected_guard']['no_regression']['combined_parent'] is False
    assert row['baseline_metrics']['instance_count']==103906
    assert row['insertion']['radius_um']==10


@pytest.mark.parametrize('fault',['runtime','producer','artifact','insertion','radius','drop_method','drop_reference','accepted_parent'])
def test_lock_rejects_scope_or_parent_substitution(tmp_path,monkeypatch,fault):
    row=locked()
    if fault=='runtime':row['runtime_sha256']='0'*64
    if fault=='producer':row['producer']['source_commit']='0'*40
    if fault=='artifact':row['producer']['artifact_id']+=1
    if fault=='insertion':row['insertion']['master']='sg13g2_buf_1'
    if fault=='radius':row['insertion']['radius_um']=100
    if fault=='drop_method':row['frozen_method_pins'].pop(next(iter(row['frozen_method_pins'])))
    if fault=='drop_reference':row['historical_reference_metrics'].pop('combined_parent')
    if fault=='accepted_parent':row['producer_rejected_guard']['candidate_adopted']=True
    p=tmp_path/m.LOCK;p.parent.mkdir(parents=True);p.write_text(json.dumps(row))
    monkeypatch.setattr(m.common,'verify_file',lambda *args:None)
    with pytest.raises(ValueError):m.lock(tmp_path)


def test_real_export_syntax_pins_exact_two_endpoint_branch(tmp_path):
    row,netlist,place=fixture(tmp_path)
    binding=m.target_binding(netlist,place,row)
    assert binding['terminals']==[['_135214_','sg13g2_dfrbpq_1','Q'],['_135215_','sg13g2_dfrbpq_1','D']]
    script=m.baseline_script(row,binding)
    assert 'u_npu.u_node0.mosi_s[0]' in script
    result=subprocess.run(['tclsh'],input=script+'puts [dict get $nssoc_explicit_places _135214_]\n',capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='50400 30240 R0 PLACED'


@pytest.mark.parametrize('fault',['wrong_driver_master','wrong_driver_pin','wrong_source_net','wrong_sink_body',
    'extra_sink','duplicate_driver','missing_driver','existing_buffer','missing_placement','duplicate_placement',
    'wrong_placement_master','wrong_header','netlist_pin','placement_pin'])
def test_binding_rejects_unproven_source_graph_or_placement(tmp_path,fault):
    row,netlist,place=fixture(tmp_path,fault)
    with pytest.raises((ValueError,KeyError)):m.target_binding(netlist,place,row)


def inserted(before):
    after=before.replace('.D(\\u_npu.u_node0.mosi_s [0])','.D(nssoc_explicit_holdnet1)')
    return after.replace('endmodule','sg13g2_dlygate4sd3_1 nssoc_explicit_sd31 (.A(\\u_npu.u_node0.mosi_s [0]), .X(nssoc_explicit_holdnet1));\nendmodule')


def test_single_positive_delay_contracts_all_original_equations(tmp_path):
    _,nl,_=fixture(tmp_path);before=nl.read_text()
    assert m.validate_single_buffer(before,inserted(before))['added_instances']==1


@pytest.mark.parametrize('fault',['master','old_master','old_pin','removed_cell','second_cell','wrong_input','reversed_delay','wrong_sink','extra_load'])
def test_single_delay_does_not_hide_another_eco(tmp_path,fault):
    _,nl,_=fixture(tmp_path);before=nl.read_text();after=inserted(before)
    if fault=='master':after=after.replace('dlygate4sd3_1','inv_1')
    if fault=='old_master':after=after.replace('buf_8','buf_4')
    if fault=='old_pin':after=after.replace('.X(out)','.X(upstream)')
    if fault=='removed_cell':after=after.replace('sg13g2_buf_8 unrelated (.A(upstream), .X(out));','')
    if fault=='second_cell':after=after.replace('endmodule','sg13g2_buf_1 extra (.A(x),.X(y));endmodule')
    if fault=='wrong_input':after=after.replace('.A(\\u_npu.u_node0.mosi_s [0])','.A(other)')
    if fault=='reversed_delay':after=after.replace('.A(\\u_npu.u_node0.mosi_s [0]), .X(nssoc_explicit_holdnet1)', '.X(\\u_npu.u_node0.mosi_s [0]), .A(nssoc_explicit_holdnet1)')
    if fault=='wrong_sink':after=after.replace('.D(nssoc_explicit_holdnet1)','.D(upstream)')
    if fault=='extra_load':after=after.replace('.A(upstream)','.A(nssoc_explicit_holdnet1)')
    with pytest.raises(ValueError):m.validate_single_buffer(before,after)


def test_guard_retains_original_combined_hold_regression():
    row=locked();baseline=dict(row['baseline_metrics'],recorded_ms=1)
    metrics={stage:baseline for stage in m.STAGES}
    g=m.guard(metrics,row,True,True)
    assert g['no_regression']['combined_parent'] is False
    assert g['aggregate_estimate_guard_passed'] is False
    assert not g['candidate_adopted'] and not g['timing_accepted']


def test_guard_requires_every_old_metric_plus_fresh_and_no_automatic_adoption():
    row=locked();before=dict(row['baseline_metrics'],recorded_ms=1)
    after=dict(before,hold_wns_seconds=-0.1e-9,hold_tns_seconds=-1.5e-9,hold_violating_endpoints=57)
    metrics={stage:before if stage=='candidate_before' else after for stage in m.STAGES}
    assert m.guard(metrics,row,True,True)['aggregate_estimate_guard_passed']
    assert not m.guard(metrics,row,False,True)['aggregate_estimate_guard_passed']
    assert not m.guard(metrics,row,True,False)['aggregate_estimate_guard_passed']
    for field,value in [('setup_wns_seconds',before['setup_wns_seconds']-1e-12),('slew_violations',1),('capacitance_violations',1)]:
        bad=copy.deepcopy(metrics);bad['reload_repeat'][field]=value
        assert not m.guard(bad,row,True,True)['aggregate_estimate_guard_passed']


def placement_fixture(tmp_path,fault=None):
    row,nl,path=fixture(tmp_path);binding=m.target_binding(nl,path,row)
    (tmp_path/'candidate_before').mkdir();(tmp_path/'candidate_before/placement.tsv').write_bytes(path.read_bytes())
    insertion=dict(buffer='nssoc_explicit_sd31',new_net='nssoc_explicit_holdnet1',original_net=m.INSERTION['native_net'],driver='_135214_',sink='_135215_',master='sg13g2_dlygate4sd3_1',radius_um=10,orientation='MX',initial_instances=3,initial_nets=10,location_dbu=[50400,34020],distance_dbu=3780,dbu_per_micron=1000,row_name='ROW_1')
    for stage in m.STAGES[1:]:
        (tmp_path/stage).mkdir();s=path.read_text()+'nssoc_explicit_sd31\tsg13g2_dlygate4sd3_1\t50400\t34020\tMX\tPLACED\n'
        if stage=='reload_repeat':
            if fault=='old_movement':s=s.replace('\t90000\t','\t90480\t')
            if fault=='old_orientation':s=s.replace('\tR0\t','\tMY\t')
            if fault=='old_status':s=s.replace('\tR0\tPLACED','\tR0\tFIRM')
            if fault=='new_movement':s=s.replace('\t34020\t','\t37800\t')
            if fault=='new_master':s=s.replace('dlygate4sd3_1','dlygate4sd2_1')
            if fault=='duplicate':s+=s.splitlines()[-1]+'\n'
        (tmp_path/stage/'placement.tsv').write_text(s)
    if fault=='wrong_distance':insertion['distance_dbu']+=1
    return row,insertion,binding


def test_full_original_placement_is_exact_at_every_stage(tmp_path):
    row,ins,b=placement_fixture(tmp_path)
    assert m.placement_contract(tmp_path,row,ins,b)['all_original_placements_and_statuses_equal']


@pytest.mark.parametrize('fault',['old_movement','old_orientation','old_status','new_movement','new_master','duplicate','wrong_distance'])
def test_placement_cannot_waive_legalization_changes(tmp_path,fault):
    row,ins,b=placement_fixture(tmp_path,fault)
    with pytest.raises(ValueError):m.placement_contract(tmp_path,row,ins,b)


def test_native_routing_step_and_child_do_not_run_placement_or_repair():
    for name in (m.HELPER,m.STEP,m.CHILD):
        text=(ROOT/name).read_text()
        assert 'common/dpl.tcl' not in text
        assert '\ndetailed_placement' not in text and '\nrepair_timing' not in text
    child=(ROOT/m.CHILD).read_text()
    assert child.index('set child_views')<child.index('common/io.tcl')<child.index('dict for {key value} $child_views')<child.index('read_current_odb')
    assert 'CURRENT_ODB _SDC_IN STEP_DIR' in child
    assert 'NSSOC_EXPLICIT_ORIGINAL_OBJECT_SHA' in child


def test_native_token_environment_is_scrubbed(monkeypatch):
    monkeypatch.setattr(m,'BASE_ENVIRONMENT',lambda:dict(PATH='/bin',GH_TOKEN='secret',GITHUB_TOKEN='secret2'))
    assert m.clean_environment()=={'PATH':'/bin'}

def network(monkeypatch,fault=None):
    row=locked();trial=row['producer'];calls=[]
    run=dict(id=trial['run_id'],head_sha=trial['source_commit'],status='completed',conclusion='success',run_attempt=1,
             repository=dict(full_name=m.eco.REPOSITORY))
    meta=dict(id=trial['artifact_id'],workflow_run=dict(id=trial['run_id'],head_sha=trial['source_commit']),
              name=trial['artifact_name'],size_in_bytes=trial['bytes'],digest='sha256:'+trial['sha256'])
    if fault=='run_id':run['id']+=1
    if fault=='source':run['head_sha']='0'*40
    if fault=='failure':run['conclusion']='failure'
    if fault=='attempt':run['run_attempt']=2
    if fault=='repo':run['repository']['full_name']='other/repo'
    if fault=='artifact_id':meta['id']+=1
    if fault=='digest':meta['digest']='sha256:'+'0'*64
    if fault=='size':meta['size_in_bytes']-=1
    if fault=='artifact_run':meta['workflow_run']['id']+=1
    def api(path):
        calls.append(path)
        if path.startswith('actions/runs/'):return run
        if fault=='expired':raise subprocess.CalledProcessError(1,['gh'])
        return meta
    monkeypatch.setattr(m.eco,'github_json',api)
    monkeypatch.setattr(m.common,'download',lambda pin,path:path.write_bytes(b'cloud-proxy-fixture'))
    return trial,calls


def test_permanent_archive_keeps_exact_run_binding_when_artifact_metadata_expires(tmp_path,monkeypatch):
    trial,calls=network(monkeypatch,'expired')
    got=m.download_producer(trial,tmp_path/'archive.zip')
    assert not got['artifact_metadata_available'] and len(calls)==2
    assert got['run']['id']==trial['run_id']


@pytest.mark.parametrize('fault',['run_id','source','failure','attempt','repo','artifact_id','digest','size','artifact_run'])
def test_available_wrong_source_metadata_cannot_use_release_fallback(tmp_path,monkeypatch,fault):
    trial,_=network(monkeypatch,fault)
    with pytest.raises(ValueError):m.download_producer(trial,tmp_path/'archive.zip')
    assert not (tmp_path/'archive.zip').exists()


def parent_fixture(row):
    return dict(status='COMPLETE_DIAGNOSTIC_ONLY',github_source_commit=row['producer']['source_commit'],
        method_files=row['frozen_method_pins'],diagnostic=dict(native=dict(candidate_files=row['candidate_files'],
        timing_metrics=dict(reload_repeat=dict(row['baseline_metrics'],recorded_ms=1))),
        independently_checked_stages=dict(reload_repeat=dict(fingerprints=row['baseline_fingerprints'])),
        aggregate_guard_assessment=row['producer_rejected_guard']))


def test_parent_rejected_disposition_is_replayed_exactly():
    row=locked();m.validate_parent_contract(parent_fixture(row),row)


@pytest.mark.parametrize('fault',['source','views','methods','metric','fingerprint','rejected_guard'])
def test_parent_contract_cannot_claim_prior_acceptance(fault):
    row=locked();parent=copy.deepcopy(parent_fixture(row))
    if fault=='source':parent['github_source_commit']='0'*40
    if fault=='views':parent['diagnostic']['native']['candidate_files']['soc_top.odb']['sha256']='0'*64
    if fault=='methods':parent['method_files'].pop(next(iter(parent['method_files'])))
    if fault=='metric':parent['diagnostic']['native']['timing_metrics']['reload_repeat']['hold_wns_seconds']=0
    if fault=='fingerprint':parent['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints']['placement']='0'*64
    if fault=='rejected_guard':parent['diagnostic']['aggregate_guard_assessment']['aggregate_estimate_guard_passed']=True
    with pytest.raises(ValueError):m.validate_parent_contract(parent,row)


def test_missing_method_inventory_is_not_silently_skipped():
    assert len(m.SOURCES)==len(set(m.SOURCES)) and set(m.OWN).issubset(m.SOURCES)
    assert set(m.original.SOURCES).issubset(m.SOURCES)
    for path in m.SOURCES:assert (ROOT/path).is_file(),path


def small_control(tmp_path):
    root=tmp_path/'control';root.mkdir()
    (root/'before.sdc').write_text('same exact constraints\n');(root/'after.sdc').write_bytes((root/'before.sdc').read_bytes())
    for name in ('graph-before.tsv','graph-after-contracted.tsv'): (root/name).write_text('same graph\n')
    for name in ('objects-before.tsv','objects-after-contracted.tsv'): (root/name).write_text('same objects\n')
    insertion=dict(master='sg13g2_dlygate4sd3_1',initial_instances=3,driver='driver',sink='sink',original_net='target',buffer='nssoc_explicit_sd31',new_net='nssoc_explicit_holdnet1',location_dbu=[50400,34020],orientation='MX',distance_dbu=3780,dbu_per_micron=1000,radius_um=10)
    row=dict(status='PASS_NATIVE_EXPLICIT_HOLD_CONTROL',negative_control_messages={k:'rejected' for k in m.CONTROL_NEGATIVES},
        pre_sdc_sha256=m.common.sha(root/'before.sdc'),post_sdc_sha256=m.common.sha(root/'after.sdc'),insertion=insertion,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
        before_metrics={c:dict(min_slack_ns=-0.1,max_slack_ns=18.) for c in ('fast','typical','slow')},
        after_metrics={c:dict(min_slack_ns=0.2,max_slack_ns=17.4) for c in ('fast','typical','slow')})
    row['negative_control_messages']['native_overlap']='DPL-0033'
    for flag in ('independently_predicted_nearest_vacancy','deterministic_vacancy','full_graph_contraction_preserved',
        'all_original_placements_preserved','no_detailed_placement_called','pg_bindings_preserved',
        'all_three_corners_loaded_and_timed','constraints_preserved','placement_parasitic_tiny_control_only'):row[flag]=True
    for corner in ('fast','typical','slow'):(root/f'after-{corner}.rpt').write_text(f'Corner: {corner}\nnssoc_explicit_sd31/X (sg13g2_dlygate4sd3_1)\n')
    (root/'result.json').write_text(json.dumps(row))
    log=tmp_path/'native.log';log.write_text('PASS_NATIVE_EXPLICIT_HOLD_CONTROL_NO_CHIP_ACCEPTANCE\n')
    return root,log,row


def test_native_fixture_receipt_requires_raw_unchanged_source_and_measured_three_corner_paths(tmp_path):
    root,log,_=small_control(tmp_path)
    assert len(m.validate_native_control(root,log)['negative_control_messages'])==39


@pytest.mark.parametrize('fault',['negative_omitted','negative_empty','movement','acceptance','radius','location','buffer',
    'corner_omitted','hold_not_improved','nan_metric','missing_delay_path','graph','sdc','overlap_not_native','marker'])
def test_native_control_rejects_missing_or_inconsistent_evidence(tmp_path,fault):
    root,log,row=small_control(tmp_path)
    if fault=='negative_omitted':row['negative_control_messages'].pop('wrong_net')
    if fault=='negative_empty':row['negative_control_messages']['wrong_net']=''
    if fault=='movement':row['all_original_placements_preserved']=False
    if fault=='acceptance':row['candidate_adopted']=True
    if fault=='radius':row['insertion']['radius_um']=11
    if fault=='location':row['insertion']['location_dbu']=[50480,34020]
    if fault=='buffer':row['insertion']['master']='sg13g2_buf_1'
    if fault=='corner_omitted':row['after_metrics'].pop('slow')
    if fault=='hold_not_improved':row['after_metrics']['fast']['min_slack_ns']=-0.2
    if fault=='nan_metric':row['after_metrics']['fast']['min_slack_ns']=float('nan')
    if fault=='missing_delay_path':(root/'after-slow.rpt').write_text('Corner: slow\n')
    if fault=='graph':(root/'graph-after-contracted.tsv').write_text('different graph\n')
    if fault=='sdc':(root/'after.sdc').write_text('changed clock\n')
    if fault=='overlap_not_native':row['negative_control_messages']['native_overlap']='early equality guard'
    if fault=='marker':log.write_text('')
    (root/'result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):m.validate_native_control(root,log)


def test_capture_includes_only_three_bound_tiny_physical_views(tmp_path,monkeypatch):
    output=tmp_path/'source';where=output/'run/01-openroad-resizertimingpostgrt/explicit-control';where.mkdir(parents=True)
    destination=tmp_path/'capture';destination.mkdir()
    for name in ('before.odb','after.odb','after.def'):(where/name).write_bytes(name.encode())
    monkeypatch.setattr(m.parent,'capture',lambda *args:dict(files={}))
    got=m.capture(output,destination)
    assert len(got['files'])==3
    for rel,pin in got['files'].items():
        assert (destination/rel).read_bytes()==(output/rel).read_bytes()
        assert not pin['source_truncated_during_copy'] and pin['sha256']==m.common.sha(output/rel)


def test_capture_rejects_unexpected_tiny_physical_view(tmp_path,monkeypatch):
    output=tmp_path/'source';where=output/'run/01-openroad-resizertimingpostgrt/explicit-control';where.mkdir(parents=True)
    (where/'unreviewed.odb').write_bytes(b'bad');destination=tmp_path/'capture';destination.mkdir()
    monkeypatch.setattr(m.parent,'capture',lambda *args:dict(files={}))
    with pytest.raises(ValueError):m.capture(output,destination)


def test_child_preserves_only_intended_view_bindings_across_actual_tcl_source_reset(tmp_path):
    # Run the real child prefix in Tcl with only native API leaves mocked. The
    # deliberately resetting io.tcl is the historical cause of wrong ODB loads.
    child=ROOT/m.CHILD
    stub=r'''
rename source original_source
proc source {path} {
    if {[string match */common/io.tcl $path]} {
        foreach key {CURRENT_ODB _SDC_IN STEP_DIR} {set ::env($key) original-wrong-view}
    } elseif {[string match */common/resizer.tcl $path]} {
        return
    } elseif {[string match *timing_explicit_hold_reload.tcl $path]} {
        uplevel 1 [list original_source $path]
    }
}
proc nssoc_hold_sha {path} {return fixed_sha}
proc nssoc_combined_read {path} {return {buffer added}}
proc read_current_odb {} {
    puts "VIEWS=$::env(CURRENT_ODB)|$::env(_SDC_IN)|$::env(STEP_DIR)"
    exit 0
}
set ::env(NSSOC_HOLD_DIAGNOSTIC_HELPER) ignored
set ::env(NSSOC_TARGETED_METHOD_ROOT) ignored
set ::env(SCRIPTS_DIR) ignored
set ::env(NSSOC_COMBINED_ROOT) root
set ::env(NSSOC_COMBINED_RELOAD_STAGE) reload_first
foreach key {CURRENT_ODB _SDC_IN STEP_DIR} {set ::env($key) intended-$key}
foreach key {NSSOC_COMBINED_ODB_SHA NSSOC_COMBINED_SDC_SHA NSSOC_TARGETED_ACTUAL_ELF_SHA256 NSSOC_EXPLICIT_INSERTION_SHA} {set ::env($key) fixed_sha}
set ::env(NSSOC_EXPLICIT_INSERTION_FILE) insertion
'''
    command=stub+'\nsource {'+str(child)+'}\n'
    result=subprocess.run(['tclsh'],input=command,capture_output=True,text=True,check=True)
    assert result.stderr=='' and result.stdout.strip()=='VIEWS=intended-CURRENT_ODB|intended-_SDC_IN|intended-STEP_DIR'
