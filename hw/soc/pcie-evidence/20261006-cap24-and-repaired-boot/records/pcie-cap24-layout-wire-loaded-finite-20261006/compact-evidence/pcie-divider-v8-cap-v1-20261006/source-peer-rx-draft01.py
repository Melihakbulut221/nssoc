# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent read-only source, saved controls and declared geometry audit."""
import ast, hashlib, json, re, xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
F=B/'source-freeze01.json';f=json.loads(F.read_text())
def pin(p):
 p=Path(p)
 with p.open('rb') as q:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(q,'sha256').hexdigest())
assert f['inputs']=={p:pin(p) for p in f['inputs']}
assert f['product_sources']=={p:pin(p) for p in f['product_sources']}
bridges=json.loads((B/'source-bridge01.json').read_text());assert len(bridges)==8
for row in bridges:
 for key in ['before','after']:
  path=Path(row[key]['path']);assert pin(path)=={k:row[key][k] for k in ['bytes','sha256']}
  assert path.read_text()==''.join(op[key] for op in row['opcodes'])
 for op in row['opcodes']:
  if op['tag']=='equal':assert op['before']==op['after']
# No production module or native runtime imported/executed.
def funcs(p):return {n.name:n for n in ast.parse(Path(p).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a=funcs(bridges[1]['before']['path']);b=funcs(bridges[1]['after']['path'])
changed=[k for k in a if ast.dump(a[k],include_attributes=False)!=ast.dump(b[k],include_attributes=False)]
assert changed==['fault_reference','main']
add=B/'source-freeze01-metadata-addendum.json';ad=json.loads(add.read_text())
assert ad['freeze']==pin(F) and ad['product_sources']==f['product_sources']
assert ad['inherited_exact_checker_functions']==[k for k in a if k not in changed]
old=ast.unparse(a['fault_reference']);new=ast.unparse(b['fault_reference'])
assert old.replace('cap_cmim w=20u','cap_cmim w=24u')==new
# Independent SPICE expansion binds all formal/actual nets and native parameters.
def graph(topname,topfile):
 paths=[R/'hw/soc/analog/pcie'/n for n in ['rx_sampler_hbt_v2.spice','clock_div2_hbt.spice','clock_div2_conditioned_hbt_v3.spice',topfile]]
 defs={};cur=None
 for path in paths:
  for line in path.read_text().splitlines():
   v=line.lower().split()
   if not v or v[0].startswith('*'):continue
   if v[0]=='.subckt':assert cur is None and v[1] not in defs;cur=v[1];defs[cur]=(v[2:],[])
   elif v[0]=='.ends':assert v==['.ends',cur];cur=None
   else:assert cur;defs[cur][1].append(v)
  assert cur is None
 out={};models={'npn13g2':4,'rppd':3,'cap_cmim':2}
 def expand(name,prefix,actual,stack):
  assert name not in stack
  formal,rows=defs[name];assert len(formal)==len(actual);bind=dict(zip(formal,actual))
  for row in rows:
   assert row[0].startswith('x');model_index=next(i for i,x in enumerate(row[1:],1) if '=' not in x and (x in defs or x in models));model=row[model_index];nets=[bind.get(n,prefix+'.'+n) for n in row[1:model_index]];ident=prefix+'.'+row[0]
   if model in defs:expand(model,ident,nets,stack+(name,));continue
   assert len(nets)==models[model] and ident not in out
   params=dict(x.split('=') for x in row[model_index+1:]);assert len(params)==len(row[model_index+1:]);out[ident]=dict(model=model,nets=nets,params=params)
 expand(topname,'div',['clkp','clkn','qp','qn','div_avdd','avss','sub'],())
 return out
oldg=graph('nssoc_clock_div4_hbt_v7','clock_div4_hbt_v7.spice');newg=graph('nssoc_clock_div4_hbt_v8','clock_div4_hbt_v8.spice')
assert len(oldg)==len(newg)==73 and Counter(x['model'] for x in newg.values())=={'npn13g2':34,'rppd':33,'cap_cmim':6}
delta={k:dict(before=oldg[k],after=newg[k]) for k in oldg if oldg[k]!=newg[k]};assert set(delta)=={'div.xcp','div.xcn'}
for k in delta:assert newg[k]==dict(oldg[k],params={'w':'24u','l':'24u'}) and oldg[k]['params']=={'w':'20u','l':'20u'}
# Independently verify exact native PDK rectangle count/coordinates without PCell or KLayout.
pdk=Path(f['pdk']);techpath=pdk/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json';tech=json.loads(techpath.read_text())['techParams']
assert tuple(D(str(tech[k]))for k in ['TV1_a','Mim_d','TV1_d','Mim_c','epsilon1'])==tuple(map(D,['.42','.36','.42','.6','.001']))
geometry={}
for width in [20,24]:
 w=D(width);cut=D('.42');gap=D('.84');over=D('.36');enc=D('.42');eps=D('.001');grid=D('.005')
 n=int(((w-2*over+gap)/(cut+gap)+eps).to_integral_value(rounding=ROUND_FLOOR));span=n*(cut+gap)-gap+2*over;off=(((w-span)/2/grid+eps).to_integral_value(rounding=ROUND_FLOOR))*grid
 low=over-enc+off;high=over+off+n*(cut+gap)+enc-gap
 assert n==(15 if width==20 else 19)
 geometry[str(width)]=dict(vias=n*n,MIM=[0,0,width,width],Metal5=list(map(str,[-D('.6'),-D('.6'),w+D('.6'),w+D('.6')])),TopMetal1=list(map(str,[low,low,high,high])),cut_first=str(over+off),cut_last=str(over+off+(n-1)*(cut+gap)))
assert D(36)-D(9)-(D(24)+D('.6'))==D('2.4')
# This is a center-line envelope. Finite escape shape widths remain subject to actual DRC.
xml=B/'source-controls04.xml';cases=list(ET.parse(xml).getroot().iter('testcase'));assert len(cases)==62 and all(not any(c.find(n)is not None for n in ['failure','error','skipped'])for c in cases)
raw=[]
for p in sorted((B/'source-controls04').rglob('*.owned.json')):
 j=json.loads(p.read_text());assert j['elapsed_watchdog_seconds'] is None
 for q in j['processes']:
  assert q['status'] in ['REAPED_NO_LIVE_MEMBERS','FAILURE_REAPED']
  live=Path('/proc')/str(q['pid'])/'stat'
  if live.exists():assert live.read_text().rsplit(')',1)[1].split()[19]!=str(q['start_ticks'])
 raw.append(dict(path=str(p),pin=pin(p),status=j['status']))
assert len(raw)==6
assert not Path(f['layout']).exists() and not Path(f['checks']).exists()
receipt=dict(status='PASS_SOURCE_ONLY_DIVIDER_V8_CAP_V1',findings=[],source_pins=f['product_sources'],launcher=pin(B/'launch01.py'),freeze=pin(F),metadata_addendum=pin(add),method=pin(Path(__file__)),whole_source_forward_inverse_bridges=8,all_frozen_inputs_rehashed=len(f['inputs']),inherited_exact_checker_functions=ad['inherited_exact_checker_functions'],changed_checker_functions=changed,independent_native_source_graph=dict(devices=73,hbt=34,resistor=33,capacitor=6,exact_two_deltas=delta,additional_finite_taps=18),independent_MIM_geometry_predeclared=geometry,source_controls=dict(actual_cases=62,failed=0,skipped=0,xml=pin(xml),lifecycle_records=raw),review_notes=['All six product sources and both launch methods read in full. Only two second-stage MIM dimensions change; remaining circuit graph/bias and native 634 via geometry multiset retained.', 'Metadata incorrectly calling fault_reference unchanged is closed by the additive pinned addendum. Original freeze/source bytes retained.', 'The 2.4um planner value measures conservative intrinsic right edge to next escape center; finite escape widths and fresh full actual DRC are still required. It is not measured design-rule margin.', 'Synthetic new-dimension syntax controls derive from saved native fixture; they do not constitute a new extracted netlist. Actual generation, six geometry controls, original21 native gates and subsequent RC/electrical validation remain mandatory.', 'Retained Layout owners prevent lazy Region storage lifetime loss. Raw GDS independently binds47 power arrays; independent Decimal formula binds two changed MIMs including225/361 Vmim cuts.', 'No reviewed producer, test, PCell, native EDA or simulator was executed. No analog division/timing/PHY completion claim.'])
(B/'source-only-peer01-rx.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(peer=pin(B/'source-only-peer01-rx.json'),status=receipt['status'],inputs=len(f['inputs']),graph_delta=list(delta),geometry=geometry),indent=2))
