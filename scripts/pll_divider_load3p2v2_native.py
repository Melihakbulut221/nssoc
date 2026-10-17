#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read every unsimplified native divider device; preserve terminal identity and finite body."""
import json,os,sys,math
from pathlib import Path
from collections import Counter
from run_cloud_tx_layout_repair import sha
ORDER={'npn13G2':['C','B','E','S'],'rppd':['rppd_1','rppd_2','rppd_sub'],'cap_cmim':['mim_top','mim_btm'],'ptap1':['TIE','WELL']}
PORTS=['CLKP','CLKN','QP','QN','DIV_AVDD','AVSS','SUB']
TOP='nssoc_clock_div4_load3p2_v2_layout'
GDS_SHA='265d5245f5b406aa20c20647afbe9d87ad9e8f1493cfe3cae3fed9d64885a71b'
def export(source,out):
    import pya
    source=Path(source);out=Path(out)
    root=source/'source/wire';gds=root/'source/layout'/(TOP+'.gds');database=root/'raw_flat/result.lvsdb'
    assert sha(gds)==GDS_SHA
    layout=pya.Layout();layout.read(str(gds));top=layout.cell(TOP);assert top is not None and layout.dbu==.001
    native=pya.LayoutVsSchematic();native.read(str(database));c=native.netlist().circuit_by_name(TOP)
    assert c is not None and c.pin_count()==7
    planes=json.loads((source/'anchors03.json').read_text())
    geometry=json.loads((root/'source/layout/result.json').read_text())
    wire=json.loads((root/'native01/result.json').read_text())
    mapping={int(k):v for k,v in wire['native_layer_mapping'].items()}
    names={};probes=[]
    for name in PORTS:
        rect=geometry['ports'][name];assert rect['layer']=='Metal5'
        point=pya.DBox(*rect['rect_um']).to_itype(layout.dbu).center()
        n=native.probe_net(native.layer_by_index(mapping[67]),point);assert n is not None
        key=str(n.cluster_id);assert key not in names;names[key]=name
        pin=next(p for p in c.each_pin()if p.name()==name);assert c.net_for_pin(pin.id()).cluster_id==n.cluster_id
        anchor=next(a for a in planes['anchors']if a['label']=='P_'+name)
        assert anchor['point_dbu']==[point.x,point.y] and str(anchor['native_cluster'])==key
        probes.append(dict(name=name,cluster=key,point_dbu=[point.x,point.y]))
    rows=[];body=set()
    for d in c.each_device():
        cls=d.device_class();assert cls.name in ORDER;terms={}
        for t in cls.terminal_definitions():
            net=d.net_for_terminal(t.id());assert net is not None
            shapes=native.shapes_of_terminal(d.terminal_ref(t.id()));assert shapes
            terms[t.name]=dict(cluster=str(net.cluster_id),native_name=net.name,shapes=[dict(layer=int(i),bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=[str(p)for p in r.each()])for i,r in shapes.items()])
            if (cls.name,t.name)in [('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL')]:body.add(str(net.cluster_id))
        assert set(terms)==set(ORDER[cls.name])
        params={p.name:d.parameter(p.id())for p in cls.parameter_definitions()}
        assert all(math.isfinite(v)for v in params.values())
        rows.append(dict(id=int(d.id()),model=cls.name,parameters=params,terminals=terms))
    assert len(rows)==len({r['id']for r in rows})==91
    assert Counter(r['model']for r in rows)==Counter(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)
    assert len(body)==1 and body.isdisjoint(names);names[next(iter(body))]='BULK'
    used={t['cluster']for r in rows for t in r['terminals'].values()}
    for cluster in sorted(used):
        if cluster not in names:names[cluster]='n_'+cluster
    assert set(names)==used and len(names)==38 and len(set(names.values()))==38
    by_term={(r['device'],r['terminal']):r for r in planes['rows']};assert len(by_term)==283
    count=0
    for r in rows:
        for term,t in r['terminals'].items():
            plane=by_term[(r['id'],term)];assert plane['model']==r['model'] and str(plane['native_cluster'])==t['cluster']
            t['logical_net']=names[t['cluster']]
            assert ('reference_label'not in plane)==(t['logical_net']=='BULK')
            count+=1
    assert count==283
    record=dict(status='EXPORTED_NATIVE_DIVIDER91_AND283_TERMINALS_NOT_ELECTRICAL_ACCEPTANCE',
        gds_sha256=sha(gds),dbu=layout.dbu,modes=dict(lvs_flat=dict(devices=rows,probes=probes,net_map=names,database_sha256=sha(database))))
    (out/'native.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true';export(sys.argv[1],sys.argv[2])
