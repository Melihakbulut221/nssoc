#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit independent physical adapter entry; original candidate guards are shared unchanged."""
import argparse,json,os,shutil,traceback
from pathlib import Path
import cdr_current_via2_m3_physical_admission as a
import cdr_current_via2_m3_access_candidate as original
from cdr_current_via2_m3_access_candidate import require,file_pin,regular,encoded,rectangles,guard_regions,add_and_reverse,FLAGS
ROOT=a.ROOT
def generate_current_candidate(pya,selected,out,config,preflight,root=ROOT):
    ctx=a.context(os.environ);method=a.source_guard(ctx,root)
    a.native_preflight(preflight,ctx,method,selected,root)
    plan=json.loads(a.q.regular(root,method['candidate_plan']).read_bytes())
    original.validate_plan(plan)
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

def main():
    p=argparse.ArgumentParser();p.add_argument('--selected',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight',type=Path,required=True);args=p.parse_args()
    ctx=a.context(os.environ);c=a.source_guard(ctx);a.native_preflight(args.preflight,ctx,c,args.selected)
    require(not args.output.exists()and not args.output.is_symlink(),'new owned native output');args.output.mkdir(parents=True)
    import pya
    try:
        geometry=json.loads(a.q.regular(ROOT,c['geometry_config']).read_bytes())
        generation=generate_current_candidate(pya,args.selected,args.output,geometry,args.preflight)
        support=c['support_members'];old=json.loads(a.q.regular(args.selected,support['layout_result']).read_bytes())
        require(len(old['ports'])==25,'exact original physical ports')
        for key,name in(('lef','nssoc_cdr_pd500_resistor_v59.lef'),('schematic','schematic.cir')):
            source=a.q.regular(args.selected,support[key]);target=args.output/name
            require(not target.exists(),'support no overwrite');shutil.copyfile(source,target)
            require(file_pin(source)==file_pin(target),'unchanged physical reference')
        outputs={name:file_pin(args.output/name)['sha256']for name in('nssoc_cdr_pd500_resistor_v59.gds','nssoc_cdr_pd500_resistor_v59.lef','schematic.cir')}
        result=dict(status='GENERATED_VIA2_M3_REQUIRES_FULL_PHYSICAL_RC_AND_ORIGINAL_WAVES',ports=old['ports'],
          inputs={str(a.q.regular(args.selected,n)):h for n,h in c['selected'].items()},outputs=outputs,**FLAGS)
        (args.output/'result.json').write_bytes(encoded(result))
        a.source_guard(ctx);a.native_preflight(args.preflight,ctx,c,args.selected)
    except BaseException as error:
        (args.output/'native-failure.json').write_bytes(encoded(dict(error=repr(error),traceback=traceback.format_exc(),**FLAGS)));raise
if __name__=='__main__':main()
