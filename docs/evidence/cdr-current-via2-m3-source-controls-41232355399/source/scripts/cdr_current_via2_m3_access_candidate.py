#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One declared eight-drain Via2/M3 candidate; actual execution remains disabled."""
import argparse,collections,hashlib,json,os,re,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN='scripts/cdr-current-via2-m3-access-plan.json'
PINS='scripts/cdr-current-via2-m3-access-source-pins.json'
BRANCH='codex/cdr-current-via2-m3-access-candidate'
DEVICES=(3,4,5,6,32,33,34,35)
FLAGS=dict(physical_acceptance=False,electrical_accepted=False,full_phy_accepted=False,
 timing_accepted=False,qualified_pex=False,causality_proven=False,new_simulation=False)
def require(value,message):
    if not value:raise AssertionError(message)
def encoded(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def file_pin(path):
    require(path.is_file()and not path.is_symlink(),'regular immutable file: '+str(path))
    with path.open('rb')as f:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def regular(root,name):
    p=Path(name);require(not p.is_absolute()and p.parts and all(x not in('','..','.')for x in p.parts),'relative regular path')
    current=root
    for part in p.parts:current=current/part;require(not current.is_symlink(),'symlink input')
    require(current.is_file(),'missing regular input');return current

def source_guard(root=ROOT):
    e=os.environ
    require(e.get('GITHUB_ACTIONS')=='true'and e.get('RUNNER_ENVIRONMENT')=='github-hosted'and e.get('RUNNER_OS')=='Linux','hosted Linux only')
    require(e.get('GITHUB_EVENT_NAME')=='workflow_dispatch'and e.get('GITHUB_RUN_ATTEMPT')=='1','manual attempt one')
    require(e.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and e.get('GITHUB_REF')=='refs/heads/'+BRANCH,'exact repository and branch')
    require(re.fullmatch('[0-9a-f]{40}',e.get('GITHUB_SHA',''))is not None,'source identity')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==e['GITHUB_SHA'],'exact checkout')
    raw=regular(root,PINS).read_bytes()
    require(raw==subprocess.check_output(['git','show',e['GITHUB_SHA']+':'+PINS],cwd=root),'manifest Git identity')
    m=json.loads(raw)
    for p,pin in m['files'].items():require(file_pin(regular(root,p))==pin,'protected source changed: '+p)
    plan=json.loads(regular(root,PLAN).read_bytes());validate_plan(plan)
    return plan

def validate_plan(plan):
    require(plan['schema']=='cdr-current-eight-drain-via2-m3-candidate-v1'and plan['branch']==BRANCH,'candidate identity')
    require(plan['top']=='nssoc_cdr_pd500_resistor_v59'and plan['dbu_um']==.001 and plan['grid_dbu']==5,'original layout units')
    require(plan['source_controls_authorized']is True and plan['all_acceptance_false']is True,'source-only scope')
    for k in('candidate_generation_authorized','physical_verification_authorized','fresh_rc_authorized','electrical_simulation_authorized'):
        require(plan[k]is False,'actual candidate execution requires a reviewed execution adapter; disabled here')
    expected=dict(metal3_width_dbu=400,via2_size_dbu=190,metal_enclosure_dbu=50,foreign_metal3_clearance_dbu=605,existing_via2_clearance_dbu=295,foreign_via2_via3_guard_dbu=5)
    require(plan['parameters']==expected,'single fixed conservative candidate')
    require(tuple(r['device']for r in plan['targets'])==DEVICES,'exact ordered eight drains')
    for row in plan['targets']:
        d=row['device'];expected=(17,28,'$131')if d<32 else(61,135,'$699')
        require((row['component'],row['native_cluster'],row['native_name'])==expected,'actual current net identity')
        require(row['label']=='T%03d_D'%d and row['original_R_material_attributed']is False,'real drain and no material attribution')
        require(row['existing_rail']['actual_anchor']['point_dbu']==row['anchor_dbu'],'actual primitive anchor')
        require(all(type(v)is int and v%5==0 for v in row['anchor_dbu']),'integer five nm anchor grid')
        shape=row['upper_metal3'];owners=shape['ownership']['candidates']
        require(shape['gds_layer']==30 and shape['gds_datatype']==0 and shape['ownership']['electrical_owner_proved']is True and len(owners)==1,'unique actual upper M3 ownership')
        require(owners[0]['complete_shape_within_component']is True and(owners[0]['component'],owners[0]['native_cluster'],owners[0]['native_name'])==expected,'full upper M3 electrical owner')
    return True

def rectangles(row):
    # The R-card endpoints select an inspection target, never a resistor footprint.
    x,y=row['anchor_dbu'];left,bottom,right,top=row['upper_metal3']['top_bbox_dbu']
    require(top-bottom==400 and right-x==200 and bottom>y and left<x-200,'actual upper M3 landing geometry')
    require((bottom+top)//2-y==17600,'exact observed upper-branch separation')
    return {29:[x-95,y-95,x+95,y+95],30:[x-200,y-200,x+200,top]},[x-200,bottom,x+200,top]

def guard_regions(pya,row,owned,full,non_drawing=None):
    boxes,landing=rectangles(row);cut=pya.Region(pya.Box(*boxes[29]));metal=pya.Region(pya.Box(*boxes[30]));land=pya.Region(pya.Box(*landing))
    require((cut.sized(50)-owned[10]).is_empty(),'Via2 lower M2 enclosure and owner')
    require((cut.sized(50)-metal).is_empty(),'Via2 upper new M3 enclosure')
    require((land-owned[30]).is_empty(),'whole upper landing lies in same-net M3')
    require(not(metal-full[30]).is_empty(),'M3 branch must add real material')
    require(cut.sized(295).interacting(full[29]).is_empty(),'new Via2 clearance from every existing Via2')
    require(metal.sized(605).interacting(full[30]-owned[30]).is_empty(),'new M3 clearance from every foreign M3')
    for layer in(29,49):require(metal.sized(5).interacting(full[layer]-owned[layer]).is_empty(),'new M3 cannot connect a foreign via'+str(layer))
    require(cut.sized(5).interacting(full[10]-owned[10]).is_empty(),'new Via2 cannot touch foreign M2')
    for layer,region in(non_drawing or {}).items():
        candidate=metal.sized(605)if layer[0]==30 else cut.sized(295)
        require(candidate.interacting(region).is_empty(),'unclassified non-drawing conductor datatype '+str(layer))
    return boxes

def raw_records(layout,cell):
    rows=[]
    for li in layout.layer_indexes():
        info=layout.get_info(li)
        for shape in cell.shapes(li).each():
            rows.append((info.layer,info.datatype,shape.to_s(),
                         json.dumps(shape.properties(),sort_keys=True,separators=(",",":")),shape.is_text()))
    return sorted(rows)

def hierarchy(cell):
    return sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in cell.each_inst())

def material(pya,layout,cell,recursive=False):
    out={}
    for li in layout.layer_indexes():
        info=layout.get_info(li);key=(info.layer,info.datatype)
        it=cell.begin_shapes_rec(li) if recursive else cell.shapes(li)
        r=pya.Region(it).flatten().merged()
        if not r.is_empty():out[key]=r
    return out

def same_material(pya,expected,actual):
    assert set(expected)==set(actual),("Changed material layer census",set(expected)^set(actual))
    for key in expected:
        assert (expected[key]^actual[key]).is_empty(),("Changed material",key)

def properties(inst):
    rows=[{"key_type":type(k).__name__,"key":k,"value_type":type(v).__name__,"value":v}
      for k,v in inst.properties().items()]
    return sorted(rows,key=lambda r:json.dumps(r,sort_keys=True,separators=(",",":"),allow_nan=False))

def snapshot(pya,layout):
    return{c.name:dict(raw=raw_records(layout,c),material=material(pya,layout,c),hierarchy=hierarchy(c),
      cell_properties=properties(c),instance_properties=[properties(i)for i in c.each_inst()])for c in layout.each_cell()}

def validate_serialized(pya,layout,before,top_name,expected_raw,expected_material,bbox):
    require(layout.dbu==.001 and{c.name for c in layout.each_cell()}==set(before),'complete original cells and DBU')
    require(layout.cell(top_name).bbox()==bbox,'complete original bbox')
    for c in layout.each_cell():
        old=before[c.name];is_top=c.name==top_name
        require(raw_records(layout,c)==(expected_raw if is_top else old['raw']),'exact original raw shapes and declared additions')
        require(hierarchy(c)==old['hierarchy']and properties(c)==old['cell_properties'],'original hierarchy and cell properties')
        require([properties(i)for i in c.each_inst()]==old['instance_properties'],'original instance properties')
        same_material(pya,expected_material if is_top else old['material'],material(pya,layout,c))

def add_and_reverse(pya,layout,rows,out):
    top_name='nssoc_cdr_pd500_resistor_v59';top=layout.cell(top_name);before=snapshot(pya,layout);bbox=top.bbox()
    require(len(rows)==16 and collections.Counter(r['layer']for r in rows)=={29:8,30:8},'exact 8 Via2 plus 8 M3 raw shapes')
    require(len({(r['layer'],tuple(r['box_dbu']))for r in rows})==16,'distinct additions')
    scratch=pya.Layout();scratch.dbu=.001;extra=scratch.create_cell('declared_only')
    expected=dict(before[top_name]['material'])
    for row in rows:
        layer=row['layer'];box=pya.Box(*row['box_dbu']);require(layer in(29,30),'no M1/M2 or primitive change')
        extra.shapes(scratch.layer(layer,0)).insert(box)
        expected[(layer,0)]=(expected.get((layer,0),pya.Region())+pya.Region(box)).merged()
    extra_raw=raw_records(scratch,extra);require(not any(r in before[top_name]['raw']for r in extra_raw),'do not duplicate existing raw shape')
    wanted=sorted(before[top_name]['raw']+extra_raw)
    for row in rows:top.shapes(layout.layer(row['layer'],0)).insert(pya.Box(*row['box_dbu']))
    validate_serialized(pya,layout,before,top_name,wanted,expected,bbox)
    candidate=out/(top_name+'.gds');require(not candidate.exists(),'candidate no overwrite');layout.write(str(candidate))
    checked=pya.Layout();checked.read(str(candidate));validate_serialized(pya,checked,before,top_name,wanted,expected,bbox)
    for row in rows:
        shapes=[s for s in checked.cell(top_name).shapes(checked.layer(row['layer'],0)).each()if s.is_box()and s.box==pya.Box(*row['box_dbu'])and not s.properties()]
        require(len(shapes)==1,'unique declared addition to undo');shapes[0].delete()
    validate_serialized(pya,checked,before,top_name,before[top_name]['raw'],before[top_name]['material'],bbox)
    restored=out/'reversed-original-geometry.gds';require(not restored.exists(),'reversal no overwrite');checked.write(str(restored))
    reread=pya.Layout();reread.read(str(restored));validate_serialized(pya,reread,before,top_name,before[top_name]['raw'],before[top_name]['material'],bbox)
    return dict(candidate=file_pin(candidate),reverse=file_pin(restored),structural_reversal_exact=True,original_file_byte_equality_claimed=False,added_records=rows)

def generate_reviewed_candidate(pya,selected,out,config,root=ROOT):
    # This body is reviewable, but the source-only plan intentionally forbids entry.
    plan=source_guard(root)
    require(plan['candidate_generation_authorized']is True,'candidate generation is disabled pending execution adapter review')
    import cdr_current_access_geometry_native as prior
    require(file_pin(regular(root,plan['native']['qualified_geometry_config']))['sha256']==plan['native']['qualified_geometry_config_sha256'],'original qualified geometry config')
    require(config['selected']==plan['native']['members'],'same complete selected native model capsule')
    before_inputs={n:file_pin(regular(selected,n))for n in config['selected']}
    require(all(p['sha256']==config['selected'][n]for n,p in before_inputs.items()),'original selected native input hash')
    saved={}
    def save(name,value):
        saved[name]=value;target=out/name;require(not target.exists(),'evidence no overwrite');target.write_bytes(encoded(value))
    incidence=json.loads(regular(root,config['incidence']).read_bytes())
    save('coordinate-source-binding.json',prior.unit_binding(pya,selected,config,incidence))
    report=prior.observe(pya,selected,config,root,save);save('original-geometry-observation.json',report)
    windows=saved['dominant-access-windows.json'];rails=saved['existing-full-drain-rails.json']
    for row in plan['targets']:
        actual=[r for r in rails['rails']if r['device']==row['device']]
        require(actual==[row['existing_rail']],'exact whole existing M1/M2 rail and primitive identity')
        edge=[e for e in windows['edges']if e['edge']['id']==row['original_R_card']['id']]
        require(len(edge)==1 and edge[0]['edge']==row['original_R_card'],'original raw R-card identity')
        shapes=[s for s in edge[0]['raw_shapes']if s['id']==row['upper_metal3']['id']]
        require(shapes==[row['upper_metal3']],'exact actual upper same-net M3 raw shape')
    g=pya.Layout();g.read(str(regular(selected,config['paths']['gds'])));top=g.cell(plan['top'])
    w=pya.LayoutToNetlist();w.read(str(regular(selected,config['paths']['wires'])))
    nets={n.cluster_id:n for n in w.netlist().top_circuit().each_net()};full={};objects={}
    for layer in(10,29,30,49):
        objects[layer]=w.layer_by_name('gds_'+str(layer));require(objects[layer]is not None,'full wire layer')
        full[layer]=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged()
        require((full[layer]^objects[layer]).is_empty(),'whole GDS/wire layer union')
    other={}
    for li in g.layer_indexes():
        info=g.get_info(li)
        if info.layer in(29,30)and info.datatype!=0:
            other[(info.layer,info.datatype)]=pya.Region(top.begin_shapes_rec(li)).merged()
    rows=[];new_regions={}
    for row in plan['targets']:
        owned={layer:w.shapes_of_net(nets[row['component']],objects[layer],True).merged()for layer in full}
        proposal=dict(device=row['device'],original_R_card=row['original_R_card'],planned_boxes=rectangles(row)[0],guards_passed=False,**FLAGS)
        save('device-%03d-proposal.json'%row['device'],proposal)
        boxes=guard_regions(pya,row,owned,full,other)
        for layer,box in boxes.items():
            region=pya.Region(pya.Box(*box))
            for owner,prior_region in new_regions.get(layer,[]):
                if owner!=row['component']:require(region.sized(605 if layer==30 else 295).interacting(prior_region).is_empty(),'new-to-new foreign access clearance')
            new_regions.setdefault(layer,[]).append((row['component'],region))
            rows.append(dict(device=row['device'],component=row['component'],native_cluster=row['native_cluster'],layer=layer,datatype=0,box_dbu=box))
        save('device-%03d-admission.json'%row['device'],dict(proposal,guards_passed=True))
    proof=add_and_reverse(pya,g,rows,out)
    require(before_inputs=={n:file_pin(regular(selected,n))for n in config['selected']},'all original native input bytes unchanged')
    save('generation.json',dict(status='GENERATED_DECLARED_VIA2_M3_CANDIDATE_REQUIRES_FRESH_DRC_LVS_RC_WAVES',proof=proof,
      original_full_rails_unchanged=True,geometry_generated=True,DRC_executed=False,LVS_executed=False,RC_executed=False,**FLAGS))
    return proof

if __name__=='__main__':
    raise SystemExit('Actual generation disabled. Source controls use the independent hosted synthetic checker.')
