# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent literal graph comparison of immutable inputs. No native/model imports."""
from pathlib import Path
import collections,hashlib,json,re
from decimal import Decimal
R=Path.cwd();B=Path(__file__).resolve().parent
P=Path('/dev/shm/nssoc-pll-acquisition-v5-max125-local-01');N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01')
PACKET=R/'hw/soc/out/pcie-pll-local-spool-v1-20261006/launch01/static-composition-for-vco01.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
packet=json.loads(PACKET.read_text());assert pin(PACKET)==dict(bytes=2943,sha256='abc6cfb76f6b99685fe98b86404cb5a1439d0872d617ac554c50d799fdc23dae')
assert all(pin(p)==v for p,v in packet['inputs'].items())
# Only static fields of the active result are consumed. Its changing status/raw
# capture is not a terminal artifact and is never given a whole-file pin.
live=json.loads((P/'result.json').read_text());old={k:live[k]for k in ['config','devices','inputs']};del live
new=json.loads((N/'result.json').read_text());assert pin(N/'result.json')==dict(bytes=426434,sha256='1428ee18fc41a19ff5b5a92c3cce2803f1c2fbbe29ce08c6a8c95c9610cf2ded')
(B/'active-immutable-fields-snapshot01.json').write_text(json.dumps(dict(status='STATIC_FIELDS_ONLY_NOT_ACTIVE_RESULT_STATUS_OR_CAPTURE',native_root=str(P),**old),indent=2)+'\n')
inputs={str(PACKET):pin(PACKET),**packet['inputs'],str(N/'result.json'):pin(N/'result.json')}
def definitions(files):
 result={}
 for p in files:
  inputs[str(p)]=pin(p);active=None
  for line in p.read_text().lower().splitlines():
   w=line.split()
   if not w or w[0].startswith('*'):continue
   if w[0]=='.subckt':
    assert active is None;active=w[1];assert active not in result;result[active]=(w[2:],[])
   elif w[0]=='.ends':assert active;active=None
   else:assert active;result[active][1].append(w)
  assert active is None
 return result
MODELS={'npn13g2':4,'rppd':3,'cap_cmim':2,'sg13_hv_pmos':4,'sg13_hv_nmos':4,'sg13_lv_pmos':4,'sg13_lv_nmos':4,'ptap1':2,'ntap1':2}
def expand(defs,roots):
 rows=[];wires=[]
 def walk(model,path,nets,stack=()):
  assert model not in stack;ports,body=defs[model];assert len(ports)==len(nets);mapping=dict(zip(ports,nets));seen=set()
  def node(x):return mapping.get(x,path+'.'+x)
  for w in body:
   assert w[0]not in seen;seen.add(w[0]);here=path+'.'+w[0]
   if w[0][0]in('r','c'):
    assert len(w)==4;wires.append(dict(path=here,kind=w[0][0],nets=[node(x)for x in w[1:3]],value=w[3]));continue
   assert w[0].startswith('x')
   if w[-1]in defs:walk(w[-1],here,[node(x)for x in w[1:-1]],stack+(model,));continue
   found=[(m,n)for m,n in MODELS.items()if len(w)>n+1 and w[n+1]==m];assert len(found)==1,w
   m,n=found[0];rows.append(dict(path=here,model=m,nets=[node(x)for x in w[1:n+1]],params=dict(x.split('=')for x in w[n+2:])))
 for model,path,nets in roots:walk(model.lower(),path.lower(),[x.lower()for x in nets])
 assert len({x['path']for x in rows})==len(rows);return rows,wires
def includes(root):return [root/x for x in re.findall(r'^\.include "([^"]+)"', (root/'bench.cir').read_text(),re.M)]
old_defs=definitions(includes(P));new_defs=definitions(includes(N));old_rows,old_rc=expand(old_defs,old['config']['roots']);new_rows,new_rc=expand(new_defs,new['config']['roots'])
by=lambda rows:{x['path']:x for x in rows}
assert by(old_rows)==by(old['devices'])and len(old_rows)==539 and not old_rc
assert by(new_rows)==by(new['devices'])and len(new_rows)==455
assert collections.Counter(x['kind']for x in new_rc)=={'r':1271,'c':1414}
def unprefix(row,prefix):
 return dict(path=row['path'].removeprefix(prefix),model=row['model'],nets=[x.removeprefix(prefix)for x in row['nets']],params=row['params'])
a=[unprefix(x,'xloop.')for x in old_rows if x['path'].startswith('xloop.xchain.xfb.')];b=[x for x in new_rows if x['path'].startswith('xchain.xfb.')];assert by(a)==by(b)and len(a)==302
# Compare the logical reference sources before distributed wire-node names.
extra=[R/'hw/soc/analog/pcie/clock_vco_hbt_v6.spice',R/'hw/soc/analog/pcie/clock_div2_conditioned_hbt_v3.spice',R/'hw/soc/analog/pcie/clock_div4_hbt_v10.spice']
refdefs=dict(old_defs)
for k,v in definitions(extra).items():assert k not in refdefs;refdefs[k]=v
ports=['clkp','clkn','vctrl','avdd','0','0']
vo,_=expand(old_defs,[('nssoc_clock_vco_hbt_v4','vco',ports)]);vn,_=expand(refdefs,[('nssoc_clock_vco_hbt_v6','vco',ports)])
ports=['clkp','clkn','qp','qn','dvdd','0','0']
do,_=expand(old_defs,[('nssoc_clock_div4_hbt_v5','div',ports)]);dn,_=expand(refdefs,[('nssoc_clock_div4_hbt_v10','div',ports)])
def delta(a,b):
 a=by(a);b=by(b);assert a.keys()==b.keys();out=[]
 for p in sorted(a):
  assert a[p]['model']==b[p]['model']and a[p]['nets']==b[p]['nets']
  if a[p]['params']!=b[p]['params']:out.append(dict(path=p,model=a[p]['model'],before=a[p]['params'],after=b[p]['params']))
 return out
vd=delta(vo,vn);dd=delta(do,dn);assert len(vd)==6 and len(dd)==7
# Bind each 49/73 reference instance to actual saved physical IDs and model
# dimensions; the complete already-reviewed metal/body joins remain separate.
joinfiles=[R/'hw/soc/out/pcie-vco-v6-local-v1-wire-20261005/source-native-bijection.json',R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1/source-native-bijection.json']
compfiles=[Path('/dev/shm/nssoc-vco-v4-mim-v6-local-v1-hybrid-01/composition.json'),R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1/composition.json']
joined=[]
def unit(x):return Decimal(x.removesuffix('u'))
for label,refs,jp,cp in zip(['vco','div'],[vn,dn],joinfiles,compfiles):
 inputs[str(jp)]=pin(jp);inputs[str(cp)]=pin(cp);j=json.loads(jp.read_text());c=json.loads(cp.read_text());records={x['native_id']:x for x in c['records']};rs=by(refs);seen=set();body=[]
 for x in j['devices']:
  if x['model'].lower()in('ptap1','ntap1'):continue
  source=(label+'.x'+x['source_name'].lower())if label=='vco'else x['source_name'].lower().replace('__','.')
  assert source in rs;seen.add(source);ref=rs[source];model=records[x['native_id']];pars={k.lower():v for k,v in model['simulator_parameters'].items()};assert model['model'].lower()==ref['model']
  for k in ['w','l','nx']:
   if k in ref['params']:assert unit(pars[k])==unit(ref['params'][k]),(source,k,pars,ref)
  actual=by(new_rows)[f'xchain.x{label if label=="div"else"osc"}.xd{x["native_id"]:04d}'];assert actual['params']==pars
  body.append(dict(source=source,native_id=x['native_id'],simulator_path=actual['path'],reference_parameters=ref['params'],actual_parameters=pars))
 assert seen==set(rs);joined+=body
parts=collections.Counter('chain_feedback'if x['path'].startswith('xloop.xchain.xfb.')else'chain_vco'if x['path'].startswith('xloop.xchain.xosc.')else'chain_divider'if x['path'].startswith('xloop.xchain.xdiv.')else'detector'if x['path'].startswith('xloop.xdet.xpfd.')else'charge_pump'if x['path'].startswith('xloop.xdet.xcp.')else'loop_filter'for x in old_rows)
assert parts==dict(chain_feedback=302,chain_vco=49,chain_divider=73,detector=102,charge_pump=10,loop_filter=3)
assert all(pin(p)==v for p,v in inputs.items())
result=dict(status='PASS_READ_ONLY_STATIC_COMPOSITION_RECONCILIATION_NO_NEW_CIRCUIT_OR_NATIVE',method=pin(__file__),inputs=inputs,static_active_fields_snapshot=pin(B/'active-immutable-fields-snapshot01.json'),old_devices=539,new_open_loop_devices=455,old_parts=dict(parts),new_parts=dict(vco=62,divider=91,feedback=302),shared_feedback_devices_bit_exact_after_only_xloop_prefix_removal=302,old_and_new_hbt_counts=[sum(x['model']=='npn13g2'for x in rows)for rows in [old_rows,new_rows]],new_contacts=31,new_wire_elements=dict(collections.Counter(x['kind']for x in new_rc)),vco_logical_parameter_deltas=vd,divider_logical_parameter_deltas=dd,complete_reference_to_actual_native_parameter_joins=joined,hypothetical_combined_devices=455+102+10+3,hypothetical_combined_not_generated=True,fixture_difference=dict(old=old['config']['fixture'],new=new['config']['fixture']),old_native_tran=re.findall(r'^\.tran .*',(P/'bench.cir').read_text(),re.M),new_native_tran=re.findall(r'^\.tran .*',(N/'bench.cir').read_text(),re.M),body_boundaries='Four explicitly separate VCO/divider body-substrate/wire-C-reference ports and finite contacts; grounded by ideal bench sources in N16. No substrate-R or joint-block-route qualification.',findings=[],scope='Exact static source/deck/graph reconciliation only. Active PLL result/capture not pinned or modified; no source/producer imports, simulation, generation, or tests. Existing539 loop remains schematic in its clock chain; N16 physical clock uses native per-block wires/intrinsics plus schematic302 feedback. Counts are model-instance census, not foundry signoff.')
(B/'result01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=pin(B/'result01.json'),parts=dict(parts),vco_deltas=[x['path']for x in vd],divider_deltas=[x['path']for x in dd],hypothetical_devices=result['hypothetical_combined_devices'])))
