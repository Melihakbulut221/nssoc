#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject saved real raw-export and anchor corruptions using unchanged strict audit."""
import copy,difflib,hashlib,importlib.util,json,re,shutil
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import networkx as nx
B=Path(__file__).resolve().parent;P=B/'rc01'
spec=importlib.util.spec_from_file_location('strict_bridge_wire',B/'audit-rc02.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=json.loads((B/'anchors03.json').read_text());positive=m.audit(P,a)
assert positive['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
text=(P/'wires.spice').read_text();rows=text.splitlines();parsed=m.rawparser.parse_spice(text)
graph=nx.Graph();graph.add_edges_from((x,y)for x,y,v in parsed['resistors'])
anchor={r['label']:r['wire_component']for r in a['anchors']};owner={};groups={}
for c in nx.connected_components(graph):
    ids={anchor[n]for n in c if n in anchor};assert len(ids)==1
    idx=next(iter(ids));owner.update({n:idx for n in c});groups[idx]=sorted(c)
ground=defaultdict(list);mutual=[]
for i,line in enumerate(rows):
    f=line.split()
    if len(f)==4 and f[0].startswith('C'):
        assert f[1]!='sub','Expected native emitted capacitor reference order'
        if f[2]=='sub' and Decimal(f[3])>0:ground[owner[f[1]]].append((i,f))
        elif f[2]!='sub' and Decimal(f[3])>0:mutual.append((i,f))
pair=next(v[:2]for v in ground.values()if len(v)>=2)
assert mutual,'Native mutual capacitance is needed for attachment controls'
delta=min(Decimal(f[3])for i,f in pair)/4
redistributed=rows.copy()
for sign,(i,f) in zip((1,-1),pair):
    redistributed[i]=' '.join([*f[:3],str(Decimal(f[3])+sign*delta)])
mi,mf=mutual[0];shifted=rows.copy()
alternate=next(n for n in groups[owner[mf[1]]] if n!=mf[1])
shifted[mi]=' '.join([mf[0],alternate,*mf[2:]])
dropped=rows.copy();del dropped[mi]
changed=rows.copy();changed[mi]=' '.join([*mf[:3],str(Decimal(mf[3])*2)])
cases=[
('dropped_actual_port',{'wires.spice':text.replace(' '+next(n for n in parsed['ports']if n.startswith('A'))+' ',' ',1)},['Export port loss/duplication']),
('dropped_resistor',{'wires.spice':re.sub(r'^R\d+ .*\n','',text,count=1,flags=re.M)},['Native/export resistor topology/value differs','R network has unanchored component or cross-conductor short','Physical wire R graph open or incomplete']),
('wrong_resistor',{'wires.spice':re.sub(r'^(R\d+ \S+ \S+) \S+$',r'\1 12345',text,count=1,flags=re.M)},['Native/export resistor topology/value differs']),
('cross_conductor_short',{'wires.spice':text.replace('.ends','R_EXTRA P_sp P_sn 1\n.ends')},['R network has unanchored component or cross-conductor short']),
('ground_redistribution_same_matrix',{'wires.spice':'\n'.join(redistributed)+'\n'},['Per-point ground C export changed']),
('mutual_anchor_shift_same_matrix',{'wires.spice':'\n'.join(shifted)+'\n'},['Mutual C native attachment changed']),
('dropped_mutual_cap',{'wires.spice':'\n'.join(dropped)+'\n'},['Mutual C native attachment changed']),
('changed_mutual_cap',{'wires.spice':'\n'.join(changed)+'\n'},['Mutual C native value changed']),
('cap_scale',{'clock_bridge_wires.ext':(P/'clock_bridge_wires.ext').read_text().replace('scale 1000 1 0.5','scale 1000 2 0.5')},['Source capacitance scale changed']),
('missing_native_completion',{'native.log':(P/'native.log').read_text().replace('NSSOC_WIRE_RC_COMPLETE','REMOVED')},['Missing/duplicate native completion'])
]
results=[];destination=B/'corruptions';destination.mkdir()
required=['clock_bridge_wires.ext','clock_bridge_wires.res.ext','native.log','wires.spice','baseline.spice']
def reject(name,files,observed_anchors,wanted):
    out=destination/name;out.mkdir()
    for filename in required:shutil.copyfile(P/filename,out/filename)
    changes={}
    for filename,value in files.items():
        original=(P/filename).read_text();assert value!=original,'No-op mutation'
        (out/filename).write_text(value)
        changes[filename]=dict(sha256=hashlib.sha256(value.encode()).hexdigest(),
                              diff=''.join(difflib.unified_diff(original.splitlines(True),value.splitlines(True))))
    (out/'anchors.json').write_text(json.dumps(observed_anchors,indent=2)+'\n')
    try:m.audit(out,observed_anchors)
    except ValueError as error:reason=str(error)
    else:raise AssertionError('Accepted actual raw corruption '+name)
    assert reason in wanted,(name,reason,wanted)
    results.append(dict(control=name,rejected_by=reason,mutated_outputs=changes,anchors_sha256=m.pin(out/'anchors.json')['sha256']))
for name,files,wanted in cases:reject(name,files,copy.deepcopy(a),wanted)
for name,fn,wanted in [
('changed_body',lambda x:next(r for r in x['rows']if r['disposition']=='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R').update(native_cluster=-1),'Original body/well identities changed'),
('missing_body',lambda x:x['dispositions'].__setitem__('RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R',1),'Body/metal disposition changed'),
('wrong_actual_metal_point',lambda x:x['anchors'][0]['point_dbu'].__setitem__(0,x['anchors'][0]['point_dbu'][0]+100),'Actual metal terminal witness changed')]:
    bad=copy.deepcopy(a);fn(bad);assert bad!=a
    reject(name,{},bad,[wanted])
assert len(results)==13
r=dict(status='PASS_REAL_NATIVE_BASELINE_AND13_SAVED_RAW_CORRUPTION_CONTROLS',
       positive_status=positive['status'],cases=results,
       inputs={str(p):m.pin(p)for p in [Path(__file__),B/'audit-rc02.py',m.PRIOR,B/'anchors03.json',*[P/n for n in required]]})
(B/'native-mutations01.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
