# SPDX-License-Identifier: Apache-2.0
"""Independent full-instance/pin inventory before and after native sizing."""
import odb,pathlib,json,hashlib
P=pathlib.Path
def snapshot(path):
 db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock()
 rows={i.getName():{'master':i.getMaster().getName(),'location':list(i.getLocation()),'orientation':str(i.getOrient()),'status':str(i.getPlacementStatus()),'pins':sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms())} for i in block.getInsts()}
 nets=sorted((n.getName(),str(n.getSigType()),sorted((t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()),sorted(t.getName() for t in n.getBTerms())) for n in block.getNets())
 ports=sorted((p.getName(),str(p.getIoType()),str(p.getSigType()),p.getNet().getName() if p.getNet() else None) for p in block.getBTerms())
 return rows,hashlib.sha256(json.dumps(nets).encode()).hexdigest(),ports
before,bnet,bports=snapshot('out/native/source.odb');after,anet,aports=snapshot('out/native/buf4-legalized-unrouted.odb')
assert len(before)==159934 and before.keys()==after.keys() and bnet==anet and bports==aports
assert before['place31551']['master']=='sg13g2_buf_1' and after['place31551']['master']=='sg13g2_buf_4'
for name in before:
 a=dict(before[name]);b=dict(after[name])
 if name=='place31551':
  del a['master'];del b['master'];del a['location'];del b['location']
 assert a==b,('Unexpected native change',name)
r={'invariants_passed':True,'instances':len(before),'unchanged_other_instances':len(before)-1,'connectivity_sha256':bnet,'top_ports':len(bports),'before_target':before['place31551'],'after_target':after['place31551'],'route_validated':False,'timing_validated':False,'manufacturing_approval':False}
P('out/derived/native-proof.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
