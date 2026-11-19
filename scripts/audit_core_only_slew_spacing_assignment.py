import os,json,hashlib
from pathlib import Path
import odb
before=Path(os.environ['NSSOC_NDR_BEFORE']);after=Path(os.environ['NSSOC_NDR_AFTER']);out=Path(os.environ['NSSOC_NDR_REPORT'])
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [before,after]}
def load(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));return d,d.getChip().getBlock()
d,b=load(before);dd,bb=load(after)
selected={'nssoc_sta_n_55164','nssoc_sta_n_55165','nssoc_sta_n_56323','net4410'};rule_name='NSSOC_SLEW_SPACE2'
def assignments(block):
 return {n.getName():n.getNonDefaultRule().getName()if n.getNonDefaultRule()else None for n in block.getNets()}
a=assignments(b);c=assignments(bb);assert set(a)==set(c)and len(a)==103087
assert {k for k in a if a[k]!=c[k]}==selected
for n in selected:
 assert a[n]is None and c[n]==rule_name and str(bb.findNet(n).getSigType())=='SIGNAL'
oldrules={r.getName()for r in b.getNonDefaultRules()};rules={r.getName():r for r in bb.getNonDefaultRules()};assert set(rules)==oldrules|{rule_name} and rule_name not in oldrules
rule=rules[rule_name];layers=[];expected={'Metal2','Metal3','Metal4','Metal5','TopMetal1','TopMetal2'}
for layer in dd.getTech().getLayers():
 if str(layer.getType())!='ROUTING':continue
 r=rule.getLayerRule(layer);assert r and r.getWidth()==layer.getWidth()
 if layer.getName()in expected:
  assert layer.getSpacing()>0 and r.getSpacing()==2*layer.getSpacing()
  layers.append(dict(name=layer.getName(),width=r.getWidth(),default_spacing=layer.getSpacing(),ndr_spacing=r.getSpacing()))
assert {x['name']for x in layers}==expected
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
out.write_text(json.dumps(dict(accepted=False,source_hashes=hashes,sources_unchanged=True,assigned_signal_nets=sorted(selected),other_net_assignments_preserved=True,widths_unchanged=True,layers=layers,scope='Native spacing-rule assignment only; does not prove realized geometric spacing or coupling improvement.'),indent=2)+'\n')
