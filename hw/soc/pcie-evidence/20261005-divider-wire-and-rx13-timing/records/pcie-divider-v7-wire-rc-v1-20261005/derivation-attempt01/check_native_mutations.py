# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve meaningful corrupted raw exports and require specific rejection."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import copy,hashlib,importlib.util,json,re,time
import networkx as nx
B=Path(__file__).resolve().parent;P=Path('/dev/shm/nssoc-div4-v7-wire-rc-01')
from unittest.mock import patch
import difflib
spec=importlib.util.spec_from_file_location('strict_wire',B/'audit_wire_rc.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=json.loads((m.GEOMETRY/'anchors.json').read_text());positive=m.audit(P,a);assert positive['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
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
cases=[
 ('dropped_actual_port',{'wires.spice':text.replace(' '+next(n for n in parsed['ports'] if n.startswith('T'))+' ',' ',1)},'Export port loss/duplication'),
 ('dropped_resistor',{'wires.spice':re.sub(r'^R\d+ .*\n','',text,count=1,flags=re.M)},'Native/export resistor topology/value differs'),
 ('wrong_resistor',{'wires.spice':re.sub(r'^(R\d+ \S+ \S+) \S+$',r'\1 12345',text,count=1,flags=re.M)},'Native/export resistor topology/value differs'),
 ('cross_conductor_short',{'wires.spice':text.replace('.ends','R_EXTRA P004 P005 1\n.ends')},'R network has unanchored component or cross-conductor short'),
 ('ground_redistribution_same_matrix',{'wires.spice':'\n'.join(redistributed)+'\n'},'Per-point ground C export changed'),
 ('mutual_anchor_shift_same_matrix',{'wires.spice':'\n'.join(shifted)+'\n'},'Mutual C native attachment changed'),
 ('dropped_cap',{'wires.spice':re.sub(r'^C\d+ .*\n','',text,count=1,flags=re.M)},'Mutual C native attachment changed'),
 ('changed_cap',{'wires.spice':re.sub(r'^(C\d+ \S+ \S+) \S+$',r'\1 1e-12',text,count=1,flags=re.M)},'Mutual C native value changed'),
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
r=dict(status='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS',positive_status=positive['status'],cases=results,seconds=time.monotonic()-start,inputs={str(p):m.pin(p) for p in [Path(__file__),B/'audit_wire_rc.py',m.PRIOR,m.GEOMETRY/'anchors.json',*[P/n for n in ('bank_wires.ext','bank_wires.res.ext','native.log','wires.spice','baseline.spice')]]})
(B/'native-mutations.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['seconds'])
