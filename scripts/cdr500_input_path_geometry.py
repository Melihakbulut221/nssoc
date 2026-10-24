#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual unchanged CDR input conductor ownership and polygon/via paths."""
import json,sys,copy
from pathlib import Path
from collections import defaultdict,deque
import pya
METALS=(8,10,30,50,67,126,134);VIAS=(19,29,49,66,125,133)
def main():
    root=Path(sys.argv[1]);request=json.loads((root/'request.json').read_text());physical=root/'physical'
    L=pya.Layout();L.read(str(physical/'parent/layout/nssoc_cdr_pd500_active_input_v57.gds'));T=L.cell('nssoc_cdr_pd500_active_input_v57');assert L.dbu==.001 and T
    native=pya.LayoutVsSchematic();native.read(str(physical/'parent/physical/lvs_flat/result.lvsdb'));assert sum(1 for _ in native.netlist().circuit_by_name(T.name).each_device())==500
    wire=pya.LayoutToNetlist();wire.read(str(physical/'wire/native05/wires.l2n'));graph=json.loads((physical/'wire/native05/result.json').read_text())
    W=pya.Layout();W.read(str(physical/'wire/native05/wires.gds'));WT=W.top_cell();assert W.dbu==L.dbu
    for m in (*METALS,*VIAS):assert(pya.Region(T.begin_shapes_rec(L.layer(m,0)))^pya.Region(WT.begin_shapes_rec(W.layer(m,0)))).is_empty(),'Actual cleaned wire geometry differs'
    def probe(a):
        point=pya.Point(*a['point_dbu']);n=native.probe_net(native.layer_by_index(graph['native_layer_mapping'][str(a['metal'])]),point);w=wire.probe_net(wire.layer_by_name('gds_'+str(a['metal'])),point)
        assert n is not None and n.cluster_id==a['native_cluster'];assert w is not None and w.cluster_id==a['wire_component'];return w
    controls=[];first=request['groups'][0]['anchors']['driver']
    for label,bad in [('wrong_native_owner',dict(first,native_cluster=-1)),('wrong_wire_owner',dict(first,wire_component=-1)),('foreign_input_point',dict(first,point_dbu=request['groups'][1]['anchors']['driver']['point_dbu']))]:
        try:probe(bad)
        except AssertionError:controls.append(label)
        else:raise AssertionError('Accepted '+label)
    result=dict(status='RUNNING',geometry_modified=False,controls=controls,groups=[])
    for group in request['groups']:
        nets={role:probe(a)for role,a in group['anchors'].items()};assert len({n.cluster_id for n in nets.values()})==1
        net=next(iter(nets.values()));pieces={m:wire.shapes_of_net(net,wire.layer_by_name('gds_'+str(m)),True).flatten().merged()for m in (*METALS,*VIAS)}
        nodes={};bylayer=defaultdict(list)
        for m in METALS:
            for poly in pieces[m].each():k=len(nodes);nodes[k]=(m,pya.Region(poly),poly);bylayer[m].append(k)
        def hits(m,region):return[k for k in bylayer[m]if not(nodes[k][1]&region).is_empty()]
        edges=defaultdict(set);cuts=defaultdict(list)
        for lo,via,hi in zip(METALS,VIAS,METALS[1:]):
            for poly in pieces[via].each():
                a=hits(lo,pya.Region(poly));b=hits(hi,pya.Region(poly));assert len(a)==len(b)==1,('Unbound physical via',via,str(poly),a,b)
                u,v=a[0],b[0];edges[u].add(v);edges[v].add(u);cuts[tuple(sorted((u,v)))].append(dict(via_layer=via,polygon_dbu=str(poly),bbox_dbu=str(poly.bbox())))
        endpoints={}
        for role,a in group['anchors'].items():
            x,y=a['point_dbu'];found=hits(a['metal'],pya.Region(pya.Box(x-1,y-1,x+1,y+1)));assert len(found)==1;endpoints[role]=found[0]
        owners={}
        for m in (*METALS,*VIAS):
            owners[m,'root_direct']=pya.Region(T.shapes(L.layer(m,0))).merged()
            for inst in T.each_inst():owners[m,inst.cell.name+'@'+str(inst.dcplx_trans)]=pya.Region(inst.cell.begin_shapes_rec(L.layer(m,0))).transformed(inst.cplx_trans).merged()
        def contributors(m,region):
            return[dict(owner=owner,overlap_polygons_dbu=[str(p)for p in (part&region).merged().each()])for(layer,owner),part in owners.items()if layer==m and not(part&region).is_empty()]
        def path(a,b):
            todo=deque([endpoints[a]]);previous={endpoints[a]:None}
            while todo and endpoints[b]not in previous:
                x=todo.popleft()
                for y in sorted(edges[x]):
                    if y not in previous:previous[y]=x;todo.append(y)
            assert endpoints[b]in previous
            ids=[];x=endpoints[b]
            while x is not None:ids.append(x);x=previous[x]
            ids.reverse();return dict(roles=[a,b],metal_pieces=[dict(node=k,metal=nodes[k][0],polygon_dbu=str(nodes[k][2]),contributors=contributors(nodes[k][0],nodes[k][1]))for k in ids],via_links=[dict(nodes=[a,b],cuts=cuts[tuple(sorted((a,b)))])for a,b in zip(ids,ids[1:])],scope='One actual polygon/via connectivity path. This is not an assertion that a reduced resistance edge is a straight wire segment.')
        dominant=[]
        for edge in group['dominant_edges']:
            endpoints_readback=[]
            for endpoint in edge['raw_endpoints']:
                x,y=endpoint['point_dbu'];region=pya.Region(pya.Box(x-3,y-3,x+3,y+3));matches=[]
                for m,part in pieces.items():
                    overlap=(part&region).merged()
                    if not overlap.is_empty():matches.append(dict(gds_layer=m,component_overlap_dbu=[str(p)for p in overlap.each()],owners=contributors(m,overlap)))
                endpoints_readback.append(dict(endpoint,matching_component_materials=matches))
            dominant.append(dict(edge,endpoints_geometry=endpoints_readback,unique_resistor_layer_claim=False))
        result['groups'].append(dict(role_binding=group['role_binding'],anchors=group['anchors'],native_cluster=first['native_cluster']if False else group['anchors']['driver']['native_cluster'],wire_component=net.cluster_id,component_layer_census={str(m):dict(area_dbu2=p.area(),polygons=p.count())for m,p in pieces.items()},paths=[path(a,b)for a,b in [('driver','gain'),('driver','termination'),('gain','termination')]],dominant_resistor_endpoints=dominant))
    assert len(result['groups'])==4 and len(controls)==3
    result.update(status='PASS_ACTUAL_CDR_INPUT_OWNERSHIP_AND_TWELVE_DRAWING_PATHS_NOT_RC_EDGE_LAYER_OR_CIRCUIT_ACCEPTANCE',original_geometry_unchanged=True,selected_native_and_wire_owners_verified=True,full_phy_accepted=False)
    (root/'native-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
