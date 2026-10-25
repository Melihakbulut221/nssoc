# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source expansion and preserved-code peer; no native simulation."""
from pathlib import Path
import hashlib,json,sys,types
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_feedback_bias_v2 as m

def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
freeze=json.loads((B/'source-freeze.json').read_text())
assert freeze=={p:pin(R/p) for p in freeze}
assert pin(m.previous.__file__)['sha256']==m.PREVIOUS_SHA
bridges=[]
for old,(new,edits) in m.BRIDGES.items():
 assert pin(m.ANALOG/old)['sha256']==m.SOURCE_PINS[old]
 text=new.read_text()
 for a,z,count in reversed(edits):assert text.count(z)==count;text=text.replace(z,a)
 assert text==(m.ANALOG/old).read_text()
 bridges.append({'source':str(m.ANALOG/old),'source_pin':pin(m.ANALOG/old),'new':str(new),'new_pin':pin(new),'inverse_byte_exact':True})
# This peer process uses the exact public byte-identical physical fixtures only.
old_hybrid=m.core.HYBRID;m.core.HYBRID=R/'sw/tests/fixtures/pcie_vco_v6_feedback_v1'
for name,digest in m.core.PINS.items():assert pin(m.core.HYBRID/name)['sha256']==digest
composition=json.loads((m.core.HYBRID/'composition.json').read_text())

def independently_expand(texts,config):
 definitions={}
 for name,text in texts.items():
  if name=='hybrid-open.spice':continue
  current=None
  for line in text.lower().splitlines():
   w=line.split()
   if not w or w[0].startswith('*'):continue
   if w[0]=='.subckt':assert current is None and w[1] not in definitions;current=w[1];definitions[current]=(w[2:],[])
   elif w[0]=='.ends':assert current is not None;current=None
   else:assert current is not None;definitions[current][1].append(w)
  assert current is None
 result={}
 widths={'npn13g2':4,'rppd':3,'cap_cmim':2,'sg13_hv_pmos':4,'sg13_hv_nmos':4,'sg13_lv_pmos':4,'sg13_lv_nmos':4}
 def visit(model,path,nets,stack=()):
  assert model not in stack
  if model=='nssoc_vco_local_hybrid_open_v2':
   mapping=dict(zip([x.lower() for x in composition['ports']],nets));assert len(mapping)==len(nets)
   for item in composition['records']:
    w=item['line'].lower().split();n=len(item['terminals']);key=path+'.'+w[0];assert key not in result
    result[key]={'path':key,'model':w[n+1],'nets':[mapping.get(n,path+'.'+n) for n in w[1:n+1]],'params':dict(x.split('=') for x in w[n+2:])}
   return
  ports,body=definitions[model];assert len(ports)==len(nets);mapping=dict(zip(ports,nets));local=lambda n:mapping.get(n,path+'.'+n)
  for w in body:
   assert w[0].startswith('x');key=path+'.'+w[0]
   if w[-1] in definitions or w[-1]=='nssoc_vco_local_hybrid_open_v2':visit(w[-1],key,[local(n) for n in w[1:-1]],stack+(model,));continue
   known=[(device,n) for device,n in widths.items() if len(w)>n+1 and w[n+1]==device];assert len(known)==1,(path,w)
   device,n=known[0];assert key not in result;result[key]={'path':key,'model':device,'nets':[local(n) for n in w[1:n+1]],'params':dict(x.split('=') for x in w[n+2:])}
 for model,name,ports in config['roots']:visit(model,name,ports)
 return result

cases=[]
for voltage,fault in [(0.6,''),(0.85,''),(0.6,'disconnect_divider_clock'),(0.6,'wrong_feedback_modulus')]:
 before_c,before_rows,before_texts=m.previous.config(voltage,fault)
 c,rows,texts=m.config(voltage,fault)
 old=independently_expand(before_texts,before_c);new=independently_expand(texts,c)
 assert old=={r['path']:r for r in before_rows};assert new=={r['path']:r for r in rows};assert len(new)==437 and set(old)==set(new)
 changes=[p for p in new if new[p]!=old[p]];assert set(changes)=={'xchain.xdiv.xfirst.xup','xchain.xdiv.xfirst.xun'}
 for p in changes:assert old[p]['params']['l']=='6.4u';assert new[p]==dict(old[p],params=dict(old[p]['params'],l='4u'))
 assert all(x['model']=='rppd' for p,x in new.items() if p in changes)
 assert sum(p.startswith('xchain.xosc.') for p in new)==62
 assert sum(v['model']=='npn13g2' for v in new.values())==64
 assert sum(v['model'] in ['ptap1','ntap1'] for v in new.values())==13
 hybrid=texts['hybrid-open.spice'];assert hybrid==before_texts['hybrid-open.spice']
 assert sum(l.startswith('R') for l in hybrid.splitlines())==889 and sum(l.startswith('C') for l in hybrid.splitlines())==765
 vectors=m.core.n.vectors(rows,c['extra_vectors']);assert vectors==m.core.n.vectors(before_rows,before_c['extra_vectors']) and len(vectors)==785
 deck=m._scope['deck'](c,rows,texts);assert deck.count('alter @q.')==64 and deck.count('NSSOC_NATIVE_FLAG_BEGIN ')==64
 for key in ['fixture','window_s','step_s','stop_s','minimum_states','vctrl','fault','extra_vectors']:assert c[key]==before_c[key]
 assert 'CLOAD_CLKP clkp 0 50f' in c['fixture'] and 'CLOAD_CLKN clkn 0 50f' in c['fixture']
 assert not any(line.lstrip().upper().startswith(('BFAKE','VCLK')) for text in texts.values() for line in text.splitlines())
 if fault=='disconnect_divider_clock':assert 'XDIV clkp clkp qp qn' in texts[m.CHAIN.name] and 'v(clkn)' in c['extra_vectors']
 if fault=='wrong_feedback_modulus':assert 'XD2N q2b q1 q1 d2b' in texts[m.core.old.counter.CIRCUIT.name]
 cases.append({'vctrl':voltage,'fault':fault,'identities':len(new),'independent_physical_deltas':changes,'observation_vectors':len(vectors),'native_OFF_alter_and_readback_flags':64,'physical_wire_counts':[889,765]})
cloned=[]
for name,value in m.previous._scope.items():
 if isinstance(value,types.FunctionType) and value.__globals__ is m.previous._scope and name!='config':
  current=m._scope[name];assert current.__code__ is value.__code__ and current.__defaults__==value.__defaults__ and current.__closure__==value.__closure__;assert current.__globals__ is m._scope;cloned.append(name)
assert m.previous.run.__globals__ is m.previous._scope and m.previous._scope['config'] is m.previous.config and m.previous._scope['SOURCE'] is not m.CHAIN
assert m._scope['Meter'] is m.previous._scope['Meter'] and m._scope['OWN_LIMIT']==80*1024**2 and m._scope['FLOOR']==512*1024**2
m.core.HYBRID=old_hybrid
assert freeze=={p:pin(R/p) for p in freeze}
record={'status':'PASS_BIASV2_TWO_PHYSICAL_PULLUP_LENGTHS_SOURCE_ONLY_PEER','source_freeze':{'path':str(B/'source-freeze.json'),**pin(B/'source-freeze.json')},'files_rehashed':freeze,'inverse_bridges':bridges,'independent_expansion':'Separate recursive parser in source_peer_review.py traversed actual top SPICE port bindings plus all62 pinned physical VCO composition records, compared all437 identities and every terminal/model/parameter against generated graphs in4configs.','cases':cases,'inherited_private_function_code_defaults_closures_identical':cloned,'private_globals_predecessor_unchanged':True,'saved_controls':{'path':str(B/'source-controls01.log'),**pin(B/'source-controls01.log'),'passed':11,'rerun':False},'peer_method':{'path':str(Path(__file__).resolve()),**pin(Path(__file__))},'issues_found':[],'native_executed':False,'scope':'Only L6.4→4um on2 rppd records. Existing safety/lifecycle/measurement, 437device screens and64OFF observations unchanged; no simulation result, improvement, PVT, PLLlock, physicaldivider or mainchip acceptance inferred.'}
p=B/'source-only-peer.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'path':str(p),**pin(p)}))
