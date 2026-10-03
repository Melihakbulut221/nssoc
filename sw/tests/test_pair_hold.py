# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound two-delay continuation; no chip or network execution."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_pair_hold as m  # noqa: E402


def locked():return json.loads((ROOT/m.LOCK).read_text())


def expression(native):
    if '.' not in native:return native
    if '[' in native:return '\\'+native.replace('[',' [')
    return '\\'+native


def fixture(tmp_path,fault=None):
    lock=locked();cells=[];places=['instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus']
    for target in lock['target_witnesses']:
        for name,witness in target['native_cell_witnesses'].items():
            ports={k:expression(witness['pins'][k]['net']) for k in ('CLK','RESET_B','D','Q')}
            master=witness['master']
            if name=='_134732_':
                if fault=='wrong_master':master='sg13g2_dfstp_1'
                if fault=='reset':ports['RESET_B']='bad'
                if fault=='clock':ports['CLK']='bad'
                if fault=='target_net':ports['Q']='bad'
                if fault=='missing_pin':ports.pop('CLK')
            body=' '+master+' '+name+' ('+', '.join('.'+p+'('+v+')' for p,v in ports.items())+');'
            if not(fault=='missing_cell' and name=='_134732_'):cells.append(body)
            if fault=='duplicate_cell' and name=='_134732_':cells.append(body)
            row=dict(witness['placement'])
            if name=='_134732_' and fault=='moved':row['x_dbu']=str(int(row['x_dbu'])+480)
            if name=='_134732_' and fault=='wrong_orientation':row['orientation']='MY'
            if not(fault=='missing_place' and name=='_134732_'):places.append('\t'.join(row[k] for k in ('instance','master','x_dbu','y_dbu','orientation','status')))
    old=lock['preserved_original_delay'];cells.append(' sg13g2_dlygate4sd3_1 '+old['buffer']+' (.A(oldinput), .X(oldoutput));')
    places.append(old['buffer']+'\tsg13g2_dlygate4sd3_1\t1711680\t1935360\tR0\tPLACED')
    if fault=='old_delay_missing':cells.pop()
    if fault=='new_prefix':cells.append(' sg13g2_dlygate4sd3_1 nssoc_pair0_sd31 (.A(x), .X(y));')
    if fault=='extra_sink':cells.append(' sg13g2_buf_1 extra (.A(_062302_), .X(y));')
    if fault=='duplicate_place':places.append(places[1])
    nl=tmp_path/'soc_top.v';nl.write_text('module soc_top;\n'+'\n'.join(cells)+'\nendmodule\n')
    placement=tmp_path/'placement.tsv';placement.write_text('\n'.join(places)+'\n')
    lock['candidate_files']['soc_top.v']=m.eco.file_pin(nl);lock['source_placement_pin']=m.eco.file_pin(placement)
    if fault=='nl_pin':nl.write_text(nl.read_text()+'// changed')
    if fault=='place_pin':placement.write_text(placement.read_text()+'changed')
    return lock,nl,placement


def test_exact_existing_single_producer_and_all_history():
    row=m.lock(ROOT)
    assert len(row['frozen_method_pins'])==64 and len(row['historical_reference_metrics'])==8
    assert row['baseline_metrics']['instance_count']==103907
    assert row['producer_guard']['aggregate_estimate_guard_passed'] is True
    assert row['producer_guard']['candidate_adopted'] is False


@pytest.mark.parametrize('fault',['runtime','source','artifact','target','radius','drop_method','drop_reference','adoption'])
def test_lock_fail_closed(tmp_path,monkeypatch,fault):
    row=locked()
    if fault=='runtime':row['runtime_sha256']='0'*64
    if fault=='source':row['producer']['source_commit']='0'*40
    if fault=='artifact':row['producer']['artifact_id']+=1
    if fault=='target':row['insertions'][1]['driver']='other'
    if fault=='radius':row['insertions'][0]['radius_um']=11
    if fault=='drop_method':row['frozen_method_pins'].pop(next(iter(row['frozen_method_pins'])))
    if fault=='drop_reference':row['historical_reference_metrics'].pop('combined_parent')
    if fault=='adoption':row['producer_guard']['candidate_adopted']=True
    path=tmp_path/m.LOCK;path.parent.mkdir(parents=True);path.write_text(json.dumps(row))
    monkeypatch.setattr(m.common,'verify_file',lambda *a:None)
    with pytest.raises(ValueError):m.lock(tmp_path)


def test_native_equations_and_places_make_valid_Tcl(tmp_path):
    row,nl,place=fixture(tmp_path);binding=m.target_binding(nl,place,row)
    script=m.baseline_script(row,binding)
    result=subprocess.run(['tclsh'],input=script+'puts [llength $nssoc_pair_targets]\nputs [dict get [lindex $nssoc_pair_targets 1] net]\n',text=True,capture_output=True,check=True)
    assert result.stdout.splitlines()==['2','u_npu.u_node0.sck_s[0]']
    assert [t['insertion'] for t in binding['targets']]==list(m.INSERTIONS)


@pytest.mark.parametrize('fault',['wrong_master','reset','clock','target_net','missing_pin','missing_cell','duplicate_cell',
    'moved','wrong_orientation','missing_place','old_delay_missing','new_prefix','extra_sink','duplicate_place','nl_pin','place_pin'])
def test_binding_faults_rejected(tmp_path,fault):
    row,nl,place=fixture(tmp_path,fault)
    with pytest.raises((KeyError,ValueError)):m.target_binding(nl,place,row)


@pytest.mark.parametrize('value',["1'b0",'a & b','\\a [00]','\\a [0:1]','a[0]','\\a [x]','a b'])
def test_native_expression_rejects_unwitnessed_syntax(value):
    with pytest.raises(ValueError):m.native_expression(value)


def inserted(text):
    for i,target in enumerate(m.INSERTIONS):
        new=target['new_net']+'37'
        text=text.replace('.D('+target['verilog_net']+')','.D('+new+')')
        text=text.replace('endmodule',' sg13g2_dlygate4sd3_1 '+target['buffer']+'37 (.A('+target['verilog_net']+'), .X('+new+'));\nendmodule')
    return text


def test_exact_two_buffers_keep_old_delay_and_all_equations(tmp_path):
    _,nl,_=fixture(tmp_path);before=nl.read_text()
    assert m.validate_pair_buffers(before,inserted(before))['added_instances']==2


@pytest.mark.parametrize('fault',['new_master','old_master','old_pin','extra_cell','reversed','wrong_sink','same_branch','wrong_input','missing_buffer'])
def test_full_logical_contraction_faults(tmp_path,fault):
    _,nl,_=fixture(tmp_path);before=nl.read_text();after=inserted(before)
    if fault=='new_master':after=after.replace('sg13g2_dlygate4sd3_1 nssoc_pair0','sg13g2_inv_1 nssoc_pair0')
    if fault=='old_master':after=after.replace('sg13g2_dlygate4sd3_1 nssoc_explicit','sg13g2_dlygate4sd2_1 nssoc_explicit')
    if fault=='old_pin':after=after.replace('.A(oldinput)','.A(other)')
    if fault=='extra_cell':after=after.replace('endmodule',' sg13g2_buf_1 extra (.A(a),.X(b));\nendmodule')
    if fault=='reversed':after=after.replace('.A(_062302_), .X(nssoc_pair0_net37)', '.X(_062302_), .A(nssoc_pair0_net37)')
    if fault=='wrong_sink':after=after.replace('.D(nssoc_pair0_net37)','.D(other)')
    if fault=='same_branch':after=after.replace('nssoc_pair1_net37','nssoc_pair0_net37')
    if fault=='wrong_input':after=after.replace('.A(_062302_)','.A(other)')
    if fault=='missing_buffer':after=after.replace('sg13g2_dlygate4sd3_1 nssoc_pair1_sd337','bad_syntax')
    with pytest.raises((ValueError,KeyError)):m.validate_pair_buffers(before,after)


def rows():
    result=[]
    for i,t in enumerate(m.INSERTIONS):
        result.append(dict(buffer=t['buffer']+'37',new_net=t['new_net']+'37',original_net=t['native_net'],
            driver=t['driver'],sink=t['sink'],master=t['master'],radius_um=10,orientation='MX',initial_instances=5+i,
            initial_nets=10+i,location_dbu=[0,0],distance_dbu=3780,dbu_per_micron=1000,row_name='ROW'))
    return result


@pytest.mark.parametrize('fault',['missing','duplicate','third','master','prefix','target','count','nets','radius','negative_distance','float_position'])
def test_exact_observed_pair_contract_rejects_mutations(fault):
    ins=rows()
    if fault=='missing':ins.pop()
    if fault=='duplicate':ins[1]=copy.deepcopy(ins[0])
    if fault=='third':ins.append(copy.deepcopy(ins[1]))
    if fault=='master':ins[0]['master']='sg13g2_buf_1'
    if fault=='prefix':ins[0]['buffer']='nssoc_explicit_sd31'
    if fault=='target':ins[1]['original_net']=ins[0]['original_net']
    if fault=='count':ins[1]['initial_instances']+=1
    if fault=='nets':ins[1]['initial_nets']+=1
    if fault=='radius':ins[0]['radius_um']=20
    if fault=='negative_distance':ins[0]['distance_dbu']=-1
    if fault=='float_position':ins[1]['location_dbu'][0]=0.5
    with pytest.raises(ValueError):m.insertion_contract(ins)


def test_all_original_placements_stay_identical(tmp_path):
    row,nl,path=fixture(tmp_path);binding=m.target_binding(nl,path,row);ins=rows();before=path.read_text()
    (tmp_path/'candidate_before').mkdir();(tmp_path/'candidate_before/placement.tsv').write_text(before)
    for i,t in enumerate(binding['targets']):
        driver=t['native_placement'][t['insertion']['driver']];ins[i]['location_dbu']=[int(driver['x_dbu']),int(driver['y_dbu'])+3780]
    after=before+''.join('\t'.join([x['buffer'],x['master'],*map(str,x['location_dbu']),x['orientation'],'PLACED'])+'\n' for x in ins)
    for stage in m.STAGES[1:]:(tmp_path/stage).mkdir();(tmp_path/stage/'placement.tsv').write_text(after)
    assert m.placement_contract(tmp_path,row,ins,binding)['added_instances']==2
    # Moving only the pre-existing single delay is still forbidden.
    q=tmp_path/'reload_repeat/placement.tsv';q.write_text(after.replace('\t1711680\t','\t1712160\t'))
    with pytest.raises(ValueError):m.placement_contract(tmp_path,row,ins,binding)


def test_guards_keep_all_eight_refs_and_fresh_parent():
    row=locked();before=dict(row['baseline_metrics'],recorded_ms=1)
    after=dict(before,hold_wns_seconds=-0.09e-9,hold_tns_seconds=-1.5e-9,hold_violating_endpoints=55)
    metrics={s:before if s=='candidate_before' else after for s in m.STAGES}
    good=m.guard(metrics,row,True,True)
    assert len(good['no_regression'])==9 and good['aggregate_estimate_guard_passed']
    assert not good['candidate_adopted'] and not good['timing_accepted'] and not good['manufacturing_approval']
    assert not m.guard(metrics,row,False,True)['aggregate_estimate_guard_passed']
    assert not m.guard(metrics,row,True,False)['aggregate_estimate_guard_passed']
    for field,value in [('setup_wns_seconds',before['setup_wns_seconds']-1e-12),('slew_violations',1),('capacitance_violations',1)]:
        bad=copy.deepcopy(metrics);bad['reload_repeat'][field]=value
        assert not m.guard(bad,row,True,True)['aggregate_estimate_guard_passed']


def test_immutable_helper_namespace_changes_prefixes_only():
    old=ROOT/m.single.HELPER
    assert hashlib.sha256(old.read_bytes()).hexdigest()=='6d12da88eaf4e6f93c945ae125c4395690225abc5fa6d1f8d5d05267707149fc'
    script='proc nssoc_hold_sha {path} {return 6d12da88eaf4e6f93c945ae125c4395690225abc5fa6d1f8d5d05267707149fc}\n'
    script+='set ::env(NSSOC_TARGETED_METHOD_ROOT) {'+str(ROOT)+'}\nsource {'+str(ROOT/m.HELPER)+'}\n'
    script+='''
foreach index {0 1} {
 foreach name [info procs ::nssoc_explicit_*] {
  set local ::nssoc_pair_${index}::[namespace tail $name]
  if {[info args $name] ne [info args $local]} {error "Arguments changed"}
  set expected [string map [list nssoc_explicit_sd3 nssoc_pair${index}_sd3 nssoc_explicit_holdnet nssoc_pair${index}_net] [info body $name]]
  if {$expected ne [info body $local]} {error "Unexpected body mutation"}
 }
}
if {[nssoc_pair_contract {}] ne {{} {}}} {error "Empty before-contract differs"}
puts PREFIX_ONLY_REUSE_PASS
'''
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
    assert p.stderr=='' and p.stdout.strip()=='PREFIX_ONLY_REUSE_PASS'


def test_child_environment_restoration_and_no_new_repair():
    for name in (m.HELPER,m.STEP,m.CHILD):
        text=(ROOT/name).read_text();assert 'common/dpl.tcl' not in text and '\ndetailed_placement' not in text and '\nrepair_timing' not in text
    child=(ROOT/m.CHILD).read_text()
    assert child.index('set child_views')<child.index('common/io.tcl')<child.index('dict for {key value} $child_views')<child.index('read_current_odb')
    assert 'CURRENT_ODB _SDC_IN STEP_DIR' in child
    workflow=(ROOT/'.github/workflows/timing-pair-hold.yml').read_text()
    assert 'fetch-depth: 0' in workflow and 'actions: read' in workflow and 'include-hidden-files: true' in workflow
    assert 'cancel-in-progress: false' in workflow and 'GH_TOKEN:' in workflow


def test_native_token_environment_scrubbed(monkeypatch):
    monkeypatch.setattr(m,'BASE_ENVIRONMENT',lambda:dict(PATH='/bin',GH_TOKEN='secret',GITHUB_TOKEN='other'))
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
        aggregate_guard_assessment=row['producer_guard']))


def test_parent_limited_improvement_scope_is_replayed_exactly():
    row=locked();m.validate_parent_contract(parent_fixture(row),row)


@pytest.mark.parametrize('fault',['source','views','methods','metric','fingerprint','rejected_guard'])
def test_parent_contract_cannot_claim_prior_acceptance(fault):
    row=locked();parent=copy.deepcopy(parent_fixture(row))
    if fault=='source':parent['github_source_commit']='0'*40
    if fault=='views':parent['diagnostic']['native']['candidate_files']['soc_top.odb']['sha256']='0'*64
    if fault=='methods':parent['method_files'].pop(next(iter(parent['method_files'])))
    if fault=='metric':parent['diagnostic']['native']['timing_metrics']['reload_repeat']['hold_wns_seconds']=0
    if fault=='fingerprint':parent['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints']['placement']='0'*64
    if fault=='rejected_guard':parent['diagnostic']['aggregate_guard_assessment']['candidate_adopted']=True
    with pytest.raises(ValueError):m.validate_parent_contract(parent,row)


def test_missing_method_inventory_is_not_silently_skipped():
    assert len(m.SOURCES)==len(set(m.SOURCES)) and set(m.OWN).issubset(m.SOURCES)
    assert set(m.original.SOURCES).issubset(m.SOURCES)
    for path in m.SOURCES:assert (ROOT/path).is_file(),path




def test_capture_preserves_all_four_native_views_and_exact_inventory(tmp_path):
    # The real parent capture skips physical files; exercise the actual bridge,
    # including before.def emitted by the frozen native fixture's write_def.
    output=tmp_path/'source';where=output/'run/01-openroad-resizertimingpostgrt/pair-control';where.mkdir(parents=True)
    (output/'result.json').write_text(json.dumps(dict(status='COMPLETE_DIAGNOSTIC_ONLY')))
    (where/'result.json').write_text('{}\n')
    for name in ('before.odb','before.def','after.odb','after.def'):
        (where/name).write_bytes(name.encode()+bytes(range(256)))
    destination=tmp_path/'capture';got=m.capture(output,destination)
    assert len(got['files'])==6
    assert set(m.shared.file_inventory(destination))==set(got['files'])|{'capture.json'}
    assert json.loads((destination/'capture.json').read_text())==got
    for rel,pin in got['files'].items():
        assert (destination/rel).read_bytes()==(output/rel).read_bytes()
        assert not pin['source_truncated_during_copy'] and pin['sha256']==m.common.sha(output/rel)
    assert got['complete_diagnostic_evidence'] is True
    assert got['candidate_adopted'] is False


@pytest.mark.parametrize('name',['unreviewed.odb','unreviewed.def'])
def test_capture_rejects_unexpected_tiny_physical_view(tmp_path,name):
    output=tmp_path/'source';where=output/'run/01-openroad-resizertimingpostgrt/pair-control';where.mkdir(parents=True)
    (output/'result.json').write_text(json.dumps(dict(status='COMPLETE_DIAGNOSTIC_ONLY')))
    (where/name).write_bytes(b'bad')
    with pytest.raises(ValueError,match='Unexpected tiny physical evidence'):
        m.capture(output,tmp_path/'capture')


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
    } elseif {[string match *timing_pair_hold_reload.tcl $path]} {
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
foreach key {NSSOC_COMBINED_ODB_SHA NSSOC_COMBINED_SDC_SHA NSSOC_TARGETED_ACTUAL_ELF_SHA256 NSSOC_PAIR_INSERTION_SHA} {set ::env($key) fixed_sha}
set ::env(NSSOC_PAIR_INSERTION_FILE) insertion
'''
    command=stub+'\nsource {'+str(child)+'}\n'
    result=subprocess.run(['tclsh'],input=command,capture_output=True,text=True,check=True)
    assert result.stderr=='' and result.stdout.strip()=='VIEWS=intended-CURRENT_ODB|intended-_SDC_IN|intended-STEP_DIR'


def small_control(tmp_path):
    root=tmp_path/'native';root.mkdir()
    for name in ('before.sdc','after.sdc'):(root/name).write_text('original constraints\n')
    for prefix in ('graph','objects'):
        for suffix in ('before','after-contracted'):(root/(prefix+'-'+suffix+'.tsv')).write_text(prefix+' unchanged\n')
    inserted=[]
    for i in (0,1):
        inserted.append(dict(master='sg13g2_dlygate4sd3_1',initial_instances=5+i,initial_nets=12+i,driver='driver'+str(i),sink='sink'+str(i),original_net='target'+str(i),buffer=f'nssoc_pair{i}_sd3{i+1}',new_net=f'nssoc_pair{i}_net{i+1}',location_dbu=[50400,34020+7560*i],orientation='MX',distance_dbu=3780,dbu_per_micron=1000,radius_um=10))
        for c in ('fast','typical','slow'):(root/f'after-branch{i}-{c}.rpt').write_text(f'Corner: {c}\n'+inserted[-1]['buffer']+'/X (sg13g2_dlygate4sd3_1)\n')
    row=dict(status='PASS_NATIVE_PAIR_HOLD_CONTROL',insertions=inserted,
        negative_control_messages={k:('DPL-0033' if k.startswith('native_overlap_') else 'rejected') for k in m.CONTROL_NEGATIVES},
        pre_sdc_sha256=m.common.sha(root/'before.sdc'),post_sdc_sha256=m.common.sha(root/'after.sdc'),
        initial_instances=5,final_instances=7,initial_nets=12,final_nets=14,
        first_vacancy='3780 50400 34020 ROW_7 MX',second_original_vacancy='3780 50400 34020 ROW_7 MX',second_actual_vacancy='3780 50400 41580 ROW_9 MX',
        before_metrics={f'target{i}':{c:dict(min_slack_ns=.1,max_slack_ns=19.) for c in ('fast','typical','slow')} for i in (0,1)},
        after_metrics={f'target{i}':{c:dict(min_slack_ns=.35,max_slack_ns=18.4) for c in ('fast','typical','slow')} for i in (0,1)},
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False)
    for flag in ('full_graph_contraction_preserved','all_original_placements_preserved','first_insertion_is_second_obstacle','preserved_original_delay','no_detailed_placement_called','pg_bindings_preserved','all_three_corners_loaded_and_timed','constraints_preserved','estimated_global_route_tiny_control_only'):row[flag]=True
    log=tmp_path/'native.log';log.write_text('PASS_NATIVE_PAIR_HOLD_CONTROL_NO_CHIP_ACCEPTANCE\n');(root/'result.json').write_text(json.dumps(row))
    return root,log,row


def test_native_capture_replays_two_routes_and_all74_faults(tmp_path):
    root,log,_=small_control(tmp_path)
    assert len(m.validate_native_control(root,log)['negative_control_messages'])==74


@pytest.mark.parametrize('fault',['omitted_fault','empty_fault','static_old_delay','missing_branch','wrong_location','wrong_prefix','missing_corner','no_hold_gain','nan','missing_path','sdc','graph','old_objects','false_obstacle','census','non_native_overlap','missing_marker','adoption'])
def test_native_pair_receipt_is_fail_closed(tmp_path,fault):
    root,log,row=small_control(tmp_path)
    if fault=='omitted_fault':row['negative_control_messages'].pop('omitted_branch')
    if fault=='empty_fault':row['negative_control_messages']['extra_net']=''
    if fault=='static_old_delay':row['preserved_original_delay']=False
    if fault=='missing_branch':row['insertions'].pop()
    if fault=='wrong_location':row['insertions'][1]['location_dbu']=[50400,34020]
    if fault=='wrong_prefix':row['insertions'][1]['buffer']='nssoc_pair0_sd32'
    if fault=='missing_corner':row['after_metrics']['target1'].pop('slow')
    if fault=='no_hold_gain':row['after_metrics']['target1']['fast']['min_slack_ns']=0.05
    if fault=='nan':row['after_metrics']['target1']['fast']['min_slack_ns']=float('nan')
    if fault=='missing_path':(root/'after-branch1-slow.rpt').write_text('Corner: slow\n')
    if fault=='sdc':(root/'after.sdc').write_text('changed clock')
    if fault=='graph':(root/'graph-after-contracted.tsv').write_text('changed equations')
    if fault=='old_objects':(root/'objects-after-contracted.tsv').write_text('moved oldsd3')
    if fault=='false_obstacle':row['second_actual_vacancy']=row['first_vacancy']
    if fault=='census':row['final_nets']=15
    if fault=='non_native_overlap':row['negative_control_messages']['native_overlap_1']='early guard only'
    if fault=='missing_marker':log.write_text('')
    if fault=='adoption':row['candidate_adopted']=True
    (root/'result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):m.validate_native_control(root,log)


@pytest.mark.parametrize('missing', sorted(locked()['producer']))
def test_complete_parent_acquisition_and_frozen_verifier_schema_required(tmp_path,monkeypatch,missing):
    row=locked();row['producer'].pop(missing)
    path=tmp_path/m.LOCK;path.parent.mkdir(parents=True);path.write_text(json.dumps(row))
    monkeypatch.setattr(m.common,'verify_file',lambda *a:None)
    with pytest.raises(ValueError,match='incomplete'):m.lock(tmp_path)


@pytest.mark.parametrize('field,value',[('kind','other_trial'),('entrypoint','scripts/other.py'),('candidate_prefix','wrong/views')])
def test_exact_parent_diagnostic_validator_view_bound_early(tmp_path,monkeypatch,field,value):
    row=locked();row['producer'][field]=value
    path=tmp_path/m.LOCK;path.parent.mkdir(parents=True);path.write_text(json.dumps(row))
    monkeypatch.setattr(m.common,'verify_file',lambda *a:None)
    with pytest.raises(ValueError,match='identity differs'):m.lock(tmp_path)


@pytest.mark.parametrize('fault',[None,'missing_kind','wrong_kind','wrong_entrypoint','wrong_git_blob','extra_method'])
def test_real_frozen_zip_extraction_and_producer_source_verifier(tmp_path,monkeypatch,fault):
    """Execute both immutable consumers; mock Git transport only, never guards."""
    import zipfile
    trial=locked()['producer'];entry=trial['entrypoint'];method=b'# exact original validator fixture\n'
    methods={entry:dict(bytes=len(method),sha256=hashlib.sha256(method).hexdigest())}
    record=dict(github_source_commit=trial['source_commit'],diagnostic_kind='explicit_single_sd3_hold_trial',
                manifest_sha256=m.eco.MANIFEST_SHA,method_files=methods)
    archive=tmp_path/'producer.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('result.json',json.dumps(record));z.writestr('methods/'+entry,method)
        if fault=='extra_method':z.writestr('methods/scripts/unrecorded.py',b'bad')
    capture=tmp_path/'capture';extracted=m.eco.extract_zip(archive,capture)
    assert extracted['files']==(3 if fault=='extra_method' else 2)
    calls=[]
    def git_bytes(commit,path):
        calls.append((commit,path));assert commit==trial['source_commit'] and path==entry
        return method if fault!='wrong_git_blob' else b'wrong immutable source'
    monkeypatch.setattr(m.eco,'git_bytes',git_bytes)
    if fault=='missing_kind':trial.pop('kind')
    if fault=='wrong_kind':trial['kind']='another_trial'
    if fault=='wrong_entrypoint':trial['entrypoint']='scripts/unknown.py'
    if fault:
        with pytest.raises((KeyError,ValueError)):m.eco.verify_producer_sources(capture,trial)
    else:
        assert m.eco.verify_producer_sources(capture,trial)==methods
        assert calls==[(trial['source_commit'],entry)]
