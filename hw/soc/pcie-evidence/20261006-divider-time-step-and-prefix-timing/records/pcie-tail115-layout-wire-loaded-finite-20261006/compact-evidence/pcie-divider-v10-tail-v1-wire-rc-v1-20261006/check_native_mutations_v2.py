# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve meaningful corrupted raw exports and require specific rejection."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import copy,hashlib,importlib.util,json,re,time
import networkx as nx
B=Path(__file__).resolve().parent;P=Path('/dev/shm/nssoc-div4-v10-tail-v1-wire-rc-01')
from unittest.mock import patch
import difflib
spec=importlib.util.spec_from_file_location('strict_wire',B/'audit_wire_rc.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=json.loads((m.GEOMETRY/'anchors.json').read_text());positive=m.audit(P,a);assert positive['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
text=(P/'wires.spice').read_text();rows=text.splitlines();parsed=m.rawparser.parse_spice(text);graph=nx.Graph();graph.add_edges_from((x,y) for x,y,v in parsed['resistors']);anchor={r['label']:r['wire_component'] for r in a['anchors']};owner={};groups={}
for c in nx.connected_components(graph):
 ids={anchor[n] for n in c if n in anchor};assert len(ids)==1;idx=next(iter(ids));owner.update({n:idx for n in c});groups[idx]=sorted(c)
# Select an actual unique resistor bridge that separates real geometry probes.
# The physical overlay may change export ordering; reject an actual open, not
# merely a missing bookkeeping row. No extraction or geometry is modified.
assert nx.number_connected_components(graph)==37
bridge_edges={frozenset(e) for e in nx.bridges(graph)}
resistor_rows=[(i,line.split()) for i,line in enumerate(rows) if line.startswith('R') and len(line.split())==4]
chosen=None
for i,f in resistor_rows:
 if frozenset(f[1:3]) not in bridge_edges:continue
 if sum(frozenset(g[1:3])==frozenset(f[1:3]) for _,g in resistor_rows)!=1:continue
 trial=graph.copy();trial.remove_edge(f[1],f[2])
 left=set(nx.node_connected_component(trial,f[1]));right=set(nx.node_connected_component(trial,f[2]))
 if not (left&set(anchor) and right&set(anchor)):continue
 assert nx.number_connected_components(trial)==38
 assert {anchor[n] for n in (left|right)&set(anchor)}=={owner[f[1]]}
 chosen=(i,f,left,right);break
assert chosen is not None,'No meaningful actual unique bridge joining real probes'
ri,rf,left,right=chosen
dropped_resistor_rows=rows.copy();del dropped_resistor_rows[ri]
bridge_control=dict(raw_line=rows[ri],endpoints=rf[1:3],physical_component=owner[rf[1]],
 original_components=37,mutated_components=38,
 left_real_probes=sorted(left&set(anchor)),right_real_probes=sorted(right&set(anchor)))
ground=defaultdict(list)
for i,line in enumerate(rows):
 f=line.split()
 if len(f)==4 and f[0].startswith('C') and f[2]=='sub' and Decimal(f[3])>Decimal('1e-17'):ground[owner[f[1]]].append((i,f))
pair=next(v[:2] for v in ground.values() if len(v)>=2);delta=min(Decimal(f[3]) for i,f in pair)/4
redistributed=rows.copy()
for sign,(i,f) in zip((1,-1),pair):redistributed[i]=' '.join([*f[:3],str(Decimal(f[3])+sign*delta)])
shifted=rows.copy()
for i,line in enumerate(rows):
 f=line.split()
 if len(f)==4 and f[0].startswith('C') and f[2]!='sub':
  alternate=next(n for n in groups[owner[f[1]]] if n!=f[1]);shifted[i]=' '.join([f[0],alternate,*f[2:]]);break
assert anchor['P004']!=anchor['P005'],'Actual short control must cross conductors'
ci,cf=next((i,line.split()) for i,line in enumerate(rows) if line.startswith('C') and len(line.split())==4 and line.split()[2]!='sub')
assert owner[cf[1]]!=owner[cf[2]] and Decimal(cf[3])!=Decimal('1e-12')
dropped_cap_rows=rows.copy();del dropped_cap_rows[ci]
changed_cap_rows=rows.copy();changed_cap_rows[ci]=' '.join([*cf[:3],'1e-12'])
cases=[
 ('dropped_actual_port',{'wires.spice':text.replace(' '+next(n for n in parsed['ports'] if n.startswith('T'))+' ',' ',1)},'Export port loss/duplication'),
 ('dropped_resistor',{'wires.spice':'\n'.join(dropped_resistor_rows)+'\n'},'Physical wire R graph open or incomplete'),
 ('wrong_resistor',{'wires.spice':re.sub(r'^(R\d+ \S+ \S+) \S+$',r'\1 12345',text,count=1,flags=re.M)},'Native/export resistor topology/value differs'),
 ('cross_conductor_short',{'wires.spice':text.replace('.ends','R_EXTRA P004 P005 1\n.ends')},'R network has unanchored component or cross-conductor short'),
 ('ground_redistribution_same_matrix',{'wires.spice':'\n'.join(redistributed)+'\n'},'Per-point ground C export changed'),
 ('mutual_anchor_shift_same_matrix',{'wires.spice':'\n'.join(shifted)+'\n'},'Mutual C native attachment changed'),
 ('dropped_cap',{'wires.spice':'\n'.join(dropped_cap_rows)+'\n'},'Mutual C native attachment changed'),
 ('changed_cap',{'wires.spice':'\n'.join(changed_cap_rows)+'\n'},'Mutual C native value changed'),
 ('cap_scale',{'bank_wires.ext':(P/'bank_wires.ext').read_text().replace('scale 1000 1 0.5','scale 1000 2 0.5')},'Source capacitance scale changed'),
 ('missing_native_completion',{'native.log':(P/'native.log').read_text().replace('NSSOC_WIRE_RC_COMPLETE','REMOVED')},'Missing/duplicate native completion')]
results=[];start=time.monotonic()
original_read=Path.read_text
for name,files,wanted in cases:
 def changed_read(path,*args,**kwargs):
  if path.parent==P and path.name in files:return files[path.name]
  return original_read(path,*args,**kwargs)
 with patch.object(Path,'read_text',changed_read):
  try:m.audit(P,a)
  except ValueError as e:observed=str(e)
  else:raise AssertionError('Mutant accepted: '+name)
 assert observed==wanted,(name,observed,wanted)
 results.append(dict(control=name,rejected_by=observed,mutated_outputs={n:dict(sha256=hashlib.sha256(v.encode()).hexdigest(),diff=''.join(difflib.unified_diff(original_read(P/n).splitlines(True),v.splitlines(True)))) for n,v in files.items()}))
for name,fn,wanted in [('changed_body',lambda x:x['unmodeled_body_well_terminals'][0].update(native_net='WRONG'),'Original body/well identities changed'),('missing_body',lambda x:x['unmodeled_body_well_terminals'].pop(),'Body/metal disposition changed'),('wrong_actual_metal_point',lambda x:x['anchors'][0]['point_dbu'].__setitem__(0,0),'Actual metal terminal witness changed')]:
 x=copy.deepcopy(a);fn(x)
 try:m.audit(P,x)
 except ValueError as e:observed=str(e)
 else:raise AssertionError(name)
 assert observed==wanted,(name,observed,wanted);results.append(dict(control=name,rejected_by=observed))
r=dict(status='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS',positive_status=positive['status'],actual_open_control=bridge_control,cases=results,seconds=time.monotonic()-start,inputs={str(p):m.pin(p) for p in [Path(__file__),B/'audit_wire_rc.py',m.PRIOR,m.GEOMETRY/'anchors.json',*[P/n for n in ('bank_wires.ext','bank_wires.res.ext','native.log','wires.spice','baseline.spice')]]})
(B/'native-mutations-v2.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['seconds'])
