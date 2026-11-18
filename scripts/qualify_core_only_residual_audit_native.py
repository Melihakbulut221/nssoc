#!/usr/bin/env python3
"""Run a real native OpenDB fault then require the strengthened audit to reject it."""
import os,json,runpy
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);mode=os.environ['NSSOC_FAULT_MODE']
d,b=load(out/'eco-legalized.odb')
if mode=='new_clock_type':b.findNet('nssoc_residualbuf_0_0_net').setSigType('SIGNAL')
elif mode=='source_clock_type':b.findNet('clknet_6_31_0_clk_npu').setSigType('SIGNAL')
elif mode=='missing_antenna':odb.dbInst.destroy(b.findInst('ANTENNA_947'))
elif mode=='buffer_power_open':b.findInst('nssoc_residualbuf_0_0').findITerm('VDD').disconnect()
elif mode=='unrelated_orientation':
 i=b.findInst('nssoc_sta_i_2520');status=str(i.getPlacementStatus());i.setPlacementStatus('PLACED');i.setOrient('MY' if str(i.getOrient())!='MY' else 'R0');i.setPlacementStatus(status)
elif mode=='resized_illegal_rotation':
 i=b.findInst('nssoc_sta_i_8532');i.setOrient('R90')
elif mode=='clock_sink_crossbranch':b.findInst('clkload1085').findITerm('A').connect(b.findNet('nssoc_residualbuf_0_1_net'))
else:assert mode=='positive',mode
odb.write_db(d,str(out/'eco-legalized.odb'))
try:
 runpy.run_path(os.environ['NSSOC_AUDIT_SCRIPT'],run_name='__main__')
except AssertionError as e:
 assert mode!='positive',('positive_rejected',repr(e))
 result=dict(mode=mode,rejected=True,assertion=str(e))
else:
 assert mode=='positive',('fault_was_not_rejected',mode)
 result=dict(mode=mode,passed=True,audit=json.loads((out/'eco-audit.json').read_text()))
(out/'control-result.json').write_text(json.dumps(result,indent=2)+'\n')
