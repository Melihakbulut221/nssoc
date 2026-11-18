#!/usr/bin/env python3
"""Omit only exact coincident BPin/pad-terminal contacts from global routing."""
import os,json,re,hashlib
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_CONTROL_BUFFER_OUT']);source=out/'chip-buffered-placed.odb'
before=hashlib.sha256(source.read_bytes()).hexdigest();d=odb.dbDatabase.create();odb.read_db(d,str(source));b=d.getChip().getBlock()
def shape(layer,r):return (layer.getName(),r.xMin(),r.yMin(),r.xMax(),r.yMax())
selected=[];omitted=[]
for net in b.getNets():
 assert not net.getWire()
 net.clearGuides()
 if str(net.getSigType())in ('POWER','GROUND'):continue
 its=list(net.getITerms());bts=list(net.getBTerms());assert len(its)+len(bts)>1
 if bts:
  assert len(its)==len(bts)==1
  t=its[0];port=bts[0]
  assert t.getMTerm().getName()=='pad'and t.getInst().getMaster().getName().startswith('sg13g2_IOPad')
  a=sorted(shape(layer,r)for layer,r in t.getGeometries()if layer.getRoutingLevel()>0)
  z=sorted(shape(x.getTechLayer(),x)for pin in port.getBPins()for x in pin.getBoxes()if x.getTechLayer().getRoutingLevel()>0)
  assert a and a==z,dict(net=net.getName(),pad_geometry=a,port_geometry=z)
  omitted.append(dict(net=net.getName(),port=port.getName(),terminal=t.getInst().getName()+'/pad',identical_rectangles=a))
 else:
  name=net.getName();assert re.fullmatch('[A-Za-z0-9_]+',name),'Unexpected Tcl net name'
  selected.append(name)
expected=int(os.environ['NSSOC_EXPECTED_PAD_ROUTE_NETS']);assert expected>1794
assert len(omitted)==76 and len(selected)==expected
assert len(set(selected)|{x['net']for x in omitted})==expected+76
(out/'route-selection.tcl').write_text('set_nets_to_route {'+' '.join(sorted(selected))+'}\n')
odb.write_db(d,str(out/'chip-route-input.odb'))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(out/'route-selection.json').write_text(json.dumps(dict(selected_nets=sorted(selected),coincident_pad_nets=omitted,all_omitted_have_identical_pin_shapes=True,stale_guides_cleared=True,source_unchanged=True,accepted=False,scope='Exact LEF BPin/ITerm metal equality; no hidden pad GDS or ESD claim. Full routed geometry audit still checks every signal net.'),indent=2)+'\n')
