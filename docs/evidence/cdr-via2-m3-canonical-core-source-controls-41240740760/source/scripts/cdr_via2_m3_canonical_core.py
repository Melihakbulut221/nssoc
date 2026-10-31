#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound canonical-view primitives. No acquisition, RC, or standalone native authority."""
import ast,collections,copy,hashlib,json,os,re,sys,types
from pathlib import Path
import cdr_via2_m3_canonical_view as projection
ROOT=Path(__file__).resolve().parents[1]
TOP=projection.TOP
CONFIG='scripts/cdr-via2-m3-canonical-core-inputs.json'
PINS='scripts/cdr-via2-m3-canonical-core-pins.json'
LAYERS=(8,10,30,50,67,126,134,19,29,49,66,125,133)
TARGETS=(3,4,5,6,32,33,34,35)
CENSUS={'sg13_lv_nmos':50,'npn13G2':124,'rppd':98,'cap_cmim':7,'ptap1':221}
DISPOSITIONS={'ACTUAL_TERMINAL_METAL_POINT_REFERENCE':953,'RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE':493}
IDENTITY='scripts/cdr_v59_tail_saved_identity_native.py'
TOPOLOGY='scripts/cdr_v59_tail_access_topology.py'
PARENT='scripts/check_cdr_sampler_active_input_v57_parent_geometry.py'
PLANES='scripts/cloud_cdr_sampler_active_input_v57_planes.py'
RECOVER='scripts/cloud_cdr_sampler_active_input_v57_wire_inputs.py'
require=projection.require
encode=projection.encode
pin=lambda p:projection.fingerprint(p.read_bytes())
def read_json(p):
    require(p.is_file()and not p.is_symlink(),'regular JSON input')
    return json.loads(p.read_bytes())
FLAGS=dict(rc_extracted=False,electrical_accepted=False,physical_accepted=False,full_phy_accepted=False)

def validate_config(config):
    require(config['schema']=='cdr-via2-m3-canonical-view-core-v1','core schema')
    require(config['physical_binding']['run_id']==41238994098 and config['physical_binding']['source']=='0b1ec86b35f8cb98928a5687f007a7ccd676f620' and config['physical_binding']['release_id']==430168624,'actual physical identity')
    require(config['candidate']['gds']==dict(bytes=998644,sha256='42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876'),'exact candidate')
    require(config['reference_prefix']=='native/candidate/' and config['graph_counts_must_be_derived'] is True,'complete original reference namespace')
    require(all(config[k]is False for k in ('rc_extraction_authorized','electrical_simulation_authorized','physical_accepted','electrical_accepted','full_phy_accepted')),'core cannot authorize later stages or acceptance')
    require(config['generation']['pin']==dict(bytes=4721,sha256='e6e1a9278ccc6b1f76972985c11727c4f2a887d4806102d43ef234c85bc2deac'),'actual serialized generation record')
    return True

def source_text(source_root,relative,config):
    expected={**config['frozen_definitions'],**config['wire_workers']}
    require(relative in expected,'explicit frozen definition source')
    path=projection.regular(source_root,relative)
    require(pin(path)==expected[relative],'immutable complete definition source: '+relative)
    return path.read_text()

def definitions(text,names,scope,filename):
    """Compile only named plain definitions, with no imports or module main executed."""
    tree=ast.parse(text);selected=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
    require(len(selected)==len(names)==len(set(names)) and {n.name for n in selected}==set(names),'exact definition census')
    for n in selected:
        require(not n.decorator_list and not n.args.defaults and not any(n.args.kw_defaults),'no definition-time side effects')
        require(n.returns is None and all(a.annotation is None for a in n.args.args+n.args.kwonlyargs),'no evaluated annotations')
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(filename),'exec'),scope)
    return {n:scope[n]for n in names}

def graph_index(graph):
    """Retain every original ownership check, derive only topology-dependent counts."""
    require(type(graph['native_device_count'])is int and graph['native_device_count']==500,'device census')
    require(type(graph['native_terminal_count'])is int and graph['native_terminal_count']==1446,'terminal census')
    require(graph['native_devices']==CENSUS and len(graph['native_ports'])==len(set(graph['native_ports']))==25,'model and public-port census')
    require(graph['no_component_union_by_native_label']is graph['no_wire_geometry_change']is True,'no label union or geometry mutation')
    require(graph['wire_rc_extracted']is graph['full_pex_qualified']is graph['substrate_r_modeled']is False,'graph-only scope')
    nets=graph['native_net_coverage'];components=graph['wire_components']
    require(type(graph['native_net_count'])is int and graph['native_net_count']==len(nets)>0,'actual native-net census')
    require(type(graph['wire_component_count'])is int and graph['wire_component_count']==len(components)>0,'actual conductor-component census')
    by_cluster={};terminals={};ports={};component_keys={};component_rows={}
    for row in nets:
        cluster=row['native_cluster'];require(type(cluster)is int and cluster not in by_cluster,'unique native cluster')
        ts=[(v['device'],v['model'],v['terminal'])for v in row['device_terminals']]
        require(len(ts)==len(set(ts)) and len(row['public_ports'])==len(set(row['public_ports'])),'unique native identities')
        for t in ts:require(t not in terminals,'terminal in two partitions');terminals[t]=cluster
        for p in row['public_ports']:require(p not in ports,'public port in two partitions');ports[p]=cluster
        key=json.dumps(dict(terminals=sorted(ts),public_ports=sorted(row['public_ports'])),sort_keys=True,separators=(',',':'),allow_nan=False)
        by_cluster[cluster]=dict(key=key,name=row['name'],row=row)
        owners=row['wire_components'];require(len(owners)<=1,'no split native conductor')
        if not ts:require(row['metal_area_dbu2']==0 and not row['public_ports'] and not owners,'empty native partition owns no material')
        if row['metal_area_dbu2']:require(len(owners)==1,'material has exact owner')
        for component in owners:
            require(type(component)is int and component not in component_keys,'unique component owner');component_keys[component]=key
    require(len(terminals)==1446 and len(ports)==25 and set(ports)==set(graph['native_ports']),'complete terminal and port identity coverage')
    require(len(component_keys)==len(components),'complete conductor ownership')
    electrical=[r['key']for r in by_cluster.values()if r['row']['device_terminals']]
    require(len(electrical)==len(set(electrical)) and type(graph['native_electrical_net_count'])is int and graph['native_electrical_net_count']==len(electrical),'actual unique electrical partitions')
    for row in components:
        component=row['component'];require(component not in component_rows and component in component_keys,'actual unique component')
        cluster=row['native_cluster'];require(cluster in by_cluster,'actual native cluster')
        require(component_keys[component]==by_cluster[cluster]['key'] and row['native_name']==by_cluster[cluster]['name'],'component identity and native spelling')
        component_rows[component]=row
    require(set(component_rows)==set(component_keys),'complete native component census')
    return dict(nets=by_cluster,terminals=terminals,ports=ports,component_keys=component_keys,component_rows=component_rows)

def topology_namespace(source_root,config):
    scope=dict(json=json,copy=copy,collections=collections,hashlib=hashlib,CENSUS=CENSUS,DISPOSITIONS=DISPOSITIONS,graph_index=graph_index)
    names=['canonical','normalize','normalized_locations','normalized_anchors']
    definitions(source_text(source_root,TOPOLOGY,config),names,scope,source_root/TOPOLOGY)
    return types.SimpleNamespace(**{n:scope[n]for n in names+['graph_index']})

def identity_namespace(source_root,config):
    topology=topology_namespace(source_root,config)
    def load_definitions(path,names,scope):
        relative=path.relative_to(source_root).as_posix()
        return definitions(source_text(source_root,relative,config),names,scope,path)
    source=types.SimpleNamespace(load_definitions=load_definitions,read_json=read_json)
    scope=dict(json=json,re=re,collections=collections,copy=copy,Path=Path,TOP=TOP,source=source,topology=topology,
        MODELS={'npn13G2':'npn13G2','rppd':'rppd','ptap1':'ptap1','cmim':'cap_cmim','nmos':'sg13_lv_nmos'})
    names=['require','parse_path','properties','stable_path','inventory','read_side','witness_controls']
    definitions(source_text(source_root,IDENTITY,config),names,scope,source_root/IDENTITY)
    def compare(old,new):return compare_witnesses(old,new,topology,scope['parse_path'])
    scope['compare_witnesses']=compare
    return types.SimpleNamespace(**{n:scope[n]for n in names},compare_witnesses=compare)

def compare_witnesses(old,new,topology,parse_path):
    require(old["native_device_count"]==new["native_device_count"]==500,"Wrong witness device census")
    require(old["native_terminal_count"]==new["native_terminal_count"]==1446,"Wrong witness terminal census")
    oi=topology.graph_index(old["graph"]);ni=topology.graph_index(new["graph"])
    require(sorted(r["key"] for r in oi["nets"].values())==
      sorted(r["key"] for r in ni["nets"].values()),"Native terminal/public-port partitions changed")
    require(len(old["paths"])==len(new["paths"])==500,"Missing stable identity")
    for a,b in zip(old["paths"],new["paths"]):
        require(a["native_device"]==b["native_device"] and a["model"]==b["model"],"Device identity changed")
        parse_path(a["raw_path"]);parse_path(b["raw_path"])
        require(a["stable_path"]==b["stable_path"],"Stable instance path changed")
    op={p["name"]:p for p in old["native_pins"]};np={p["name"]:p for p in new["native_pins"]}
    require(len(op)==len(old["native_pins"])==len(np)==len(new["native_pins"])==25,"Duplicate/missing public identity")
    require(set(op)==set(np),"Public port names changed")
    for name in op:
        require(op[name]["full_partition"]==np[name]["full_partition"],"Public name/terminal partition changed")
        require(op[name]["full_anchor"]==np[name]["full_anchor"],"Public name/anchor binding changed")
    ol=topology.normalized_locations(old["locations"],oi);nl=topology.normalized_locations(new["locations"],ni)
    for rows,side in ((ol,old),(nl,new)):
        paths={r["native_device"]:r for r in side["paths"]}
        for row in rows["devices"]:
            witness=paths[row["native_id"]]
            require(row["pcell"]["path"]==witness["raw_path"],"Stable witness not bound to exact raw location")
            row["pcell"]["path"]=witness["stable_path"]
    require(ol==nl,"Full semantic device/parameter/location data changed")
    require(topology.normalized_anchors(old["anchors"],oi)==topology.normalized_anchors(new["anchors"],ni),
      "Complete original 978 anchors changed")
    return {"status":"PASS_COMPLETE_NATIVE_IDENTITIES_WITH_OBSERVED_TOPOLOGY_COUNTS",
      "devices":500,"terminals":1446,"ports":25,"anchors":978,"native_nets":len(ni["nets"]),
      "old_native_port_order":[p["name"] for p in old["native_pins"]],
      "new_native_port_order":[p["name"] for p in new["native_pins"]],
      "native_port_ids_preserved_as_evidence_not_assumed_equal":True,
      "all_levels_and_instance_ordinals_and_transforms_equal":True,
      "no_historical_failure_or_acceptance_transferred":True,"physical_accepted":False,"electrical_accepted":False,
      "qualified_pex":False,"topology_count_checks_derived_from_complete_observations":True}

def derived_sources(source_root,config):
    oldtop='nssoc_cdr_pd500_active_input_v57'
    records={};texts={}
    for origin,name in ((PARENT,'check_width_parent_geometry.py'),(PLANES,'width_planes.py'),(RECOVER,'width_source_pins.py')):
        text=source_text(source_root,origin,config);count=text.count(oldtop)
        require(count>0,'original top substitution exists')
        generated=text.replace(oldtop,TOP)
        changes=[dict(before=oldtop,after=TOP,count=count)]
        if origin==PLANES:
            before='from check_cdr_sampler_active_input_v57_parent_geometry import check'
            after='from check_width_parent_geometry import check'
            require(generated.count(before)==1,'one parent geometry import')
            generated=generated.replace(before,after);changes.append(dict(before=before,after=after,count=1))
        texts[name]=generated
        records[name]=dict(source=origin,source_pin=config['frozen_definitions'][origin],
            generated_pin=projection.fingerprint(generated.encode()),changes=changes,
            execution_scope='Only frozen native/recover definitions; unused historical main/admission and imports are not executed.')
    return texts,records

def prepare(reference,physical,out,source_root,config,reference_members,physical_members):
    validate_config(config);out=Path(out);source_root=Path(source_root)
    require(out.is_absolute()and out.resolve()==out and not out.exists()and not out.is_symlink(),'new core output')
    out.mkdir(parents=True)
    view=out/'candidate'
    result=projection.project_view(reference,physical,view,source_root,reference_members,physical_members,
        config['reference_prefix'],config['candidate']['gds'],config['wire_workers'])
    texts,records=derived_sources(source_root,config)
    for name,text in texts.items():projection.write_new(view,'methods/'+name,text.encode())
    projection.write_new(out,'derived-methods.json',encode(records))
    projection.write_new(out,'projection-binding.json',encode(dict(projection=result,methods=records,
        immutable_reference_members=reference_members,immutable_physical_members=physical_members,**FLAGS)))
    verify_prepared(view,source_root,config)
    return view

def verify_prepared(view,source_root,config):
    view=Path(view);texts,records=derived_sources(source_root,config)
    projected=read_json(projection.regular(view,'projection.json'))
    require(projected['status']=='PROJECTED_CANDIDATE_VIEW_NOT_EXECUTED_OR_QUALIFIED'and projected['candidate']==config['candidate']['gds'],'original projection identity')
    for name,expected in projected['outputs'].items():
        require(pin(projection.regular(view,name))==expected,'all original projected inputs unchanged: '+name)
    for name,text in texts.items():require(projection.regular(view,'methods/'+name).read_bytes()==text.encode(),'exact derived helper')
    for name in projection.WORKERS:
        require(projection.regular(view,'wire/'+name).read_bytes()==projection.regular(source_root,projection.WIRE_SOURCE+name).read_bytes(),'frozen projected worker')
    require(pin(projection.regular(view,'parent/layout/'+TOP+'.gds'))==config['candidate']['gds'],'actual candidate remains unchanged')
    return records

def derived_scope(mode,view,source_root,config):
    require(mode in ('planes','recover'),'exact primitive mode')
    verify_prepared(view,source_root,config)
    name,entry={'planes':('width_planes.py','native'),'recover':('width_source_pins.py','recover')}[mode]
    path=view/'methods'/name
    scope=dict(__file__=str(path),__name__='candidate_bound_frozen_definition',OUT=view,ROOT=source_root,TOP=TOP,
        Path=Path,json=json,re=re,copy=copy,hashlib=hashlib,Counter=collections.Counter,
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(),
        METALS=(8,10,30,50,67,126,134),MODELS={'npn13G2','rppd','ptap1','cmim','nmos'})
    definitions(path.read_text(),[entry],scope,path)
    return scope,entry

def derived(mode,view,source_root,config):
    """Called only by the separate admitted hosted native entry."""
    scope,entry=derived_scope(mode,view,source_root,config)
    directory=str(view/'methods')
    require('check_width_parent_geometry'not in sys.modules,'no preloaded geometry replacement')
    sys.path.insert(0,directory)
    try:scope[entry]()
    finally:
        require(sys.path[0]==directory,'helper import path unchanged')
        sys.path.pop(0)
    verify_prepared(view,source_root,config)

def selected_files(prefix=''):
    return {k:prefix+v for k,v in dict(gds='parent/layout/'+TOP+'.gds',lvs='parent/physical/lvs_flat/result.lvsdb',
        inventory='wire/pcell-inventory01.json',graph='wire/native05/result.json',
        locations='wire/device-locations01.json',anchors='wire/anchors08.json').items()}

def component_keys(graph):
    index=graph_index(graph);result={}
    for row in graph['wire_components']:
        key=index['nets'][row['native_cluster']]['key']
        require(key not in result,'one conductor per complete native partition');result[key]=row
    require(len(result)==len(graph['wire_components']),'all observed conductor components')
    return index,result

def target_keys(graph):
    index=graph_index(graph);result={};clusters={}
    for device in TARGETS:
        terminal=(device,'sg13_lv_nmos','D');require(terminal in index['terminals'],'actual drain terminal')
        cluster=index['terminals'][terminal];clusters[device]=cluster
        result['T%03d_D'%device]=index['nets'][cluster]['key']
    require(len(set(result.values()))==2,'two actual drain partitions')
    for group in (TARGETS[:4],TARGETS[4:]):
        require(len({result['T%03d_D'%d]for d in group})==1,'four-drain ownership')
    return result,clusters

def declarations(generation,config,old_graph,new_graph):
    require(generation['status']=='GENERATED_DECLARED_VIA2_M3_CANDIDATE_REQUIRES_FRESH_DRC_LVS_RC_WAVES' and generation['geometry_generated']is True,'actual generation outcome')
    require(generation['proof']['candidate']==config['candidate']['gds'] and generation['proof']['structural_reversal_exact']is True and generation['original_full_rails_unchanged']is True,'serialized candidate and structural preservation')
    rows=generation['proof']['added_records'];require(rows==config['generation']['added_records'],'exact complete 16 observed additions')
    require(len(rows)==16 and {(r['device'],r['layer'])for r in rows}=={(d,l)for d in TARGETS for l in (29,30)},'eight vias and eight M3 straps')
    _,old_components=component_keys(old_graph);keys,clusters=target_keys(old_graph)
    newkeys,_=target_keys(new_graph);require(keys==newkeys,'same complete target partitions')
    grouped={}
    for row in rows:
        require(set(row)=={'box_dbu','component','datatype','device','layer','native_cluster'}and row['datatype']==0,'actual declaration schema')
        key=keys['T%03d_D'%row['device']];owner=old_components[key]
        require(row['native_cluster']==clusters[row['device']] and row['component']==owner['component'],'original full native owner')
        box=row['box_dbu'];require(len(box)==4 and all(type(v)is int and v%5==0 for v in box) and box[0]<box[2] and box[1]<box[3],'integer five nm boxes')
        if row['layer']==29:require(box[2]-box[0]==box[3]-box[1]==190,'exact Via2')
        else:require(box[2]-box[0]==400 and box[3]-box[1]==18000,'exact M3 strap')
        grouped.setdefault((key,row['layer']),[]).append(box)
    return grouped,keys

def exact_union(pya,before,after,boxes):
    expected=before.dup()
    for box in boxes:expected.insert(pya.Box(*box))
    require((expected.merged()^after.merged()).is_empty(),'exact all-layer material union')

def layer_region(pya,wire,net,graph,layer):
    info=graph['layers'][str(layer)]
    require(type(info['explicitly_empty'])is bool,'explicit observed layer disposition')
    native=wire.layer_by_name('gds_'+str(layer))
    if info['explicitly_empty']:
        require(native is None,'empty native layer unregistered')
        return pya.Region()
    require(native is not None,'complete actual conductor layer')
    return wire.shapes_of_net(net,native,True).merged()

def prove_material(pya,reference,view,old,new,source_root,config):
    _,before=component_keys(old['graph']);_,after=component_keys(new['graph'])
    require(set(before)==set(after),'all full conductor partitions retained')
    generation_path=projection.regular(source_root,config['generation']['proof_path'])
    require(pin(generation_path)==config['generation']['pin'],'unchanged original generation evidence')
    generation=read_json(generation_path)
    grouped,targets=declarations(generation,config,old['graph'],new['graph'])
    ow=pya.LayoutToNetlist();ow.read(str(reference/(config['reference_prefix']+'wire/native05/wires.l2n')))
    nw=pya.LayoutToNetlist();nw.read(str(view/'wire/native05/wires.l2n'))
    on={n.cluster_id:n for n in ow.netlist().top_circuit().each_net()}
    nn={n.cluster_id:n for n in nw.netlist().top_circuit().each_net()}
    require(set(on)=={r['component']for r in before.values()}and set(nn)=={r['component']for r in after.values()},'actual complete wire net census')
    require(set(old['graph']['layers'])==set(new['graph']['layers'])=={str(n)for n in LAYERS},'all seven metals and six vias')
    records=[]
    for key in sorted(before):
        a=before[key];b=after[key]
        for layer in LAYERS:
            left=layer_region(pya,ow,on[a['component']],old['graph'],layer)
            right=layer_region(pya,nw,nn[b['component']],new['graph'],layer)
            boxes=grouped.get((key,layer),[]);exact_union(pya,left,right,boxes)
            records.append(dict(partition=json.loads(key),layer=layer,old_component=a['component'],new_component=b['component'],
                old_native_cluster=a['native_cluster'],new_native_cluster=b['native_cluster'],
                old_area_dbu2=left.area(),new_area_dbu2=right.area(),declared_additions=boxes))
    require(len(records)==len(before)*len(LAYERS)and sum(len(r['declared_additions'])for r in records)==16,'complete observed full-layer union census')
    return dict(status='PASS_ALL_OBSERVED_COMPONENTS_ALL13LAYERS_EXACT16_VIA2_M3_ADDITIONS',
        records=records,observed_old_components=len(before),observed_new_components=len(after),layers=len(LAYERS),added_shapes=16,
        generation=pin(generation_path),targets={k:dict(full_partition=json.loads(v),old=before[v],new=after[v])for k,v in targets.items()},
        resistor_reduction_identity_assumed=False,transient_voltage_recovery_proved=False,**FLAGS)

def report_inputs(report,view):
    require(type(report['inputs'])is dict and report['inputs'],'complete fresh report inputs')
    result={}
    for name,expected in report['inputs'].items():
        p=Path(name)
        require(p.is_absolute()and p.resolve()==p and p.is_relative_to(view)and p.is_file()and not any(q.is_symlink()for q in (p,*p.parents)),'fresh report input ownership')
        digest=expected['sha256']if isinstance(expected,dict)else expected
        require(pin(p)['sha256']==digest,'fresh report exact bytes')
        if isinstance(expected,dict):require(pin(p)==expected,'fresh report byte size')
        result[name]=pin(p)
    return result

def verify(reference,physical,view,out,source_root,config):
    import pya
    validate_config(config);verify_prepared(view,source_root,config)
    require(pin(reference/(config['reference_prefix']+'parent/layout/'+TOP+'.gds'))==config['original_reference_gds'],'exact original graph geometry')
    planes=read_json(view/'native-planes.json');recovery=read_json(view/'wire/source-pins.json')
    require(planes['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'and len(planes['anchors'])==160 and len(planes['controls'])==19,'all native planes and faults')
    parent=planes['parent_geometry']
    require(len(parent['controls'])==5 and len(parent['actual_placements'])==16 and len(parent['checked_layers_by_kind'])==9,'all independent original leaves and transforms')
    require(recovery['status']=='PASS_RECOVERED_SOURCE_PIN_BOXES_ON_IDENTICAL_PRIMITIVE_DRAWING'and recovery['target_gds_sha256']==config['candidate']['gds']['sha256']and recovery['target_geometry_edited']is False and recovery['missing_referenced_primitive_rejected']is True,'actual recovered source pins')
    identities=identity_namespace(source_root,config)
    producer=source_root/(projection.WIRE_SOURCE+'locate01.py')
    old_layout,old=identities.read_side(pya,reference,selected_files(config['reference_prefix']),producer)
    new_layout,new=identities.read_side(pya,view,selected_files(),producer)
    comparison=identities.compare_witnesses(old,new)
    faults=identities.witness_controls(old,new)
    material=prove_material(pya,reference,view,old,new,source_root,config)
    reports={'parent-geometry':parent,'planes':planes,'source-pins':recovery,'graph':new['graph'],'locations':new['locations'],'anchors':new['anchors']}
    bindings={n:report_inputs(r,view)for n,r in reports.items()}
    for name,value in (('old-native-identity.json',old),('new-native-identity.json',new),('native-identity-comparison.json',comparison),
        ('actual-witness-faults.json',faults),('full-partition-material.json',material),('fresh-report-bindings.json',bindings)):
        projection.write_new(out,name,encode(value))
    files=projection.inventory(view)
    result=dict(status='PASS_CANDIDATE_BOUND_CANONICAL_VIEW_REQUIRES_FRESH_RC',
        candidate_gds=config['candidate']['gds'],candidate_flat_lvs=pin(view/'parent/physical/lvs_flat/result.lvsdb'),
        physical_producer=config['physical_binding'],generation=config['generation']['pin'],current_files=files,
        complete_current_file_count=len(files),native_identity=comparison,material=pin(out/'full-partition-material.json'),
        native_view_executed=True,fresh_report_bindings=bindings,**FLAGS)
    projection.write_new(out,'canonical-view-qualification.json',encode(result))
    return result

def authorize_native(*args,**kwargs):
    raise AssertionError('CORE_HAS_NO_NATIVE_AUTHORITY: use a separately reviewed hosted admission and entry')

if __name__=='__main__':authorize_native()
