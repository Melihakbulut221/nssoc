#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Locate measured native supply wire resistors on the exact captured layout."""
import argparse,hashlib,json,os,re,shlex,subprocess
from collections import Counter,defaultdict
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-supply-geometry'
REQUIRED={'R15966','R13797','R13791','R14027','R12487','R14125'}
def records(text):return [shlex.split(s)for s in text.splitlines()if s.strip()]
def read_points(text):
    rows=records(text)
    assert [r[1:]for r in rows if r[0]=='scale']==[['1000','1','0.5']]
    points={}
    for row in rows:
        if row[0]!='rnode':continue
        assert len(row)==7 and float(row[2])==0 and row[6]=='0'
        # Native extresist type is a placeholder0, NOT a metal layer number.
        value=dict(raw_node=row[1],magic_xy=[int(row[4]),int(row[5])],
            point_dbu=[5*int(row[4]),5*int(row[5])],native_rnode=row)
        assert row[1]not in points
        points[row[1]]=value
    assert points
    return points,rows
def controls():
    text='scale 1000 1 0.5\nrnode "P_avss.n0" 0 3.5 20 30 0\n'
    points,_=read_points(text)
    assert points['P_avss.n0']['point_dbu']==[100,150]
    for bad in [text+text.splitlines()[1]+'\n',text.replace('scale 1000 1 0.5','scale 1000 1 1'),text.replace('20 30 0','20 30 metal1')]:
        try:read_points(bad)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('Malformed/ambiguous native point table accepted')
    return dict(known_coordinate_conversion=True,duplicate_point_rejected=True,changed_scale_rejected=True,
                placeholder_type_never_treated_as_metal=True)
def native():
    import pya
    request=json.loads((OUT/'mapping-request.json').read_text())
    L=pya.Layout();L.read(str(OUT/'capture/source/parent/layout/nssoc_cdr_pd484_localbus_v12.gds'))
    top=L.cell('nssoc_cdr_pd484_localbus_v12');assert top is not None and L.dbu==.001
    wire=pya.LayoutToNetlist();wire.read(str(OUT/'capture/source/wire/native05/wires.l2n'))
    layout=json.loads((OUT/'capture/source/parent/layout/result.json').read_text())
    placements={}
    for tag,p in layout['placements'].items():
        box=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',p['bbox_um'])));assert len(box)==4
        placements[tag]=dict(kind=p['kind'],bbox_um=box)
    assert len(placements)==16
    layers={m:wire.layer_by_name('gds_'+str(m))for m in (8,10,30,50,67,126,134)}
    mapped={}
    for name,row in request['points'].items():
        point=pya.Point(*row['point_dbu']);hits=[]
        for metal,layer in layers.items():
            net=wire.probe_net(layer,point)
            if net is not None:hits.append(dict(metal=metal,wire_component=net.cluster_id))
        um=[v*L.dbu for v in row['point_dbu']]
        inside={tag:dict(**p,relative_to_bbox_lower_left_um=[um[0]-p['bbox_um'][0],um[1]-p['bbox_um'][1]])
                for tag,p in placements.items()if p['bbox_um'][0]<=um[0]<=p['bbox_um'][2]and p['bbox_um'][1]<=um[1]<=p['bbox_um'][3]}
        same=[h for h in hits if h['wire_component']==row['wire_component']]
        mapped[name]=dict(**row,point_um=um,point_metal_probe_hits=hits,
            same_conductor_metal_hits=same,same_conductor_point_found=bool(same),containing_macros=inside)
    result=dict(status='NATIVE_WIRE_POINT_TO_LAYOUT_MAPPING_NOT_ROUTE_POLYGON_OR_EFFECTIVE_R',
        points=mapped,macro_placements=placements,
        unresolved_points=[n for n,x in mapped.items()if not x['same_conductor_point_found']],
        scope='A native resistor node is a representative point, not a full resistor polygon or a uniquely identified routing layer. Layer0 in res.ext is a placeholder. Actual wire L2N probing establishes conductor/layer witnesses at the point; co-located layers and other-net crossings remain explicit.')
    (OUT/'native-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,
        full_phy_accepted=False,no_new_simulation=True)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=controls()
        pp=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-supply-paths-pass-20261019.json').read_text())
        prior=pp['report']
        assert pp['run']==39287266456 and pp['summary_sha256']=='398812061d64066b4114044638d2778c1af21cb33a6df86c5fc6547ac2ca22b0'
        assert prior['sources_unchanged']
        cp=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-mim-composition-pass-20261019.json').read_text())
        composed,composition_proof=reports.restore_report('cdr-parent-avdd-v13-mim-composition',cp['run'],cp['summary_sha256'],cp['parts_sha256'],OUT/'model',['pd484-mim-wire.spice','composition.json'])
        assert composed==cp['report']and composed['sources_unchanged']
        assert prior['model_source']['summary_sha256']==cp['summary_sha256']
        pin=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-mim-parent-capture-pass-20261019.json').read_text())
        assert pin['run']==39275348623 and pin['summary_sha256']=='64e5d22c420f6adb083a44b2599e43ed6d550d68b42735c02a409d2d3a838ddb'
        ap=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-mim-parent-audit-pass-20261019.json').read_text())
        assert composed['audited_source']['summary_sha256']==ap['summary_sha256']
        assert ap['report']['capture_source']['summary_sha256']==pin['summary_sha256']
        names=['wire/anchors08.json','wire/rc03/pump_wires.ext','wire/rc03/pump_wires.res.ext','wire/rc03/wires.spice',
            'source/wire/native05/wires.l2n','source/wire/device-locations01.json','source/wire/native05/result.json',
            'source/parent/layout/nssoc_cdr_pd484_localbus_v12.gds','source/parent/layout/result.json']
        capture,capture_proof=reports.restore_report('cdr-parent-avdd-v13-mim-parent-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'capture',names)
        assert capture==pin['report']and capture['sources_unchanged']
        frozen={str(p):sha(p)for p in [Path(__file__),*[OUT/'capture'/n for n in names],OUT/'model/pd484-mim-wire.spice',OUT/'model/composition.json']}
        r.update(capture_source=capture_proof,composition_source=composition_proof,supply_review_source=dict(run=pp['run'],summary_sha256=pp['summary_sha256']))
        contract=json.loads((OUT/'model/composition.json').read_text())
        points,raw=read_points((OUT/'capture/wire/rc03/pump_wires.res.ext').read_text())
        anchors=json.loads((OUT/'capture/wire/anchors08.json').read_text())
        byanchor={a['label']:a for a in anchors['anchors']};assert len(byanchor)==946
        original=records((OUT/'capture/wire/rc03/pump_wires.ext').read_text())
        ports=[x for x in original if x[0]=='port'];assert len(ports)==946
        for row in original:
            if row[0]=='node' and row[1]not in points:
                assert len(row)>=7
                points[row[1]]=dict(raw_node=row[1],magic_xy=[int(row[4]),int(row[5])],
                    point_dbu=[5*int(row[4]),5*int(row[5])],retained_original_native_node=row)

        for p in ports:
            a=byanchor[p[1]]
            assert p[3:5]==p[5:7]and all(abs(int(x)*5-y)<=2 for x,y in zip(p[3:5],a['point_dbu']))
        raw_edges=Counter((tuple(sorted(row[1:3])),parser.number(row[3]))for row in raw if row[0]=='resist')
        wire_rows=parser.statements((OUT/'capture/wire/rc03/wires.spice').read_text())
        edges={x[0]:dict(raw_nodes=x[1:3],resistance_ohm=float(parser.number(x[3])))for x in wire_rows[1:-1]if x[0].startswith('R')}
        assert len(edges)==16010 and raw_edges==Counter((tuple(sorted(x[1:3])),parser.number(x[3]))for x in wire_rows[1:-1]if x[0].startswith('R'))
        graph=defaultdict(list)
        for edge in edges.values():
            a,b=edge['raw_nodes'];graph[a].append(b);graph[b].append(a)
        owners={}
        for label,a in byanchor.items():
            if label in owners:
                assert owners[label]==a['wire_component'];continue
            owner=a['wire_component'];stack=[label];owners[label]=owner
            while stack:
                node=stack.pop()
                if node in byanchor:assert byanchor[node]['wire_component']==owner
                for other in graph[node]:
                    if other not in owners:owners[other]=owner;stack.append(other)
                    else:assert owners[other]==owner
        assert set(owners)==set(graph) and len(set(owners.values()))==111
        assert set(graph)<=set(points),'Missing raw native node coordinates'
        inverse={v.lower():k for k,v in contract['wire_node_map'].items()}
        assert len(inverse)==len(contract['wire_node_map'])
        selected={}
        for rail,review in prior['rails'].items():
            candidates={}
            for path in review['shortest_paths']:
                for edge in path['resistor_path']:candidates[edge['name']]=edge
            wanted={q['name']for q in sorted(candidates.values(),key=lambda x:-x['resistance_ohm'])[:30]}
            wanted|={q['name']for q in review['unavoidable_wire_bridges'][:16]}
            wanted|=REQUIRED&set(candidates)
            selected[rail]=[]
            for name in sorted(wanted,key=lambda n:-candidates[n]['resistance_ohm']):
                edge=candidates[name];actual=edges[name]
                assert sorted(inverse[n]for n in edge['nodes'])==sorted(actual['raw_nodes'])
                assert abs(actual['resistance_ohm']-edge['resistance_ohm'])<1e-9
                item=dict(name=name,**actual,composed_nodes=edge['nodes'])
                bridge=next((q for q in review['unavoidable_wire_bridges']if q['name']==name),None)
                if bridge:item['disconnected_terminal_count']=bridge['disconnected_terminal_count']
                selected[rail].append(item)
        assert REQUIRED<={e['name']for rows in selected.values()for e in rows}
        wanted_nodes={n for rows in selected.values()for e in rows for n in e['raw_nodes']}
        physical_devices={d['native_id']:d for d in json.loads((OUT/'capture/source/wire/device-locations01.json').read_text())['devices']}
        mapped={}
        for node in sorted(wanted_nodes):
            entry=dict(**points[node],wire_component=owners[node],composed_node=contract['wire_node_map'][node])
            if node in byanchor:
                entry['anchor']=byanchor[node]
                witnesses=[d for d in contract['device_records']if any(t['anchor']==node for t in d['terminals'])]
                entry['native_devices']=[dict(record=d,geometry=physical_devices[d['native_id']])for d in witnesses]
            mapped[node]=entry
        request=dict(points=mapped,rails=selected)
        (OUT/'mapping-request.json').write_text(json.dumps(request,indent=2)+'\n')
        r.update(raw_points=len(points),selected_edges={k:len(v)for k,v in selected.items()},required_edges=sorted(REQUIRED),
            native_resistor_edge_value_multiset_preserved=True,all946port_quantization_checks_pass=True)
        save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with(OUT/'native.log').open('w')as f:code=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r['native_returncode']=code
        if code:print((OUT/'native.log').read_text()[-14000:],flush=True)
        assert code==0
        geometry=json.loads((OUT/'native-geometry.json').read_text())
        r['geometry']=geometry;r['rails']=selected;save()
        required_nodes={n for rows in selected.values()for e in rows if e['name']in REQUIRED for n in e['raw_nodes']}
        assert all(geometry['points'][n]['same_conductor_point_found']for n in required_nodes),'Required supply points not bound to actual wire geometry'
        assert all(sha(Path(p))==h for p,h in frozen.items())
        r.update(status='COMPLETE_MEASURED_SUPPLY_RESISTOR_POINT_LAYOUT_MAPPING_NOT_ELECTRICAL_ACCEPTANCE',
            sources_unchanged=True,protected_inputs=frozen,
            scope='Original failure/model/wire geometry only. Raw resistor identities/values preserved, native coordinate scale checked against946actual anchors, representative points probed against original physical wire components. Neither effective R, branch current, uniquely reconstructed conductor polygon nor new electrical/PEX acceptance.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args()
    if args.native:native()
    else:main()
