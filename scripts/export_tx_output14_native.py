#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Export actual unsimplified TX output14 device terminals from both native LVS databases."""
import json,sys,hashlib
from pathlib import Path
from collections import Counter
import pya
TOP='nssoc_tx_cml_layout'
PORTS='INP INN OUTP OUTN AVDD AVSS SUB IREF'.split()
ORDER={'npn13G2':['C','B','E','S'],'rsil':['rsil_1','rsil_2','rsil_sub'],'ptap1':['TIE','WELL']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source,out=map(Path,sys.argv[1:])
L=pya.Layout();L.read(str(source/'layout'/(TOP+'.gds')));top=L.cell(TOP);assert top is not None and L.dbu==.001
metal=pya.Region(top.begin_shapes_rec(L.layer(67,0))).merged()
labels=[s.text for s in top.each_shape(L.layer(67,25))if s.is_text()]
assert len(labels)==8 and {t.string for t in labels}==set(PORTS)
modes={}
for mode in ('lvs','lvs_flat'):
    db=source/('check/'+mode+'/result.lvsdb')
    lvs=pya.LayoutVsSchematic();lvs.read(str(db));c=lvs.netlist().circuit_by_name(TOP)
    assert c is not None and c.pin_count()==8
    layers=[i for i in lvs.layer_indexes()if (lvs.layer_by_index(i)^metal).is_empty()];assert len(layers)==1
    names={};probes=[]
    for text in labels:
        point=text.trans.disp
        net=lvs.probe_net(lvs.layer_by_index(layers[0]),point);assert net is not None
        pin=next(p for p in c.each_pin()if p.name()==text.string)
        assert c.net_for_pin(pin.id()).cluster_id==net.cluster_id
        key=str(net.cluster_id);assert key not in names;names[key]=text.string.lower()
        probes.append(dict(name=text.string.lower(),cluster=key,point_dbu=[point.x,point.y]))
    rows=[]
    for d in c.each_device():
        cls=d.device_class();assert cls.name in ORDER;terms={}
        for t in cls.terminal_definitions():
            net=d.net_for_terminal(t.id());assert net is not None
            shapes=lvs.shapes_of_terminal(d.terminal_ref(t.id()));assert shapes
            terms[t.name]=dict(cluster=str(net.cluster_id),native_name=net.name,
                shapes=[dict(layer=int(i),bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=[str(p)for p in r.each()])for i,r in shapes.items()])
        assert set(terms)==set(ORDER[cls.name])
        rows.append(dict(id=int(d.id()),model=cls.name,parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()},terminals=terms))
    assert Counter(r['model']for r in rows)==dict(npn13G2=4,rsil=2,ptap1=8)
    byname={v:k for k,v in names.items()}
    tails=[r for r in rows if r['model']=='npn13G2'and r['parameters']['Nx']==8 and r['terminals']['B']['cluster']==byname['iref']and r['terminals']['E']['cluster']==byname['avss']]
    assert len(tails)==1
    for term,name in [('C','TAIL'),('S','BULK')]:
        cluster=tails[0]['terminals'][term]['cluster'];assert cluster not in names;names[cluster]=name
    used={t['cluster']for r in rows for t in r['terminals'].values()}
    assert set(names)==used and len(names)==10
    for r in rows:
        for t in r['terminals'].values():t['logical_net']=names[t['cluster']]
    modes[mode]=dict(devices=rows,probes=probes,net_map=names,database_sha256=sha(db))
out.write_text(json.dumps(dict(status='EXPORTED_NATIVE_TX_OUTPUT14_TERMINALS_NOT_RC_ACCEPTANCE',gds_sha256=sha(source/'layout'/(TOP+'.gds')),dbu=L.dbu,modes=modes),indent=2)+'\n')
