#!/usr/bin/env python3
"""Restrict estimated placement repair to measured pad input violations."""
import os,json,re
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PAD_REPAIR_OUT']);d=odb.dbDatabase.create();odb.read_db(d,str(out/'chip-detailedroute.odb'));b=d.getChip().getBlock()
parts=re.split(r'(?m)^(max slew|max capacitance|max fanout)\s*$',(out/'slow-violations.rpt').read_text())
pins=set()
for i in range(1,len(parts)-1,2):
 if parts[i]not in ('max slew','max capacitance'):continue
 for line in parts[i+1].splitlines():
  if '(VIOLATED)'not in line:continue
  pin=line.split()[0]
  if pin.endswith('/p2c')or not pin.startswith('u_pad_'):pins.add(pin)
assert pins
targets={}
for pin in sorted(pins):
 inst,port=pin.rsplit('/',1);i=b.findInst(inst);assert i;term=i.findITerm(port);assert term and term.getNet();net=term.getNet()
 drivers=[t for t in net.getITerms()if str(t.getIoType())=='OUTPUT'];assert len(drivers)==1
 driver=drivers[0];assert driver.getMTerm().getName()=='p2c'and driver.getInst().getMaster().getName().startswith('sg13g2_IOPad')
 assert driver.getInst().getName()not in ('u_pad_clk_i','u_pad_test_clk'),'Clock repair not authorized in this candidate'
 targets.setdefault(net.getName(),dict(driver=driver.getInst().getName()+'/p2c',violating_pins=[]))['violating_pins'].append(pin)
assert len(targets)>=18
flags={n.getName():n.isDoNotTouch()for n in b.getNets()}
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
# Protect signal topology, while allowing native global-connect to power new cells.
for n in b.getNets():
 n.setDoNotTouch(n.getName()not in targets and str(n.getSigType())not in ('POWER','GROUND'))
for i in b.getInsts():
 if str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
odb.write_db(d,str(out/'repair-input.odb'))
(out/'repair-selection.json').write_text(json.dumps(dict(targets=targets,original_net_flags=flags,original_placement_statuses=statuses,estimated_model_for_candidate_only=True,accepted=False),indent=2)+'\n')
