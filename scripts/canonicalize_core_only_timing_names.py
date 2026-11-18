#!/usr/bin/env python3
"""Rename only unsafe internal identifiers; prove exact geometry and topology."""
import os,json,re,hashlib,struct
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_CANONICAL_OUT']);spec=json.loads((out/'canonical-input.json').read_text())
def load(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));return d,d.getChip().getBlock()
d,b=load(spec['odb']);assert len(list(b.getInsts()))==104885
im={};nm={}
for index,i in enumerate(sorted(b.getInsts(),key=lambda x:x.getName())):
 old=i.getName()
 if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*',old):
  new='nssoc_sta_i_'+str(index);assert not b.findInst(new);im[old]=new
for index,n in enumerate(sorted(b.getNets(),key=lambda x:x.getName())):
 old=n.getName()
 if not list(n.getBTerms())and str(n.getSigType())not in ('POWER','GROUND')and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*',old):
  new='nssoc_sta_n_'+str(index);assert not b.findNet(new);nm[old]=new
assert im and nm
sdc=Path(spec['sdc']).read_text()
assert not any(n in sdc for n in set(im)|set(nm)),'SDC references a renamed identifier; explicit translation required'
def snapshot(block,inv_i,inv_n):
 def ni(s):return inv_i.get(s,s)
 def nn(s):return inv_n.get(s,s)
 inst=[];terms=[];nets=[]
 for i in block.getInsts():
  bb=i.getBBox();inst.append((ni(i.getName()),i.getMaster().getName(),str(i.getOrient()),str(i.getPlacementStatus()),bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()))
  for t in i.getITerms():terms.append((ni(i.getName()),t.getMTerm().getName(),None if not t.getNet()else nn(t.getNet().getName())))
 for t in block.getBTerms():
  boxes=sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for p in t.getBPins()for x in p.getBoxes());terms.append(('@PORT',t.getName(),None if not t.getNet()else nn(t.getNet().getName()),str(t.getIoType()),boxes))
 for n in block.getNets():
  wire=n.getWire();h=hashlib.sha256()
  if wire:
   for j in range(wire.length()):h.update(struct.pack('<Bi',wire.getOpcode(j),wire.getData(j)))
  # Include every special-wire rectangle/via via stable DB serialization fields.
  sw=[]
  for w in n.getSWires():
   for x in w.getWires():
    if x.isVia():
     v=x.getBlockVia()or x.getTechVia();sw.append(('via',v.getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax()))
    else:sw.append(('metal',x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax()))
  nets.append((nn(n.getName()),str(n.getSigType()),bool(n.isSpecial()),None if not wire else (wire.length(),h.hexdigest()),sorted(sw)))
 def digest(v):return hashlib.sha256(json.dumps(sorted(v),separators=(',',':')).encode()).hexdigest()
 return dict(instances=len(inst),terminals=len(terms),nets=len(nets),instance_geometry_sha256=digest(inst),terminal_connectivity_and_port_geometry_sha256=digest(terms),all_wire_opcodes_and_special_geometry_sha256=digest(nets))
before=snapshot(b,{},{});assert len(set(im.values()))==len(im)and len(set(nm.values()))==len(nm)
for old,new in im.items():assert b.findInst(old).rename(new)
for old,new in nm.items():assert b.findNet(old).rename(new)
inv_i={v:k for k,v in im.items()};inv_n={v:k for k,v in nm.items()}
assert snapshot(b,inv_i,inv_n)==before
odb.write_db(d,str(out/'canonical.odb'));dd,bb=load(out/'canonical.odb');assert snapshot(bb,inv_i,inv_n)==before
(out/'canonical-name-map.json').write_text(json.dumps(dict(instances=im,nets=nm),indent=2)+'\n')
(out/'canonical-proof.json').write_text(json.dumps(dict(renamed_instances=len(im),renamed_nets=len(nm),all_original_geometry_and_connectivity_preserved=True,encoded_routed_wires_unchanged=True,binary_readback_verified=True,original_sdc_unchanged=True,snapshot=before,accepted=False),indent=2)+'\n')
