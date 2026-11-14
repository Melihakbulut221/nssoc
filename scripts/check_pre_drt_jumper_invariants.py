# SPDX-License-Identifier: Apache-2.0
"""Independent native whole-chip invariants for guide-only antenna repair."""
import pathlib,json,hashlib,odb
P=pathlib.Path;matches=list(P('hw/soc/out/impl-probe/route').glob('*/before-jumpers.odb'));assert len(matches)==1;root=matches[0].parent

def snapshot(path):
 db=odb.dbDatabase.create();odb.read_db(db,str(path));b=db.getChip().getBlock()
 cells={i.getName():(i.getMaster().getName(),list(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus()),sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms())) for i in b.getInsts()}
 nets=sorted((n.getName(),str(n.getSigType()),sorted((t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()),sorted(p.getName() for p in n.getBTerms())) for n in b.getNets())
 ports=sorted((p.getName(),str(p.getIoType()),str(p.getSigType()),p.getNet().getName() if p.getNet() else None) for p in b.getBTerms())
 return cells,hashlib.sha256(json.dumps(nets).encode()).hexdigest(),ports
before,bnet,bports=snapshot(root/'before-jumpers.odb');after,anet,aports=snapshot(root/'after-jumpers.odb')
assert before==after and bnet==anet and bports==aports
assert len(before)==159934 and len(bports)==354
# Compare per-net guide geometry, independent of write order.
def guides(path):
 result={};net=None;inside=False
 for line in path.read_text().splitlines():
  line=line.strip()
  if not line:continue
  if line=='(':
   assert net is not None and not inside;inside=True;continue
  if line==')':assert inside;inside=False;net=None;continue
  if inside:result[net].append(line)
  else:assert net is None and line not in result;net=line;result[net]=[]
 assert not inside and net is None
 return {n:sorted(v) for n,v in result.items()}
a=guides(root/'before-jumpers.guide');b=guides(root/'after-jumpers.guide');assert a.keys()==b.keys()
changed=[n for n in a if a[n]!=b[n]]
r={'invariants_passed':True,'instances':len(before),'top_ports':len(bports),'connectivity_sha256':bnet,'all_instance_geometry_and_status_unchanged':True,'changed_guide_net_count':len(changed),'guide_net_count':len(a),'accepted_as_routed':False,'manufacturing_approval':False}
(root/'jumper-connectivity-proof.json').write_text(json.dumps(r,indent=2));assert changed,'No actual guide geometry changed';print(json.dumps(r))
