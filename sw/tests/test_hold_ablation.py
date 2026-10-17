# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent one-target ablations; no cloud or full-chip native execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_hold_ablation as m  # noqa: E402
import test_pair_hold as old_fixture  # noqa: E402


def locked():return json.loads((ROOT/m.LOCK).read_text())


def test_exact_parent_and_reusable_sources_remain_frozen():
    row=m.lock(ROOT)
    assert row['producer']['run_id']==37107650542
    assert len(row['frozen_method_pins'])==64 and len(row['reuse_method_pins'])==72
    assert row['baseline_metrics']['hold_violating_endpoints']==57
    assert row['baseline_metrics']['setup_violating_endpoints']==1310
    assert len(row['historical_reference_metrics'])==8
    assert row['producer_guard']['candidate_adopted'] is False


@pytest.mark.parametrize('fault',['variant','target','radius','reuse_missing','reuse_hash','parent_metric','parent_source','parent_adoption'])
def test_lock_rejects_mixed_parent_and_unbound_variant(tmp_path,monkeypatch,fault):
    row=locked()
    if fault=='variant':row['variants']['other']=row['variants']['eth']
    if fault=='target':row['variants']['eth']['driver']='wrong'
    if fault=='radius':row['variants']['eth']['radius_um']=20
    if fault=='reuse_missing':row['reuse_method_pins'].pop(next(iter(row['reuse_method_pins'])))
    if fault=='reuse_hash':row['reuse_method_pins'][m.pair.ENTRY]['sha256']='0'*64
    if fault=='parent_metric':row['baseline_metrics']['hold_violating_endpoints']=59
    if fault=='parent_source':row['producer']['run_id']=37130065441
    if fault=='parent_adoption':row['producer_guard']['candidate_adopted']=True
    q=tmp_path/m.LOCK;q.parent.mkdir(parents=True);q.write_text(json.dumps(row))
    monkeypatch.setattr(m.common,'verify_file',lambda p,v: (_ for _ in ()).throw(ValueError('wrong reuse pin')) if v.get('sha256')=='0'*64 else None)
    monkeypatch.setattr(m.pair,'lock',lambda root:old_fixture.locked())
    with pytest.raises(ValueError):m.lock(tmp_path)


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_selected_branch_has_one_exact_generated_native_contract(tmp_path,variant):
    row,nl,place=old_fixture.fixture(tmp_path);binding=m.target_binding(nl,place,row,variant)
    assert binding['variant']==variant and len(binding['targets'])==1
    assert binding['targets'][0]['insertion']==m.TARGETS[variant]
    script=m.baseline_script(row,binding)
    command=script+'puts [llength $nssoc_ablation_targets]\nputs $nssoc_ablation_expected_variant\nputs [dict get [lindex $nssoc_ablation_targets 0] net]\n'
    result=subprocess.run(['tclsh'],input=command,text=True,capture_output=True,check=True)
    assert result.stdout.splitlines()==['1',variant,m.TARGETS[variant]['native_net']]


@pytest.mark.parametrize('variant',m.VARIANTS)
@pytest.mark.parametrize('fault',['wrong_master','reset','clock','target_net','missing_pin','missing_cell','duplicate_cell','moved','wrong_orientation','missing_place','old_delay_missing','extra_sink','duplicate_place','nl_pin','place_pin'])
def test_both_original_branches_are_source_checked_before_selection(tmp_path,variant,fault):
    row,nl,place=old_fixture.fixture(tmp_path,fault)
    with pytest.raises((KeyError,ValueError)):m.target_binding(nl,place,row,variant)


@pytest.mark.parametrize('bad',['explicit_two_sd3_hold_trial','explicit_hold_ablation_other','explicit_hold_ablation_',None])
def test_unknown_or_other_producer_variant_rejected(bad):
    with pytest.raises(ValueError):m.variant_from_record({'diagnostic_kind':bad})


def inserted(before,variant):
    t=m.TARGETS[variant];cell=m.original.logical_cell_census(before)[t['sink']]
    oldbody=' '+cell['master']+' '+t['sink']+' ('+', '.join('.'+p+'('+v+')'for p,v in cell['ports'].items())+');'
    new=t['new_net']+'37';newbody=oldbody.replace('.D('+t['verilog_net']+')','.D('+new+')')
    assert oldbody in before
    return before.replace(oldbody,newbody).replace('endmodule',f' sg13g2_dlygate4sd3_1 {t["buffer"]}37 (.A({t["verilog_net"]}), .X({new}));\nendmodule')


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_one_identity_contraction_preserves_other_branch_and_old_delay(tmp_path,variant):
    _,nl,_=old_fixture.fixture(tmp_path);before=nl.read_text()
    assert m.validate_identity_buffer(before,inserted(before,variant),variant)['added_instances']==1


@pytest.mark.parametrize('variant',m.VARIANTS)
@pytest.mark.parametrize('fault',['other_variant','extra_cell','new_master','old_delay_input','old_delay_master','wrong_sink','reversed','missing'])
def test_logical_contraction_rejects_nonselected_changes(tmp_path,variant,fault):
    _,nl,_=old_fixture.fixture(tmp_path);before=nl.read_text();after=inserted(before,variant);t=m.TARGETS[variant]
    if fault=='other_variant':after=inserted(before,'npu'if variant=='eth'else'eth')
    if fault=='extra_cell':after=after.replace('endmodule',' sg13g2_buf_1 extra (.A(a),.X(b));\nendmodule')
    if fault=='new_master':after=after.replace('sg13g2_dlygate4sd3_1 '+t['buffer'],'sg13g2_inv_1 '+t['buffer'])
    if fault=='old_delay_input':after=after.replace('.A(oldinput)','.A(other)')
    if fault=='old_delay_master':after=after.replace('sg13g2_dlygate4sd3_1 nssoc_explicit','sg13g2_dlygate4sd2_1 nssoc_explicit')
    if fault=='wrong_sink':after=after.replace('.D('+t['new_net']+'37)','.D(wrong)')
    if fault=='reversed':after=after.replace('.A('+t['verilog_net']+'), .X('+t['new_net']+'37)', '.X('+t['verilog_net']+'), .A('+t['new_net']+'37)')
    if fault=='missing':after=before
    with pytest.raises((KeyError,ValueError)):m.validate_identity_buffer(before,after,variant)


def row(variant):
    t=m.TARGETS[variant]
    return dict(buffer=t['buffer']+'37',new_net=t['new_net']+'37',original_net=t['native_net'],driver=t['driver'],sink=t['sink'],master=t['master'],radius_um=10,orientation='MX',initial_instances=5,initial_nets=12,location_dbu=[0,0],distance_dbu=3780,dbu_per_micron=1000,row_name='ROW')


@pytest.mark.parametrize('variant',m.VARIANTS)
@pytest.mark.parametrize('fault',['zero','two','prefix','target','master','radius','distance','float_position'])
def test_exact_one_native_identity_required(variant,fault):
    rows=[row(variant)]
    if fault=='zero':rows=[]
    if fault=='two':rows.append(copy.deepcopy(rows[0]))
    if fault=='prefix':rows[0]['buffer']='nssoc_pair0_sd31'
    if fault=='target':rows[0]['driver']='other'
    if fault=='master':rows[0]['master']='sg13g2_buf_1'
    if fault=='radius':rows[0]['radius_um']=11
    if fault=='distance':rows[0]['distance_dbu']=-1
    if fault=='float_position':rows[0]['location_dbu'][0]=0.5
    with pytest.raises(ValueError):m.insertion_contract(rows,variant)


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_exact_plus_one_placement_preserves_old_sd3(tmp_path,variant):
    lock,nl,path=old_fixture.fixture(tmp_path);binding=m.target_binding(nl,path,lock,variant);ins=row(variant)
    driver=binding['targets'][0]['native_placement'][ins['driver']];ins['location_dbu']=[int(driver['x_dbu']),int(driver['y_dbu'])+3780]
    before=path.read_text();(tmp_path/'candidate_before').mkdir();(tmp_path/'candidate_before/placement.tsv').write_text(before)
    after=before+'\t'.join([ins['buffer'],ins['master'],*map(str,ins['location_dbu']),ins['orientation'],'PLACED'])+'\n'
    for stage in m.STAGES[1:]:(tmp_path/stage).mkdir();(tmp_path/stage/'placement.tsv').write_text(after)
    assert m.placement_contract(tmp_path,lock,[ins],binding,variant)['added_instances']==1
    q=tmp_path/'reload_repeat/placement.tsv';q.write_text(after.replace('\t1711680\t','\t1712160\t'))
    with pytest.raises(ValueError):m.placement_contract(tmp_path,lock,[ins],binding,variant)


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_frozen_helper_namespace_is_prefix_only_and_variant_immutable(variant):
    command=f'''set ::env(NSSOC_TARGETED_METHOD_ROOT) {{{ROOT}}}
set ::env(NSSOC_HOLD_ABLATION_VARIANT) {variant}
proc nssoc_hold_sha {{path}} {{return [lindex [exec sha256sum $path] 0]}}
source {{{ROOT/m.HELPER}}}
foreach name [info procs ::nssoc_explicit_*] {{
 set local ::nssoc_ablation::[namespace tail $name]
 if {{[info args $name] ne [info args $local]}} {{error "Arguments changed"}}
 set expected [string map [list nssoc_explicit_sd3 nssoc_ablation_{variant}_sd3 nssoc_explicit_holdnet nssoc_ablation_{variant}_net] [info body $name]]
 if {{$expected ne [info body $local]}} {{error "Unexpected body mutation"}}
}}
if {{![catch {{nssoc_ablation_verify {{}}}}]}} {{error "Missing insertion accepted"}}
set ::env(NSSOC_HOLD_ABLATION_VARIANT) wrong
if {{![catch {{nssoc_ablation_call vacancy driver}}]}} {{error "Variant changed"}}
puts PREFIX_ONLY_REUSE_PASS
'''
    result=subprocess.run(['tclsh'],input=command,text=True,capture_output=True,check=True)
    assert result.stderr=='' and result.stdout.strip()=='PREFIX_ONLY_REUSE_PASS'


def test_no_imported_producer_bindings_are_mutated():
    tree=ast.parse((ROOT/m.ENTRY).read_text())
    for node in ast.walk(tree):
        if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
            for target in node.targets if isinstance(node,ast.Assign)else[node.target]:
                assert not (isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name)
                    and target.value.id in {'pair','single','original','prior','shared','targeted'})
    refs=(m.shared.worker,m.shared.capture,m.targeted.specification)
    for variant in m.VARIANTS:assert m.specification(variant).validator.keywords=={'variant':variant}
    assert refs==(m.shared.worker,m.shared.capture,m.targeted.specification)


def test_cloud_matrix_has_two_separate_source_bound_jobs_and_no_retries():
    text=(ROOT/'.github/workflows/timing-hold-ablation.yml').read_text()
    assert 'variant: [eth, npu]'in text and 'fail-fast: false'in text
    assert '--variant "${{ matrix.variant }}"'in text and 'hold-ablation-${{ matrix.variant }}-final-'in text
    assert 'fetch-depth: 0'in text and 'actions: read'in text and 'include-hidden-files: true'in text
    assert 'cancel-in-progress: false'in text and 'GH_TOKEN:'in text
    for f in [m.HELPER,m.STEP,m.CHILD]:
        s=(ROOT/f).read_text();assert '\nrepair_timing'not in s and '\ndetailed_placement'not in s and 'common/dpl.tcl'not in s
    child=(ROOT/m.CHILD).read_text();assert child.index('set child_views')<child.index('common/io.tcl')<child.index('dict for {key value} $child_views')<child.index('read_current_odb')


def test_native_environment_removes_both_tokens(monkeypatch):
    monkeypatch.setenv('GH_TOKEN','secret');monkeypatch.setenv('GITHUB_TOKEN','other');monkeypatch.setenv('PATH','/bin')
    got=m.clean_environment();assert got['PATH']=='/bin' and 'GH_TOKEN'not in got and 'GITHUB_TOKEN'not in got


def test_capture_actual_bridge_includes_all_four_native_physical_files(tmp_path):
    output=tmp_path/'source';where=output/'run/01-openroad-resizertimingpostgrt/ablation-control';where.mkdir(parents=True)
    (output/'result.json').write_text(json.dumps(dict(status='COMPLETE_DIAGNOSTIC_ONLY')))
    for n in ['before.odb','before.def','after.odb','after.def']:(where/n).write_bytes(n.encode()+bytes(range(256)))
    dest=tmp_path/'capture';result=m.capture(output,dest)
    assert set(m.shared.file_inventory(dest))==set(result['files'])|{'capture.json'}
    assert len(result['files'])==5
    for n,v in result['files'].items():assert hashlib.sha256((dest/n).read_bytes()).hexdigest()==v['sha256']


@pytest.mark.parametrize('name',['other.odb','other.def'])
def test_capture_rejects_unreviewed_native_file(tmp_path,name):
    output=tmp_path/'source';where=output/'run/01-openroad-resizertimingpostgrt/ablation-control';where.mkdir(parents=True)
    (output/'result.json').write_text(json.dumps(dict(status='COMPLETE_DIAGNOSTIC_ONLY')));(where/name).write_bytes(b'bad')
    with pytest.raises(ValueError):m.capture(output,tmp_path/'capture')


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_native_environment_binds_variant_from_record_not_caller_environment(tmp_path,monkeypatch,variant):
    out=tmp_path/'output';(out/'native-controls').mkdir(parents=True);(out/'run').mkdir()
    record=dict(diagnostic_kind='explicit_hold_ablation_'+variant,runtime_sha256=m.targeted.RUNTIME_SHA,
        work=str(tmp_path/'work'),candidate_overlay=dict(files={'soc_top.odb':{'sha256':'a'*64},'soc_top.sdc':{'sha256':'b'*64}}))
    (out/'result.json').write_text(json.dumps(record));(out/'native-controls/result.json').write_text(json.dumps(dict(
        command=[m.targeted.NATIVE_IDENTITY['launcher']['path']],native_executable_sha256=m.targeted.NATIVE_IDENTITY['launcher']['sha256'])))
    calls=[]
    def verify(root,row,spec):
        calls.append(spec.name);assert row==record and spec.sources==m.SOURCES;return {'pdk_root':'pdk'}
    monkeypatch.setattr(m.shared,'verify_inputs',verify);monkeypatch.setattr(m,'verify_overlay',lambda root,row:tmp_path/'candidate')
    monkeypatch.setattr(m.common,'sha',lambda p:m.targeted.RECIPE_SHA if str(p).endswith(m.targeted.RECIPE)else m.targeted.FIXTURE_SHA)
    monkeypatch.setenv('NSSOC_HOLD_ABLATION_VARIANT','wrong-caller')
    m.native_environment(['program','_native_flow','--force-run-dir',str(out/'run')])
    assert calls==['explicit_hold_ablation_'+variant]
    import os
    assert os.environ['NSSOC_HOLD_ABLATION_VARIANT']==variant
    assert os.environ['NSSOC_ELECTRICAL_CANDIDATE_ODB']==str(tmp_path/'candidate/soc_top.odb')
    assert os.environ['NSSOC_TARGETED_ACTUAL_ELF_SHA256']==m.targeted.NATIVE_IDENTITY['actual_elf']['sha256']


def test_both_limited_proof_processes_use_sanitized_environment(tmp_path,monkeypatch):
    before=tmp_path/'before.v';before.write_text('original');candidate=tmp_path/'candidate';candidate.mkdir();(candidate/'soc_top.v').write_text('parent')
    repaired=tmp_path/'after.v';repaired.write_text('after');out=tmp_path/'out';out.mkdir();calls=[]
    monkeypatch.setattr(m.eco,'bundle_inputs',lambda *a:(before,tmp_path/'lib',tmp_path/'macro'))
    monkeypatch.setenv('GH_TOKEN','secret');monkeypatch.setenv('GITHUB_TOKEN','other')
    def execute(command,output,record,name,env):
        assert 'GH_TOKEN'not in env and 'GITHUB_TOKEN'not in env
        target=output/name;target.mkdir();(target/'result.json').write_text(json.dumps({'status':'PASS within scope'}));calls.append(name)
    monkeypatch.setattr(m.shared,'execute',execute)
    result=m.logic_proofs(out,{'work':str(tmp_path/'work')},{},candidate,repaired)
    assert calls==['parent-logic','electrical-logic']
    assert result['parent-logic']['after']==result['electrical-logic']['before']
    assert result['electrical-logic']['after']==m.eco.file_pin(repaired)


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_every_historical_and_fresh_guard_remains_strict(variant):
    locked_row=locked();before=locked_row['baseline_metrics'];metrics={name:dict(before,recorded_ms=1)for name in m.STAGES}
    metrics['reload_repeat']['hold_wns_seconds']+=1e-12
    metrics['reload_repeat']['hold_tns_seconds']+=1e-12
    metrics['reload_repeat']['hold_violating_endpoints']-=1
    got=m.guard(metrics,locked_row,True,True)
    assert len(got['no_regression'])==9 and got['aggregate_estimate_guard_passed']
    assert not got['candidate_adopted'] and not got['timing_accepted']
    metrics['reload_repeat']['setup_violating_endpoints']+=1
    assert not m.guard(metrics,locked_row,True,True)['aggregate_estimate_guard_passed']
    metrics['reload_repeat']['setup_violating_endpoints']-=1
    assert not m.guard(metrics,locked_row,False,True)['aggregate_estimate_guard_passed']
    assert not m.guard(metrics,locked_row,True,False)['aggregate_estimate_guard_passed']


def tiny_control_fixture(root,variant):
    """Small raw-report fixture; no archived results or network dependencies."""
    selected=m.VARIANTS.index(variant);prefix='nssoc_ablation_'+variant
    root.mkdir();log=root/'native.log';log.write_text('PASS_NATIVE_HOLD_ABLATION_CONTROL_NO_CHIP_ACCEPTANCE\n')
    for stem in ('graph','objects'):
        for suffix in ('before','after-contracted'):(root/f'{stem}-{suffix}.tsv').write_text('preserved original\n')
    for name in ('before.sdc','after.sdc'):(root/name).write_text('create_clock -period 20 clock\n')
    result=dict(status='PASS_NATIVE_HOLD_ABLATION_CONTROL',variant=variant,selected_branch=selected,untouched_branch=1-selected,
        negative_control_messages={key:'DPL-0033'if key=='native_overlap'else'rejected'for key in m.CONTROL_NEGATIVES},
        pre_sdc_sha256=m.common.sha(root/'before.sdc'),post_sdc_sha256=m.common.sha(root/'after.sdc'),
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
        insertion=dict(master='sg13g2_dlygate4sd3_1',initial_instances=5,initial_nets=12,driver=f'driver{selected}',
            sink=f'sink{selected}',original_net=f'target{selected}',location_dbu=[50400,34020],orientation='MX',row_name='ROW_7',
            distance_dbu=3780,dbu_per_micron=1000,radius_um=10,buffer=prefix+'_sd31',new_net=prefix+'_net1'),
        initial_instances=5,final_instances=6,initial_nets=12,final_nets=13,selected_vacancy='3780 50400 34020 ROW_7 MX',
        before_metrics={},after_metrics={})
    for flag in ('independently_predicted_nearest_vacancy','untouched_branch_preserved','single_row_adapters_verified',
        'all_original_objects_preserved','all_original_placements_preserved','preserved_original_delay',
        'full_graph_contraction_preserved','exactly_one_new_cell_and_net','pg_bindings_preserved',
        'actual_global_route_before_and_after','all_three_corners_loaded_and_timed','no_detailed_placement_called',
        'constraints_preserved','estimated_global_route_tiny_control_only','tiny_native_control_only'):result[flag]=True
    for phase in ('before','after'):
        for branch in (0,1):
            timing=result[phase+'_metrics'][f'target{branch}']={}
            for corner in ('fast','typical','slow'):
                delayed=phase=='after'and branch==selected
                values=dict(min_slack_ns=0.35 if delayed else 0.1,max_slack_ns=19.3 if delayed else 19.8);timing[corner]=values
                texts=[]
                for delay in ('min','max'):
                    texts.append(f'Startpoint: driver{branch}\nPath Type: {delay}\nCorner: {corner}\n'
                        f'driver{branch}/Q (sg13g2_dfrbpq_1)\nsink{branch}/D (sg13g2_dfrbpq_1)\n'
                        +(prefix+'_sd31/X (sg13g2_dlygate4sd3_1)\n'if delayed else'')
                        +f'{values[delay+"_slack_ns"]:.9f} slack (MET)\n')
                (root/f'{phase}-branch{branch}-{corner}.rpt').write_text(''.join(texts))
    (root/'result.json').write_text(json.dumps(result));return result,log


@pytest.mark.parametrize('variant',m.VARIANTS)
def test_native_control_replays_both_raw_branches_and_three_corners(tmp_path,variant):
    result,log=tiny_control_fixture(tmp_path/'control',variant)
    assert m.validate_native_control(log.parent,log,variant)==result


@pytest.mark.parametrize('fault',['missing_negative','empty_negative','fake_overlap','constraint_bytes','graph_bytes','object_bytes',
    'missing_marker','duplicate_marker','adoption','missing_invariant','wrong_variant','wrong_branch','wrong_prefix',
    'wrong_vacancy','extra_cell','extra_net','missing_corner','property_mismatch','wrong_raw_driver','missing_raw_max',
    'wrong_raw_corner','missing_raw_delay','untouched_raw_delay','untouched_metrics','missing_selected_gain'])
def test_native_control_rejects_changed_raw_and_native_contract(tmp_path,fault):
    root=tmp_path/'control';result,log=tiny_control_fixture(root,'eth')
    report=root/'after-branch0-fast.rpt';untouched=root/'after-branch1-fast.rpt'
    if fault=='missing_negative':result['negative_control_messages'].pop('wrong_variant')
    if fault=='empty_negative':result['negative_control_messages']['wrong_variant']=''
    if fault=='fake_overlap':result['negative_control_messages']['native_overlap']='generic check'
    if fault=='constraint_bytes':(root/'after.sdc').write_text('create_clock -period 21 clock\n')
    if fault=='graph_bytes':(root/'graph-after-contracted.tsv').write_text('different graph\n')
    if fault=='object_bytes':(root/'objects-after-contracted.tsv').write_text('moved old delay\n')
    if fault=='missing_marker':log.write_text('complete\n')
    if fault=='duplicate_marker':log.write_text(log.read_text()*2)
    if fault=='adoption':result['candidate_adopted']=True
    if fault=='missing_invariant':result['preserved_original_delay']=False
    if fault=='wrong_variant':result['variant']='npu'
    if fault=='wrong_branch':result['selected_branch']=1
    if fault=='wrong_prefix':result['insertion']['buffer']='nssoc_ablation_npu_sd31'
    if fault=='wrong_vacancy':result['insertion']['location_dbu'][1]+=3780
    if fault=='extra_cell':result['final_instances']=7
    if fault=='extra_net':result['final_nets']=14
    if fault=='missing_corner':result['after_metrics']['target0'].pop('slow')
    if fault=='property_mismatch':result['after_metrics']['target0']['fast']['min_slack_ns']+=0.001
    if fault=='wrong_raw_driver':report.write_text(report.read_text().replace('driver0/Q','driver1/Q'))
    if fault=='missing_raw_max':report.write_text(report.read_text().split('Startpoint: driver0')[1])
    if fault=='wrong_raw_corner':report.write_text(report.read_text().replace('Corner: fast','Corner: slow'))
    if fault=='missing_raw_delay':report.write_text(report.read_text().replace('nssoc_ablation_eth_sd31/X','another/X'))
    if fault=='untouched_raw_delay':untouched.write_text(untouched.read_text().replace('Corner: fast','Corner: fast\nnssoc_ablation_eth_sd31/X'))
    if fault=='untouched_metrics':
        result['after_metrics']['target1']['fast']['min_slack_ns']=0.2
        untouched.write_text(untouched.read_text().replace('0.100000000 slack','0.200000000 slack'))
    if fault=='missing_selected_gain':
        result['after_metrics']['target0']['fast']['min_slack_ns']=0.1
        report.write_text(report.read_text().replace('0.350000000 slack','0.100000000 slack'))
    (root/'result.json').write_text(json.dumps(result))
    with pytest.raises((KeyError,ValueError)):m.validate_native_control(root,log,'eth')
