#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only native survey; never emits or accepts candidate layout."""
import hashlib, json, math, textwrap
from pathlib import Path
import pya

GENERATOR_SHA='9485afdff48bd00b7bd3ba0b761980c3a0d187be4fe0a3a127a93307449b17fb'
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
CLEARANCE={m:2000 if m in (126,134) else 500 for m in (*METALS,*VIAS)}
CLEARANCE.update({m:300 for m in VIAS})

def survey(ctx, namespace):
    args=ctx['args'];L=ctx['L'];T=ctx['T'];own=ctx['own'];total=ctx['total']
    require=namespace['require'];sha=namespace['sha'];plans=ctx['plans']
    source=Path(namespace['SURVEY_ORIGINAL_GENERATOR']).read_text()
    require(hashlib.sha256(source.encode()).hexdigest()==GENERATOR_SHA,'Survey source differs')
    require(namespace['CLEARANCE']==CLEARANCE,'Planning clearances changed')
    # Native renderer and primitive invocation list are copied verbatim from the
    # frozen generator. Execution stops before ANY parent insertion/write.
    a=source.index('    def via(');b=source.index('            clear(reg, info.layer, plan)',a)
    render=textwrap.dedent(source[a:b]+'            rendered[info.layer] = reg\n        return dict(cell=cell,transform=tr,parameters=parameters,rendered=rendered)\n')
    env=dict(namespace);env.update(ctx);exec(compile(render,'<exact-native-via-render-prefix>','exec'),env)
    native_via=env['via']
    primitives=[]
    def collect_via(bottom_name,top_name,point,plan,purpose,columns=8,upper=False,original_via4=None):
        v=native_via(bottom_name,top_name,point,plan,purpose,columns,upper,original_via4)
        layer_name={'Metal1':8,'Metal3':30,'Metal4':50,'Metal5':67,'TopMetal1':126,'TopMetal2':134}
        require(layer_name[bottom_name]in v['rendered']and layer_name[top_name]in v['rendered'],'Native via endpoint missing')
        require(not(v['rendered'][layer_name[bottom_name]]&own[plan['gain_native_id']][layer_name[bottom_name]]).is_empty(),'Rendered bottom landing misses original owned metal')
        if original_via4 is not None:
            expected=pya.Region()
            for box in original_via4:expected+=pya.Region(pya.Box(*box))
            ctx['exact_original_via4'](v['rendered'][66],expected.merged(),own[plan['gain_native_id']][66])
        primitives.append(dict(kind='via',gain=plan['gain_native_id'],plan=plan,purpose=purpose,
            point=list(point),parameters=v['parameters'],transform=str(v['transform']),
            exact_original_via4=original_via4 is not None,regions=v['rendered']))
    def collect_region(layer,region,plan,purpose):
        primitives.append(dict(kind='line',gain=plan['gain_native_id'],plan=plan,purpose=purpose,regions={layer:region},layer=layer))
    # This entire line function, including Manhattan/grid checks and endcaps,
    # is unchanged; only its add_region binding collects instead of inserting.
    a=source.index('    def add_line(');b=source.index('    def exact_original_via4(',a)
    env['add_region']=collect_region
    exec(compile(textwrap.dedent(source[a:b]),'<exact-line-renderer>','exec'),env)
    original_line=env['add_line']
    def collect_line(layer,a,b,width,plan,purpose):
        original_line(layer,a,b,width,plan,purpose)
        primitives[-1].update(a=list(a),b=list(b),width=width)
    a=source.index('    diagnostic_active = True\n');b=source.index('    def equal_snapshot(',a)
    calls=textwrap.dedent(source[a:b])
    env.update(via=collect_via,add_line=collect_line,landing=ctx['landing'])
    exec(compile(calls,'<exact-all-candidate-calls>','exec'),env)
    require(len(primitives)==44 and sum(p['kind']=='via'for p in primitives)==28,'Incomplete primitive inventory')
    require(sum(p.get('exact_original_via4',False)for p in primitives)==8,'Missing original high cuts')
    for i,p in enumerate(primitives):p['id']=i
    bylayer={m:[]for m in CLEARANCE}
    for p in primitives:
        for m,reg in p['regions'].items():bylayer[m].append((p['id'],p['gain'],reg))
    wire=ctx['wire'];graph=ctx['graph']
    original_owners={m:[]for m in CLEARANCE}
    records={r['component']:r for r in graph['wire_components']}
    for net in wire.netlist().top_circuit().each_net():
        require(net.cluster_id in records,'Native wire mapping absent')
        for m in CLEARANCE:
            reg=wire.shapes_of_net(net,wire.layer_by_name('gds_'+str(m)),True).flatten().merged()
            if not reg.is_empty():original_owners[m].append((records[net.cluster_id],reg))
    drawing={m:[('root_direct',pya.Region(T.shapes(L.layer(m,0))).merged())]for m in CLEARANCE}
    for inst in T.each_inst():
        for m in CLEARANCE:
            reg=pya.Region(inst.cell.begin_shapes_rec(L.layer(m,0))).transformed(inst.cplx_trans).merged()
            if not reg.is_empty():drawing[m].append((inst.cell.name+'@'+str(inst.dcplx_trans),reg))
    def polygons(reg):return[str(q)for q in reg.merged().each()]
    def foreign(gain,layer):
        result=total[layer]-own[gain][layer]
        for _,other,region in bylayer[layer]:
            if other!=gain:result+=region
        return result.merged()
    def adjacent(layer):
        if layer not in METALS:return[]
        i=METALS.index(layer)
        return([VIAS[i-1]]if i else[])+([VIAS[i]]if i<len(VIAS)else[])
    def detail(gain,layer,region):
        f=foreign(gain,layer);collision=(region.sized(CLEARANCE[layer])&f).merged()
        old_collisions=[];candidate_collisions=[]
        for record,piece in original_owners[layer]:
            if record['native_cluster']==next(p['native_cluster']for p in plans if p['gain_native_id']==gain):continue
            hit=(piece&region.sized(CLEARANCE[layer])).merged()
            if not hit.is_empty():
                old_collisions.append(dict(wire_component=record['component'],native_cluster=record['native_cluster'],
                    native_name=record['native_name'],clipped_polygons_dbu=polygons(hit)))
        for pid,other,piece in bylayer[layer]:
            if other==gain:continue
            hit=(piece&region.sized(CLEARANCE[layer])).merged()
            if not hit.is_empty():candidate_collisions.append(dict(primitive=pid,gain=other,clipped_polygons_dbu=polygons(hit)))
        via_hits=[]
        for via in adjacent(layer):
            hit=(region&foreign(gain,via)).merged()
            if not hit.is_empty():via_hits.append(dict(layer=via,polygons_dbu=polygons(hit)))
        partial=[]
        if layer in VIAS:
            for old in own[gain][layer].interacting(region).each():
                remainder=(pya.Region(old)-region).merged()
                if not remainder.is_empty():
                    partial.append(dict(original_polygon=str(old),outside_candidate_polygons_dbu=polygons(remainder),
                        overlap_area_dbu2=(pya.Region(old)&region).area()))
        drawing_hits=[]
        for owner,piece in drawing[layer]:
            hit=(piece&collision).merged()
            if not hit.is_empty():drawing_hits.append(dict(owner=owner,clipped_polygons_dbu=polygons(hit)))
        ok=collision.is_empty()and not via_hits and not partial
        return dict(layer=layer,planning_clearance_dbu=CLEARANCE[layer],planning_clear=ok,
            candidate_polygons_dbu=polygons(region),collision_polygons_dbu=polygons(collision),
            actual_overlap_polygons_dbu=polygons(region&f),original_native_owners=old_collisions,
            candidate_foreign_owners=candidate_collisions,drawing_owners=drawing_hits,
            foreign_adjacent_cut_capture=via_hits,partial_original_cut_overlap=partial)
    inventory=[]
    for p in primitives:
        layers=[detail(p['gain'],m,reg)for m,reg in sorted(p['regions'].items())]
        item={k:v for k,v in p.items()if k not in('regions','plan')}
        item.update(layers=layers,planning_clear=all(x['planning_clear']for x in layers))
        inventory.append(item)
    # Offset corridors retain the EXACT original endpoints and width. Search
    # coordinates come from actual obstacle polygon edges, never guessed shifts.
    # Bounds limit diagnosis only; failure means no corridor in this finite search.
    corridors=[]
    tech=json.loads((args.pdk/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())
    params=tech.get('techParams',tech)
    for p in primitives:
        if p['kind']!='line':continue
        layer=p['layer'];a=p['a'];b=p['b'];width=p['width'];half=width//2
        minimum_key={30:'Mn_a',126:'TM1_a',134:'TM2_a'}[layer]
        minimum_dbu=round(float(params[minimum_key])*1000)
        require(width>=minimum_dbu,'Diagnostic corridor below pinned native minimum width')
        vertical=a[0]==b[0];axis=0 if vertical else 1
        region=p['regions'][layer];f=foreign(p['gain'],layer)
        margin=100000
        roi=pya.Region(pya.Box(min(a[0],b[0])-margin,min(a[1],b[1])-margin,max(a[0],b[0])+margin,max(a[1],b[1])+margin))
        coordinates={a[axis]};origins={}
        for poly in f.interacting(roi).each():
            points=list(poly.each_point_hull())
            for hole in range(poly.holes()):points+=list(poly.each_point_hole(hole))
            for point in points:
                edge=point.x if axis==0 else point.y
                for sign in(-1,1):
                    raw=edge+sign*(CLEARANCE[layer]+half+5)
                    value=(raw//5)*5 if sign<0 else -((-raw)//5)*5
                    if abs(value-a[axis])<=margin:
                        coordinates.add(value);origins.setdefault(value,[]).append(dict(edge_coordinate=edge,side=sign))
        def boxline(u,v):
            require(u[0]==v[0]or u[1]==v[1],'Non-Manhattan corridor')
            return pya.Region(pya.Box(min(u[0],v[0])-half,min(u[1],v[1])-half,max(u[0],v[0])+half,max(u[1],v[1])+half))
        safe=[];tested=0
        for value in sorted(coordinates,key=lambda v:(abs(v-a[axis]),v)):
            points=[a,[value,a[1]],[value,b[1]],b]if vertical else[a,[a[0],value],[b[0],value],b]
            reg=pya.Region()
            for u,v in zip(points,points[1:]):reg+=boxline(u,v)
            reg=reg.merged();tested+=1
            if not(reg.sized(CLEARANCE[layer])&f).is_empty():continue
            if any(not(reg&foreign(p['gain'],via)).is_empty()for via in adjacent(layer)):continue
            if not(reg-pya.Region(ctx['original_box'])).is_empty():continue
            safe.append(dict(points_dbu=points,width_dbu=width,layer=layer,
                actual_obstacle_edge_origins=origins.get(value,[]),offset_dbu=value-a[axis],
                polygons_dbu=polygons(reg),length_dbu=sum(abs(u[0]-v[0])+abs(u[1]-v[1])for u,v in zip(points,points[1:]))))
        corridor=dict(primitive=p['id'],gain=p['gain'],purpose=p['purpose'],layer=layer,
            original_planning_clear=inventory[p['id']]['planning_clear'],unchanged_width_dbu=width,native_minimum_width_dbu=minimum_dbu,native_minimum_parameter=minimum_key,
            finite_search_margin_dbu=margin,tested_offset_coordinates=tested,
            safe_corridor_count=len(safe),nearest_safe_corridors=safe[:4],
            scope='Planning-only against ALL original foreign metal/vias and ALL other candidate owners at unchanged layer clearance. Endpoints/width unchanged; no native DRC, combined-repair,RC or electrical acceptance.')
        if not inventory[p['id']]['planning_clear']:
            corridor['original_foreign_material_in_search_window']=polygons(f&roi)
        corridors.append(corridor)
    # Actual original hierarchy/drawings/labels stay untouched, including after
    # creating uninstantiated native PCells to inspect their real cut footprints.
    for index,before in ctx['old_cells'].items():
        after=ctx['cell_snapshot'](L,L.cell(index))
        require(before[0].keys()==after[0].keys()and before[1:]==after[1:],'Original cell inventory changed')
        require(all((before[0][k]^after[0][k]).is_empty()for k in before[0]),'Original drawing changed')
    require(T.name==ctx['original_top_name']and T.bbox()==ctx['original_box'],'Parent identity changed')
    require(all(sha(Path(q))==h for q,h in ctx['protected'].items()),'Protected native input changed')
    require(len(ctx['controls'])==8,'Original pre-insertion corruption controls not executed')
    # Report-only integrity faults: missing primitive, owner alias, changed
    # clearance and omitted exact-high-cut membership must reject.
    def census(items,clearance):
        require(clearance==CLEARANCE,'Altered planning clearance')
        require(len(items)==44 and sum(p['kind']=='via'for p in items)==28,'Missing actual primitive')
        require(sum(p.get('exact_original_via4',False)for p in items)==8,'Missing high-cut identity')
        require(all(p['gain']==p['plan']['gain_native_id']for p in items),'Changed primitive native owner')
    import copy
    faults=[]
    for label,items,clearance in[
        ('missing_actual_primitive',primitives[:-1],CLEARANCE),
        ('changed_clearance',primitives,dict(CLEARANCE,**{'126':1999})),
        ('changed_owner',[dict(p,gain=-1)if i==0 else p for i,p in enumerate(primitives)],CLEARANCE),
        ('omitted_original_high_cut',[dict(p,exact_original_via4=False)for p in primitives],CLEARANCE)]:
        try:census(items,clearance)
        except ValueError:faults.append(label)
        else:raise AssertionError('Accepted survey corruption '+label)
    require(len(faults)==4,'Missing survey fault')
    census(primitives,CLEARANCE)
    result=dict(status='PASS_READ_ONLY_ALL44_NATIVE_CANDIDATE_PRIMITIVES_AND_FINITE_CORRIDOR_SURVEY_NOT_PHYSICAL_ACCEPTANCE',
        original_generator_sha256=GENERATOR_SHA,primitive_count=44,via_count=28,line_count=16,
        exact_original_high_via4_sets=8,original_preinsertion_controls=ctx['controls'],survey_controls=faults,
        actual_inventory=inventory,finite_corridors=corridors,
        problematic_primitives=[x['id']for x in inventory if not x['planning_clear']],
        original_material_hierarchy_labels_unchanged=True,protected_input_sha256=ctx['protected'],
        planned_candidate_inserted=False,candidate_gds_written=False,physical_accepted=False,
        drc_accepted=False,lvs_accepted=False,rc_reused=False,resistance_gain_claim=False,electrical_accepted=False,
        planning_clearance_dbu=CLEARANCE,
        native_minwidth_source_parameters={k:v for k,v in params.items()if k.endswith('_a')and(k.startswith('M')or k.startswith('TM'))},
        renderer_prefix_sha256=hashlib.sha256(render.encode()).hexdigest(),
        exact_candidate_call_list_sha256=hashlib.sha256(calls.encode()).hexdigest())
    args.out.mkdir(parents=True)
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
