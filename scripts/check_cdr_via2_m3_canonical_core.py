#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/JSON/synthetic-region controls; no project native acquisition."""
import ast,builtins,copy,hashlib,json,os,re,subprocess,symtable,tempfile
from pathlib import Path
import cdr_via2_m3_canonical_core as c
ROOT=c.ROOT
BRANCH='codex/cdr-via2-m3-canonical-view-core'
RESULT=ROOT/'hw/soc/out/cdr-via2-m3-canonical-core-source'
RECORDS=[]
def record(name,scope,**values):
    RECORDS.append(dict(name=name,scope=scope,**values))
def reject(name,fn):
    try:fn()
    except(AssertionError,KeyError,ValueError,TypeError,FileNotFoundError)as e:
        record(name,'intentional synthetic refusal',error=str(e));return
    raise AssertionError('Accepted '+name)
def source_guard():
    e=os.environ
    c.require(e.get('GITHUB_ACTIONS')=='true'and e.get('RUNNER_ENVIRONMENT')=='github-hosted'and e.get('RUNNER_OS')=='Linux','hosted controls')
    c.require(e.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and e.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual exact repository')
    c.require(e.get('GITHUB_REF')=='refs/heads/'+BRANCH and e.get('GITHUB_JOB')=='source-controls'and e.get('GITHUB_RUN_ATTEMPT')=='1','source branch/job/attempt')
    head=e.get('GITHUB_SHA','');c.require(re.fullmatch('[0-9a-f]{40}',head)and e.get('APPROVED_SOURCE')==head,'exact approved source')
    c.require(e.get('GITHUB_WORKFLOW_REF')=='Melihakbulut221/nssoc/.github/workflows/cloud-evidence-summary.yml@refs/heads/'+BRANCH and Path.cwd()==ROOT,'workflow and cwd')
    c.require(subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip()==head,'actual checkout')
    manifest=c.projection.regular(ROOT,c.PINS).read_bytes()
    c.require(manifest==subprocess.check_output(['git','show',head+':'+c.PINS],cwd=ROOT),'exact source manifest')
    m=json.loads(manifest)
    for name,pin in m['files'].items():c.require(c.pin(c.projection.regular(ROOT,name))==pin,'complete source pin '+name)
    config=c.read_json(ROOT/c.CONFIG);c.validate_config(config)
    c.require(config['branch']==BRANCH and config['source_controls_authorized']is True,'source identity')
    c.require(all(config[k]is False for k in('native_acquisition_authorized','view_execution_authorized','native_execution_authorized','rc_extraction_authorized','electrical_simulation_authorized')),'source-only authority')
    return config,dict(source=head,run_id=int(e['GITHUB_RUN_ID']),attempt=1,job=e['GITHUB_JOB'],manifest_sha256=hashlib.sha256(manifest).hexdigest())
def graph_fixture(groups=7,empty=3):
    modeldefs=[('sg13_lv_nmos',50,('D','G','S','B')),('npn13G2',124,('C','B','E','S')),
        ('rppd',98,('P','N','rppd_sub')),('cap_cmim',7,('P','N')),('ptap1',221,('TAP','WELL'))]
    bins={28:[],135:[]};bins.update({1000+i:[]for i in range(groups)})
    device=0
    for model,count,terminals in modeldefs:
        for _ in range(count):
            device+=1
            for t in terminals:
                owner=28 if device in (3,4,5,6)and t=='D' else 135 if device in(32,33,34,35)and t=='D' else 1000+(device%groups)
                bins[owner].append(dict(device=device,model=model,terminal=t))
    ports=['P'+str(i)for i in range(25)];nets=[];components=[]
    for i,(cluster,terminals)in enumerate(bins.items()):
        component=17 if cluster==28 else 61 if cluster==135 else 2000+i
        pp=[p for n,p in enumerate(ports)if n%len(bins)==i]
        nets.append(dict(native_cluster=cluster,name='$'+str(cluster),device_terminals=terminals,public_ports=pp,wire_components=[component],metal_area_dbu2=1))
        components.append(dict(component=component,native_cluster=cluster,native_name='$'+str(cluster),layers={}))
    for i in range(empty):nets.append(dict(native_cluster=5000+i,name='$empty'+str(i),device_terminals=[],public_ports=[],wire_components=[],metal_area_dbu2=0))
    return dict(native_device_count=500,native_terminal_count=1446,native_devices=c.CENSUS,native_ports=ports,
        no_component_union_by_native_label=True,no_wire_geometry_change=True,wire_rc_extracted=False,full_pex_qualified=False,substrate_r_modeled=False,
        native_net_coverage=nets,wire_components=components,native_net_count=len(nets),wire_component_count=len(components),
        native_electrical_net_count=len(bins),layers={str(n):dict(explicitly_empty=False)for n in c.LAYERS})
def count_controls():
    for groups,empty in ((7,3),(111,0),(114,126)):
        graph=graph_fixture(groups,empty);index=c.graph_index(graph)
        c.require(len(index['terminals'])==1446 and len(index['ports'])==25,'synthetic complete identities')
        record('dynamic_graph_%d_%d'%(groups,empty),'synthetic complete graph',components=len(index['component_rows']),native_nets=len(index['nets']))
    original=graph_fixture()
    mutations={
        'stale113_components':lambda g:g.update(wire_component_count=113),
        'stale238_nets':lambda g:g.update(native_net_count=238),
        'stale114_electrical':lambda g:g.update(native_electrical_net_count=114),
        'missing_terminal':lambda g:g['native_net_coverage'][0]['device_terminals'].pop(),
        'duplicate_terminal':lambda g:g['native_net_coverage'][1]['device_terminals'].append(copy.deepcopy(g['native_net_coverage'][0]['device_terminals'][0])),
        'duplicate_cluster':lambda g:g['native_net_coverage'][-1].update(native_cluster=28),
        'orphan_component':lambda g:g['wire_components'][0].update(native_cluster=999999),
        'wrong_native_name':lambda g:g['wire_components'][0].update(native_name='wrong'),
        'missing_component':lambda g:g['wire_components'].pop(),
        'split_native_partition':lambda g:g['native_net_coverage'][0]['wire_components'].append(999999),
        'empty_partition_metal':lambda g:g['native_net_coverage'][-1].update(metal_area_dbu2=1),
        'duplicate_public_port':lambda g:g['native_net_coverage'][1]['public_ports'].append(g['native_net_coverage'][0]['public_ports'][0]),
        'missing_public_port':lambda g:g['native_ports'].pop(),
        'rc_promotion':lambda g:g.update(wire_rc_extracted=True),
        'label_union':lambda g:g.update(no_component_union_by_native_label=False),
        'wrong_device_census':lambda g:g.update(native_device_count=499)}
    for name,mutate in mutations.items():
        bad=copy.deepcopy(original);mutate(bad);reject(name,lambda:c.graph_index(bad))
def source_definition_controls(config):
    identities=c.identity_namespace(ROOT,config)
    topo=c.topology_namespace(ROOT,config)
    c.require(identities.read_side.__name__=='read_side'and identities.witness_controls.__name__=='witness_controls','actual exact frozen definitions loaded')
    original=ast.parse(c.source_text(ROOT,'scripts/cdr_current_tail_graph_native.py',config))
    old=next(n for n in original.body if isinstance(n,ast.FunctionDef)and n.name=='compare_witnesses')
    current=ast.parse((ROOT/'scripts/cdr_via2_m3_canonical_core.py').read_text())
    new=next(n for n in current.body if isinstance(n,ast.FunctionDef)and n.name=='compare_witnesses')
    c.require(ast.dump(ast.Module(body=old.body[:-1],type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=new.body[:-1],type_ignores=[]),include_attributes=False),'all identity checks unchanged before return metadata')
    record('frozen_identity_and_anchor_definitions','exact source/AST scope',checks_before_return_identical=True,identity_functions=7,normalization_functions=4)
    texts,proof=c.derived_sources(ROOT,config)
    for filename,text in texts.items():
        tree=ast.parse(text);c.require(tree,'derived helper parses')
    record('three_helper_derivations','exact source substitution',records=proof)
    scope={}
    c.definitions('raise RuntimeError("must not execute")\ndef good():\n    return 7\n',['good'],scope,'explicit-source-fixture')
    c.require(scope['good']()==7,'module main excluded')
    record('definition_only_module_side_effect_excluded','synthetic source')
    for label,text,names in(
        ('missing_definition','def x():\n    pass\n',['missing']),
        ('duplicate_definition','def x():\n    pass\ndef x():\n    pass\n',['x']),
        ('decorator_side_effect','@effect()\ndef x():\n    pass\n',['x']),
        ('default_side_effect','def x(a=effect()):\n    pass\n',['x']),
        ('annotation_side_effect','def x(a: effect()):\n    pass\n',['x'])):
        reject(label,lambda text=text,names=names:c.definitions(text,names,{},'explicit-source-fixture'))
    bad=copy.deepcopy(config);bad['frozen_definitions'][c.IDENTITY]['sha256']='0'*64
    reject('changed_frozen_identity_source',lambda:c.identity_namespace(ROOT,bad))
    return texts
def material_controls(config):
    import pya
    generation=c.read_json(ROOT/config['generation']['proof_path'])
    c.require(c.pin(ROOT/config['generation']['proof_path'])==config['generation']['pin'],'exact derived generation bytes')
    old=graph_fixture();new=copy.deepcopy(old)
    groups,targets=c.declarations(generation,config,old,new)
    c.require(len(groups)==4 and sum(map(len,groups.values()))==16 and len(targets)==8,'complete actual16shape metadata applied to synthetic graph')
    for(key,layer),boxes in groups.items():
        before=pya.Region(pya.Box(0,0,10,10));after=before.dup()
        for b in boxes:after.insert(pya.Box(*b))
        c.exact_union(pya,before,after,boxes)
        reject('missing_material_layer%d_%s'%(layer,key[:35]),lambda:c.exact_union(pya,before,before,boxes))
        foreign=after+pya.Region(pya.Box(-100,-100,-90,-90))
        reject('foreign_material_layer%d_%s'%(layer,key[:35]),lambda:c.exact_union(pya,before,foreign,boxes))
    record('all16_actual_declaration_shapes_synthetic_union','synthetic native Region algebra',partitions=2,layers=[29,30],shapes=16)
    for label,change in(
        ('missing_added_record',lambda g:g['proof']['added_records'].pop()),
        ('wrong_generation_candidate',lambda g:g['proof']['candidate'].update(sha256='0'*64)),
        ('no_structural_reversal',lambda g:g['proof'].update(structural_reversal_exact=False)),
        ('changed_original_owner',lambda g:g['proof']['added_records'][0].update(native_cluster=999)),
        ('changed_added_layer',lambda g:g['proof']['added_records'][0].update(layer=10))):
        bad=copy.deepcopy(generation);change(bad);reject(label,lambda:c.declarations(bad,config,old,new))
    bad=copy.deepcopy(new)
    bad['native_net_coverage'][1]['device_terminals'].append(bad['native_net_coverage'][0]['device_terminals'].pop())
    reject('moved_actual_drain_partition',lambda:c.declarations(generation,config,old,bad))
    class Wire:
        def __init__(self,registered):self.registered=registered
        def layer_by_name(self,name):return object()if self.registered else None
        def shapes_of_net(self,*args):return pya.Region(pya.Box(0,0,10,10))
    graph=copy.deepcopy(old);graph['layers']['29']['explicitly_empty']=True
    c.require(c.layer_region(pya,Wire(False),None,graph,29).is_empty(),'empty observed layer')
    reject('empty_layer_registered',lambda:c.layer_region(pya,Wire(True),None,graph,29))
    reject('present_layer_missing',lambda:c.layer_region(pya,Wire(False),None,old,29))
    c.require(c.layer_region(pya,Wire(True),None,old,29).area()==100,'observed present native layer')
    record('independent_old_new_layer_presence','synthetic native Region algebra')
def scope_controls(config):
    reject('standalone_native_entry',lambda:c.authorize_native())
    active=copy.deepcopy(config);active['view_execution_authorized']=True;active['native_execution_authorized']=True
    reject('core_config_cannot_grant_native_entry',lambda:c.authorize_native(active))
    for field in('rc_extraction_authorized','electrical_simulation_authorized','physical_accepted','electrical_accepted','full_phy_accepted'):
        bad=copy.deepcopy(config);bad[field]=True;reject('forbidden_'+field,lambda:c.validate_config(bad))

def incremental_preservation_controls(config):
    """Explicit synthetic globals clone; real exclusive JSON writes, no native input."""
    import types
    original_identity=c.identity_namespace
    phases=('new-read','compare','witness','material','bindings')
    names=('old-native-identity.json','new-native-identity.json','native-identity-comparison.json',
        'actual-witness-faults.json','full-partition-material.json')
    for phase,expected_count in zip(phases,(1,2,3,4,5)):
        out=RESULT/'lifecycle-fixtures'/phase;out.mkdir(parents=True)
        def sentinel():
            raise RuntimeError('EXPLICIT_SYNTHETIC_FAILURE:'+phase)
        observations={
            'old':dict(synthetic_fixture=True,side='old'),
            'new':dict(synthetic_fixture=True,side='new',graph={},locations={},anchors={}),
            'compare':dict(synthetic_fixture=True,complete_observation='comparison'),
            'witness':dict(synthetic_fixture=True,complete_observation='witness'),
            'material':dict(synthetic_fixture=True,complete_observation='material')}
        def read_side(pya,root,files,producer):
            if root.name=='new-view'and phase=='new-read':sentinel()
            return None,observations['new'if root.name=='new-view'else'old']
        def compare(old,new):
            if phase=='compare':sentinel()
            return observations['compare']
        def witness(old,new):
            if phase=='witness':sentinel()
            return observations['witness']
        def material(*args):
            if phase=='material':sentinel()
            return observations['material']
        def report_inputs(*args):sentinel()
        def read_json(path):
            if path.name=='native-planes.json':
                return dict(status='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS',anchors=[None]*160,controls=[None]*19,
                    parent_geometry=dict(controls=[None]*5,actual_placements=[None]*16,checked_layers_by_kind=[None]*9))
            assert path.name=='source-pins.json'
            return dict(status='PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING',
                target_gds_sha256=config['candidate']['gds']['sha256'],target_geometry_edited=False,missing_referenced_primitive_rejected=True)
        scope=dict(c.verify.__globals__,verify_prepared=lambda *args:None,read_json=read_json,
            pin=lambda p:config['original_reference_gds'],
            identity_namespace=lambda *args:types.SimpleNamespace(read_side=read_side,compare_witnesses=compare,witness_controls=witness),
            prove_material=material,report_inputs=report_inputs)
        fixture=types.FunctionType(c.verify.__code__,scope,c.verify.__name__)
        c.require(fixture.__code__ is c.verify.__code__ and fixture.__globals__ is not c.verify.__globals__,'exact verifier body, explicit isolated fixture globals')
        try:fixture(out/'old-reference',out/'unused-physical',out/'new-view',out,ROOT,config)
        except RuntimeError as e:c.require(str(e)=='EXPLICIT_SYNTHETIC_FAILURE:'+phase,'original synthetic primary retained')
        else:raise AssertionError('Fixture did not reach its explicit failure')
        actual=sorted(p.name for p in out.iterdir()if p.is_file())
        c.require(actual==sorted(names[:expected_count]),'all completed observations retained and no later fabricated record')
        saved={p.name:c.read_json(p)for p in out.iterdir()if p.is_file()}
        values=[observations[n]for n in('old','new','compare','witness','material')[:expected_count]]
        c.require(saved==dict(zip(names[:expected_count],values)),'actual exclusive output bytes represent completed observations')
        c.require(c.identity_namespace is original_identity,'production globals unchanged')
        record('incremental_preservation_'+phase,'explicit source-only failure fixture',native_acquired=False,
            production_admission_exercised=False,exact_function_code=True,completed_output_records=saved,
            output_pins={p.name:c.pin(p)for p in out.iterdir()if p.is_file()})
    reject('production_native_entry_still_disabled_after_lifecycle',lambda:c.authorize_native())

def main():
    config,context=source_guard();RESULT.mkdir(parents=True,exist_ok=False)
    c.projection.write_new(RESULT,'source-context.json',c.encode(context))
    try:
        source_definition_controls(config);count_controls();material_controls(config);scope_controls(config);incremental_preservation_controls(config)
        result=dict(status='PASS_SOURCE_AND_SYNTHETIC_CORE_CONTROLS_NOT_NATIVE_QUALIFICATION',context=context,
            controls=RECORDS,control_count=len(RECORDS),native_acquired=False,native_view_executed=False,**c.FLAGS)
        c.projection.write_new(RESULT,'source-controls.json',c.encode(result));print(json.dumps(result,sort_keys=True))
    except BaseException as e:
        c.projection.write_new(RESULT,'source-failure.json',c.encode(dict(error=type(e).__name__,message=str(e),completed_controls=RECORDS,native_acquired=False)))
        raise
if __name__=='__main__':main()
