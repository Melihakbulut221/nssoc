# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve meaningful corrupted raw exports and require specific rejection."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import copy,hashlib,importlib.util,json,re,time
import networkx as nx
B=Path(__file__).resolve().parent;P=B/'rc01'
from unittest.mock import patch
import difflib
spec=importlib.util.spec_from_file_location('strict_wire',B/'audit-rc02.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=json.loads((B/'anchors03.json').read_text());positive=m.audit(P,a);assert positive['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
text=(P/'wires.spice').read_text();rows=text.splitlines();parsed=m.rawparser.parse_spice(text);graph=nx.Graph();graph.add_edges_from((x,y) for x,y,v in parsed['resistors']);anchor={r['label']:r['wire_component'] for r in a['anchors']};owner={};groups={}
for c in nx.connected_components(graph):
 ids={anchor[n] for n in c if n in anchor};assert len(ids)==1;idx=next(iter(ids));owner.update({n:idx for n in c});groups[idx]=sorted(c)
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
# Select one real R whose deletion preserves every connected component.
resistor_rows=[(i,line.split()) for i,line in enumerate(rows) if re.fullmatch(r'R\d+ \S+ \S+ \S+',line)]
assert len(resistor_rows)==len(parsed['resistors'])
from collections import Counter
edge_counts=Counter(frozenset((f[1],f[2])) for i,f in resistor_rows)
bridges={frozenset(e) for e in nx.bridges(graph)}
drop_index,drop_fields=next((i,f) for i,f in resistor_rows if edge_counts[frozenset((f[1],f[2]))]>1 or frozenset((f[1],f[2])) not in bridges)
dropped_rows=rows[:drop_index]+rows[drop_index+1:]
dropped_text='\n'.join(dropped_rows)+'\n'
dropped_parsed=m.rawparser.parse_spice(dropped_text)
assert len(dropped_parsed['resistors'])==len(parsed['resistors'])-1
kept_graph=nx.Graph();kept_graph.add_edges_from((x,y) for x,y,v in dropped_parsed['resistors'])
assert set(kept_graph)==set(graph)
assert {frozenset(c) for c in nx.connected_components(kept_graph)}=={frozenset(c) for c in nx.connected_components(graph)}
cases=[
 ('dropped_actual_port',{'wires.spice':text.replace(' '+next(n for n in parsed['ports'] if n.startswith('A'))+' ',' ',1)},'Export port loss/duplication'),
 ('dropped_resistor',{'wires.spice':dropped_text},'Native/export resistor topology/value differs'),
 ('wrong_resistor',{'wires.spice':re.sub(r'^(R\d+ \S+ \S+) \S+$',r'\1 12345',text,count=1,flags=re.M)},'Native/export resistor topology/value differs'),
 ('cross_conductor_short',{'wires.spice':text.replace('.ends','R_EXTRA P_d0p0 P_d0n0 1\n.ends')},'R network has unanchored component or cross-conductor short'),
 ('ground_redistribution_same_matrix',{'wires.spice':'\n'.join(redistributed)+'\n'},'Per-point ground C export changed'),
 ('mutual_anchor_shift_same_matrix',{'wires.spice':'\n'.join(shifted)+'\n'},'Mutual C native attachment changed'),
 ('dropped_cap',{'wires.spice':re.sub(r'^C\d+ .*\n','',text,count=1,flags=re.M)},'Mutual C native attachment changed'),
 ('changed_cap',{'wires.spice':re.sub(r'^(C\d+ \S+ \S+) \S+$',r'\1 1e-12',text,count=1,flags=re.M)},'Mutual C native value changed'),
 ('cap_scale',{'full_tx_output8088_power128return64_wires.ext':(P/'full_tx_output8088_power128return64_wires.ext').read_text().replace('scale 1000 1 0.5','scale 1000 2 0.5')},'Source capacitance scale changed'),
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
for name,fn,wanted in [('changed_body',lambda x:next(r for r in x['rows'] if r['disposition']=='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R').update(native_net='WRONG'),'Original body/well identities changed'),('missing_body',lambda x:x['dispositions'].__setitem__('RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R',8073),'Body/metal disposition changed'),('wrong_actual_metal_point',lambda x:x['anchors'][0]['point_dbu'].__setitem__(0,0),'Actual metal terminal witness changed')]:
 x=copy.deepcopy(a);fn(x)
 try:m.audit(P,x)
 except ValueError as e:observed=str(e)
 else:raise AssertionError(name)
 assert observed==wanted,(name,observed,wanted);results.append(dict(control=name,rejected_by=observed))
r=dict(status='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS',positive_status=positive['status'],cases=results,seconds=time.monotonic()-start,inputs={str(p):m.pin(p) for p in [Path(__file__),B/'audit-rc02.py',m.PRIOR,B/'anchors03.json',*[P/n for n in ('full_tx_output8088_power128return64_wires.ext','full_tx_output8088_power128return64_wires.res.ext','native.log','wires.spice','baseline.spice')]]})
(B/'native-mutations01.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['seconds'])
