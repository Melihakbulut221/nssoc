#!/usr/bin/env python3
"""Compare exact legalized ECO against its newly routed native database."""
import os,json
from pathlib import Path
from buffer_core_only_chip_controls import load,geom,identity,connections
out=Path(os.environ['NSSOC_CONTROL_BUFFER_OUT'])
d0,b0=load(out/'chip-buffered-placed.odb');d1,b1=load(out/'chip-detailedroute.odb')
def insts(b):return {i.getName():(identity(i),str(i.getPlacementStatus()))for i in b.getInsts()}
assert insts(b0)==insts(b1)and connections(b0)==connections(b1)and geom(b0)==geom(b1)
guided={n.getName()for n in b1.getNets()if list(n.getGuides())}
expected={n.getName()for n in b1.getNets()if str(n.getSigType())not in ('POWER','GROUND')and len(list(n.getITerms()))+len(list(n.getBTerms()))>1}
assert expected<=guided
report=dict(instances=len(list(b1.getInsts())),placements_masters_connections_pins_and_power_geometry_unchanged=True,guided_nets=len(guided),multi_terminal_nets=len(expected),unwired=sorted(n.getName()for n in b1.getNets()if n.getName()in expected and not n.getWire()),accepted=False)
(out/'route-identity.json').write_text(json.dumps(report,indent=2)+'\n')
