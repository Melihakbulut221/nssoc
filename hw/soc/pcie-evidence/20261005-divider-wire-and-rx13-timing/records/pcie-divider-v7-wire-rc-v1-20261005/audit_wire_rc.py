# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit distributed wire graph without using intrinsic aliases to hide opens."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,importlib.util,json,math,re,shlex,sys
import networkx as nx
B=Path(__file__).resolve().parent
GEOMETRY=B.parent/'pcie-divider-v7-wire-v5-20261005'
PRIOR=B.parent/'pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'
spec=importlib.util.spec_from_file_location('frozen_raw_parser',PRIOR);rawparser=importlib.util.module_from_spec(spec);spec.loader.exec_module(rawparser)

def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def require(v,m):
 if not v:raise ValueError(m)
def read(p):return [shlex.split(s) for s in Path(p).read_text().splitlines() if s.strip()]
def close(a,b):return math.isclose(a,b,rel_tol=3e-6,abs_tol=1e-4)
def edge(a,b):return tuple(sorted((a,b)))
def audit(p,anchors):
 p=Path(p);a={r['label']:r for r in anchors['anchors']};require(len(a)==205,'Missing/duplicate geometry probes')
 require(anchors['actual_metal_terminals']==198 and anchors['body_well_terminals']==85 and len(anchors['unmodeled_body_well_terminals'])==85,'Body/metal disposition changed')
 parent=GEOMETRY/'terminal-reference-planes.json'
 require(pin(parent)==anchors['inputs'][str(parent)],'Frozen terminal witness changed')
 native_rows=json.loads(parent.read_text())['rows']
 require(anchors['unmodeled_body_well_terminals']==[r for r in native_rows if r['disposition']!='ACTUAL_METAL_POINT_REFERENCE'],'Original body/well identities changed')
 for i,r in enumerate(native_rows):
  if r['disposition']=='ACTUAL_METAL_POINT_REFERENCE':
   n=a.get(f'T{i:04d}')
   require(n is not None and n['detail']==r and n['point_dbu']==r['point_dbu'] and n['wire_component']==r['wire_component'],'Actual metal terminal witness changed')
 rows=read(p/'bank_wires.ext');rep=read(p/'bank_wires.res.ext');log=(p/'native.log').read_text()
 require([r[1:] for r in rows if r[0]=='scale']==[['1000','1','0.5']],'Source capacitance scale changed')
 require([r[1:] for r in rep if r[0]=='scale']==[['1000','1','0.5']],'Replacement scale changed')
 require([r[1:] for r in rows if r[0]=='style']==[['ngspice()']],'Wrong native extraction style')
 require(not re.search(r'Missing (?:gate|substrate|terminal|source|drain)|Orphaned node|Error in extracting node|Unknown (?:layer|statement)|Error: Node with no area',log),'Native failure')
 require(re.findall(r'^Total Nets: (\d+)$',log,re.M)==['38'],'Wrong full native node count')
 for key in ('Nets extracted','Nets output'):require(re.findall(r'^'+key+r': (\d+)',log,re.M)==['37'],'Incomplete native wire extraction')
 require(log.count('\nNSSOC_WIRE_RC_COMPLETE\n')==1,'Missing/duplicate native completion')
 ports=[r for r in rows if r[0]=='port'];require(len(ports)==205 and {r[1] for r in ports}==set(a),'Incomplete native port census')
 # Magic internal port coordinates are integer 5 nm units in this exact import.
 coordinate_deltas=[]
 for r in ports:
  anchor=a[r[1]];require(r[3:5]==r[5:7],'Reference point became rectangle')
  xy=[int(v)*5 for v in r[3:5]];delta=[v-w for v,w in zip(xy,anchor['point_dbu'])]
  require(all(abs(d)<=2 for d in delta),'Probe moved beyond native nearest 5 nm quantization')
  coordinate_deltas.append(dict(label=r[1],source_dbu=anchor['point_dbu'],magic_dbu=xy,delta_nm=delta))
 nodes={r[1]:float(r[3]) for r in rows if r[0]=='node'};require(len(nodes)==37,'Wrong wire node count')
 subs=[r for r in rows if r[0]=='substrate'];require(len(subs)==1 and subs[0][1]=='sub!' and float(subs[0][3])==0,'Wire capacitance reference changed')
 # Original aliases validate physical owner correspondence only. They are NEVER
 # edges in the exported resistor graph, where they would conceal broken probes.
 original={n:a[n]['wire_component'] for n in nodes}
 for r in rows:
  if r[0]=='equiv':
   require(r[1] in original and r[2] in a and r[2] not in original,'Unsupported intrinsic alias')
   require(original[r[1]]==a[r[2]]['wire_component'],'Native conductor contradicts geometry')
   original[r[2]]=original[r[1]]
 require(set(original)==set(a) and set(original.values())==set(range(1,38)),'Incomplete physical conductor ownership')
 short_warnings=re.findall(r'^Warning:  Ports "([^"]+)" and "([^"]+)" are electrically shorted\.$',log,re.M)
 require(all(x in a and y in a and original[x]==original[y] for x,y in short_warnings),'Actual unexpected port short warning')
 after=rawparser.parse_spice((p/'wires.spice').read_text());before=rawparser.parse_spice((p/'baseline.spice').read_text())
 require(len(after['ports'])==205 and set(after['ports'])==set(a),'Export port loss/duplication')
 require(not after['devices'] and not before['devices'] and not before['resistors'],'Device insertion into wire-only graph')
 require(len(before['ports'])==37 and all(n in original for n in before['ports']) and {original[n] for n in before['ports']}==set(range(1,38)),'Baseline conductor port set differs')
 graph=nx.Graph();graph.add_nodes_from(a)
 for x,y,value in after['resistors']:
  require(x!=y and value>0,'Invalid distributed resistor')
  graph.add_edge(x,y)
 owners={};comps=[];isolated=[]
 for component in nx.connected_components(graph):
  ids={a[n]['wire_component'] for n in component if n in a}
  require(len(ids)==1,'R network has unanchored component or cross-conductor short')
  owner=next(iter(ids));owners.update({n:owner for n in component})
  comps.append(dict(component=owner,nodes=len(component),probes=sorted(component&set(a))))
  if len(component)==1:isolated+=list(component)
 connected=[c for c in comps if c['nodes']>1]
 require(len(connected)==37 and len({c['component'] for c in connected})==37,'Physical wire R graph open or incomplete')
 native_r=Counter((edge(r[1],r[2]),rawparser.number(r[3])) for r in rep if r[0]=='resist')
 export_r=Counter((edge(x,y),v) for x,y,v in after['resistors'])
 require(native_r==export_r,'Native/export resistor topology/value differs')
 # Capacitance reference is the extractor ground, not an inferred device body.
 owners['sub']=0
 expected=defaultdict(float)
 for n,v in nodes.items():
  require(v>=0 and math.isfinite(v),'Invalid source intrinsic C')
  expected[edge(original[n],0)]+=v
 for r in rows:
  if r[0]=='cap':
   x,y=original[r[1]],original[r[2]];require(x!=y,'Same-conductor native cap')
   value=float(r[3]);require(value>=0 and math.isfinite(value),'Invalid source mutual C');expected[edge(x,y)]+=value
 def collapsed(capacitors,own):
  result=defaultdict(float)
  for x,y,v in capacitors:
   require(x in own and y in own and v>=0,'Unknown capacitor endpoint/value')
   x,y=own[x],own[y];require(x!=y or v==0,'Nonzero within-conductor capacitor')
   if v:result[edge(x,y)]+=float(v)*1e18
  return dict(result)
 baseline=collapsed(before['capacitors'],dict(original,sub=0));actual=collapsed(after['capacitors'],owners)
 expected={k:v for k,v in expected.items() if v}
 require(baseline.keys()==expected.keys() and all(close(v,baseline[k]) for k,v in expected.items()),'Baseline source capacitance differs')
 missing_caps=sorted(expected.keys()-actual.keys());extra_caps=sorted(actual.keys()-expected.keys())
 wrong_caps=[dict(a=k[0],b=k[1],expected=v,actual=actual[k]) for k,v in expected.items() if k in actual and not close(v,actual[k])]
 cap_pass=not (missing_caps or extra_caps or wrong_caps)
 retire=[r for r in rep if r[0] in ('subcap','killnode')];require(len(retire)==37 and {r[1] for r in retire}==set(nodes),'Missing/duplicate original node retirement')
 for r in retire:
  if r[0]=='subcap':require(close(-float(r[2]),nodes[r[1]]),'Wrong retained-node intrinsic C retirement')
 points=defaultdict(float)
 for r in rep:
  if r[0]=='rnode':
   require(r[1] in owners and float(r[2])==0 and float(r[3])>=0,'Invalid native distributed C')
   points[owners[r[1]]]+=float(r[3])
 wrong_ground=[dict(node=n,component=original[n],expected=v,actual=points[original[n]]) for n,v in nodes.items() if not close(v,points[original[n]])]
 markers=re.findall(r'^NSSOC_V2_INTRINSIC_DISTRIBUTION (\S+) total=(\S+) intrinsic=(\S+)$',log,re.M)
 require(len(markers)==37 and {r[0] for r in markers}==set(nodes),'Native unreduced branch census differs')
 wrong_markers=[]
 for n,total,intrinsic in markers:
  owner=original[n];incident=sum(v for (x,y),v in expected.items() if x and y and owner in (x,y))
  if not(close(float(intrinsic),nodes[n]) and close(float(total),nodes[n]+incident)):wrong_markers.append(dict(node=n,intrinsic_expected=nodes[n],intrinsic_actual=float(intrinsic),legacy_expected=nodes[n]+incident,legacy_actual=float(total)))
 # Every individual point-C and mutual attachment is checked in addition
 # to the complete conductor-collapsed matrix; equal totals are not enough.
 native_point=defaultdict(float);export_ground=defaultdict(float);wanted_mutual=defaultdict(float);export_mutual=defaultdict(float)
 for row in rep:
  if row[0]=='rnode':native_point[row[1]]+=float(row[3])
 for row in rows:
  if row[0]=='cap':wanted_mutual[edge(row[1],row[2])]+=float(row[3])
 for x,y,v in after['capacitors']:
  if y=='sub':export_ground[x]+=float(v)*1e18
  elif x=='sub':export_ground[y]+=float(v)*1e18
  else:export_mutual[edge(x,y)]+=float(v)*1e18
 require(set(export_ground)<=set(native_point),'Ground C attached to unknown native point')
 require(all(close(v,export_ground.get(n,0)) for n,v in native_point.items()),'Per-point ground C export changed')
 require(wanted_mutual.keys()==export_mutual.keys(),'Mutual C native attachment changed')
 require(all(close(v,export_mutual[n]) for n,v in wanted_mutual.items()),'Mutual C native value changed')
 result=dict(status='FAIL_EXPORTED_TERMINAL_AND_CAPACITANCE_CONTRACT' if isolated or not cap_pass or wrong_ground or wrong_markers else 'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',
  original_devices=91,public_ports=7,physical_wire_components=37,geometry_probes=205,metal_device_terminals=198,
  unmodeled_body_well_terminals=85,actual_exported_resistors=len(after['resistors']),actual_exported_capacitors=len(after['capacitors']),
  resistor_components=len(comps),connected_wire_components=37,disconnected_probes=[a[n] for n in sorted(isolated)],
  disconnected_by_kind=dict(Counter(a[n]['kind'] for n in isolated)),
  native_export_r_edge_value_multiset_exact=True,geometry_conductor_ownership_exact=True,
  every_native_point_ground_capacitance_preserved=True,every_native_mutual_attachment_and_value_preserved=True,
  collapsed_capacitance_edge_count=len(expected),collapsed_matrix_entries=38**2,
  complete_collapsed_capacitance_conserved=cap_pass,per_conductor_intrinsic_ground_c_conserved=not wrong_ground,
  wrong_native_branch_witnesses=wrong_markers,
  missing_capacitance_edges=[dict(a=x,b=y,source_af=expected[x,y]) for x,y in missing_caps],extra_capacitance_edges=[dict(a=x,b=y,actual_af=actual[x,y]) for x,y in extra_caps],wrong_capacitance_values=wrong_caps,wrong_intrinsic_ground_values=wrong_ground,
  original_retained_node_subtractions=sum(r[0]=='subcap' for r in retire),original_node_deletions=sum(r[0]=='killnode' for r in retire),
  capacitor_ground_reference='sub: extractor reference, not mapped to any intrinsic body or supply',
  original_port_short_warnings=len(short_warnings),all_short_warnings_same_geometry_conductor=True,
  probes_native_grid_delta_nm_counts=dict(Counter(str(r['delta_nm']) for r in coordinate_deltas)),
  no_intrinsic_alias_edges_inserted_in_resistance_graph=True,substrate_r_modeled=False,full_pex_qualified=False,
  point_attachment_or_rf_distribution_qualified=False,
  components=comps,capacitance_edges_af=[dict(a=k[0],b=k[1],source=v,baseline=baseline[k],distributed=actual.get(k)) for k,v in sorted(expected.items())])
 return result
if __name__=='__main__':
 p=Path(sys.argv[1]);anchors=Path(sys.argv[2]);out=Path(sys.argv[3])
 try:r=audit(p,json.loads(anchors.read_text()))
 except ValueError as e:r=dict(status='FAIL_AUDIT',error=str(e),full_pex_qualified=False)
 r['inputs']={str(x):pin(x) for x in [Path(__file__),PRIOR,anchors,*[p/n for n in ['bank_wires.ext','bank_wires.res.ext','native.log','wires.spice','baseline.spice']]]}
 out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r.get('error'),r.get('disconnected_by_kind'))
