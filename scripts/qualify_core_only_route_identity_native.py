#!/usr/bin/env python3
"""Native positive and exact-category fault controls for route identity."""
import os,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load
from audit_core_only_route_identity import snapshot,compare
p=Path(os.environ['NSSOC_ROUTE_IDENTITY_BEFORE']);mode=os.environ['NSSOC_ROUTE_IDENTITY_FAULT']
d0,b0=load(p);d1,b1=load(p)
expected=None
if mode=='power_open':b1.findInst('nssoc_slewiso_0_0').findITerm('VDD').disconnect();expected='terminals'
elif mode=='clock_type':
 n=next(n for n in b1.getNets()if str(n.getSigType())=='CLOCK');n.setSigType('SIGNAL');expected='nets'
elif mode=='signal_rewire':b1.findInst('nssoc_slewiso_0_0').findITerm('A').connect(b1.findInst('nssoc_slewiso_1_0').findITerm('A').getNet());expected='terminals'
elif mode=='instance_move':
 i=b1.findInst('nssoc_slewiso_0_0');i.setPlacementStatus('PLACED');r=i.getBBox();i.setLocation(r.xMin()+1000,r.yMin());expected='instances'
elif mode=='antenna_missing':
 i=next(i for i in b1.getInsts()if str(i.getMaster().getType())=='CORE_ANTENNACELL');odb.dbInst.destroy(i);expected='instances'
elif mode=='port_type':
 t=next(iter(b1.getBTerms()));t.setSigType('GROUND'if str(t.getSigType())!='GROUND'else 'SIGNAL');expected='special_and_ports'
else:assert mode=='positive',mode
try:r=compare(snapshot(b0),snapshot(b1))
except AssertionError as e:
 assert expected is not None and str(e)=='route_identity_changed:'+expected,(mode,repr(e))
 result=dict(mode=mode,rejected=True,category=expected)
else:
 assert mode=='positive',('fault_not_rejected',mode);result=dict(mode=mode,passed=True,audit=r)
Path(os.environ['NSSOC_ROUTE_IDENTITY_CONTROL_RESULT']).write_text(json.dumps(result,indent=2)+'\n')
