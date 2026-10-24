#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual failed LVS clusters without accepting or editing the geometry."""
import argparse,json,os,re,subprocess
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-parent-m4-wire-path'
TOP='nssoc_cdr_pd500_active_input_v57'
def native():
    import pya
    from collections import defaultdict,deque
    source=OUT/'source';meta=json.loads((source/'baseline/layout/result.json').read_text())
    L=pya.Layout();L.read(str(source/'rejected-supply-short.gds'));T=L.cell(TOP)
    assert L.dbu==.001 and T is not None
    metals=(8,10,30,50,67,126,134);vias=(19,29,49,66,125,133)
    regions={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).flatten().merged()for m in (*metals,*vias)}
    e=pya.LayoutToNetlist('ACTUAL500_WIRES',L.dbu)
    for m,r in regions.items():
        assert not r.is_empty();e.register(r,'gds_'+str(m));e.connect(r)
    for lo,via,hi in zip(metals,vias,metals[1:]):
        e.connect(regions[lo],regions[via]);e.connect(regions[via],regions[hi])
    e.extract_netlist()
    c=e.netlist().top_circuit();assert not list(c.each_device())
    def point(raw):
        return pya.DBox(*map(float,re.findall(r'-?\d+(?:\.\d+)?',raw))).to_itype(L.dbu).center()
    ports={name:point(meta['ports'][name])for name in ('avss','sub')}
    nets={name:e.probe_net(regions[134],p)for name,p in ports.items()}
    assert all(n is not None for n in nets.values())
    same=nets['avss'].cluster_id==nets['sub'].cluster_id
    result=dict(status='COMPLETE_ACTUAL500_LABEL_FREE_WIRE_PATH_DIAGNOSIS',geometry_edited=False,
        same_physical_wire_component=same,public_wire_clusters={k:n.cluster_id for k,n in nets.items()},
        full_phy_accepted=False,method='Drawing-only seven-metal/six-via native KLayout connectivity; no text/net-label union.')
    if not same:
        result['source_texts']={f'{L.get_info(i).layer}/{L.get_info(i).datatype}':[str(s.text)for s in T.shapes(i).each()if s.is_text()]for i in L.layer_indexes()if any(s.is_text()for s in T.shapes(i).each())}
        result['avss_sub_conductor_regions']={name:{str(m):[str(p)for p in e.shapes_of_net(n,regions[m],True).each()]for m in metals}for name,n in nets.items()}
    else:
        pieces={m:e.shapes_of_net(nets['avss'],regions[m],True).flatten().merged()for m in (*metals,*vias)}
        nodes={};grids={m:defaultdict(set)for m in metals};size=100000
        def tiles(b):
            for x in range(b.left//size,b.right//size+1):
                for y in range(b.bottom//size,b.top//size+1):yield x,y
        for m in metals:
            for poly in pieces[m].each():
                key=len(nodes);nodes[key]=(m,pya.Region(poly),poly)
                for tile in tiles(poly.bbox()):grids[m][tile].add(key)
        def hits(m,r):
            candidates=set()
            for tile in tiles(r.bbox()):candidates.update(grids[m].get(tile,()))
            return [k for k in candidates if not(nodes[k][1]&r).is_empty()]
        graph=defaultdict(set);edge_vias={};unbound=[]
        for lo,via,hi in zip(metals,vias,metals[1:]):
            for poly in pieces[via].each():
                r=pya.Region(poly);a=hits(lo,r);b=hits(hi,r)
                assert len(a)<=1 and len(b)<=1,('One cut touches multiple same-layer components',via,a,b)
                if not a or not b:unbound.append(dict(via=via,box_dbu=str(poly.bbox()),lower=a,upper=b));continue
                u,v=a[0],b[0];graph[u].add(v);graph[v].add(u)
                edge_vias.setdefault(tuple(sorted((u,v))),[]).append(dict(via=via,polygon_dbu=str(poly)))
        endpoints={}
        for name,p in ports.items():
            hit=hits(134,pya.Region(pya.Box(p.x-1,p.y-1,p.x+1,p.y+1)));assert len(hit)==1
            endpoints[name]=hit[0]
        todo=deque([endpoints['avss']]);previous={endpoints['avss']:None}
        while todo and endpoints['sub']not in previous:
            node=todo.popleft()
            for other in sorted(graph[node]):
                if other not in previous:previous[other]=node;todo.append(other)
        assert endpoints['sub']in previous,'Drawing-only native short lacks polygon/via path'
        path=[];node=endpoints['sub']
        while node is not None:path.append(node);node=previous[node]
        path.reverse();owners={}
        for m in set(nodes[k][0]for k in path):
            owners[(m,'root_direct')]=pya.Region(T.shapes(L.layer(m,0))).flatten().merged()
            for inst in T.each_inst():
                owners[(m,inst.cell.name+'@'+str(inst.dcplx_trans))]=pya.Region(inst.cell.begin_shapes_rec(L.layer(m,0))).transformed(inst.cplx_trans).flatten().merged()
        records=[]
        for k in path:
            m,r,poly=nodes[k];contributors=[]
            for (layer,owner),part in owners.items():
                if layer!=m:continue
                overlap=(part&r).merged()
                if not overlap.is_empty():contributors.append(dict(owner=owner,polygons_dbu=[str(p)for p in overlap.each()]))
            records.append(dict(node=k,metal=m,polygon_dbu=str(poly),contributors=contributors))
        result.update(wire_graph_nodes=len(nodes),wire_graph_edges=len(edge_vias),path=records,
            path_edges=[dict(nodes=[a,b],cuts=edge_vias[tuple(sorted((a,b)))])for a,b in zip(path,path[1:])],unbound_vias=unbound)
    e.write(str(OUT/'actual-wires.l2n'))
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','same_physical_wire_component','public_wire_clusters')},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-m4-overlay-supply-rejection-20261024.json').read_text())
        selected=['rejected-supply-short.gds','rejected-supply-short.json','baseline/layout/result.json']
        prior,proof=reports.restore_report('cdr-sampler-active-input-v57-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report']and prior['source_head']==pin['source_head'];r['original_source']=proof
        assert prior['status']=='FAIL_OR_ERROR'and prior['generation_returncode']==1 and 'physical_returncode'not in prior
        failure=json.loads((OUT/'source/rejected-supply-short.json').read_text())
        assert failure['accepted']is False and failure['clusters']['avss']==failure['clusters']['sub']
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with (OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=rc
        if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert rc==0;r['native']=json.loads((OUT/'native.json').read_text())
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_REJECTED_CANDIDATE_ACTUAL500_WIRE_PATH_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
