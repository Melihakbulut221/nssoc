#!/usr/bin/env python3
"""Create a bounded buffer-only ECO selected by actual extracted path evidence."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d,b=load(out/'core-routed.odb')
assert len(list(b.getInsts()))==104885
text=(out/'slow-max.rpt').read_text();hold=(out/'fast-min.rpt').read_text()
assert 'slice$71785'in text and 'slice$72130'in text
assert 'u_ram.g_ram_2048x64_ecc.u_b2/A_MEN'in hold and 'slack (VIOLATED)'in hold
# Inspect data-path buffer outputs only; clock buffers and logic cells are excluded.
selected={}
for line in text.splitlines():
 m=re.fullmatch(r'\s*(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+[\^v]\s+(\S+)/X\s+\(sg13g2_buf_1\)\s*',line)
 if not m or float(m[4])<0.45:continue
 name=m[6];assert not any(x in name.lower()for x in ['clkbuf','delaybuf','clock'])
 selected[name]=dict(delay_ns=float(m[4]),slew_ns=float(m[3]),cap_pf=float(m[2]))
assert 5<=len(selected)<=30,('Unexpected measured buffer selection',selected)
new_master=d.findMaster('sg13g2_buf_4');small=d.findMaster('sg13g2_buf_1');assert new_master and small
original_statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
for i in b.getInsts():
 if str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
for name in sorted(selected):
 i=b.findInst(name);assert i and i.getMaster().getName()=='sg13g2_buf_1'
 assert {t.getMTerm().getName()for t in i.getITerms()}=={'A','X','VDD','VSS'}
 assert i.findITerm('A').getNet() and i.findITerm('X').getNet()
 i.swapMaster(new_master);assert i.getMaster().getName()=='sg13g2_buf_4';i.setPlacementStatus('PLACED')
sink=b.findInst('u_ram.g_ram_2048x64_ecc.u_b2').findITerm('A_MEN');net=sink.getNet();assert net.getName()=='net30226'
drivers=[t for t in net.getITerms()if str(t.getIoType())=='OUTPUT'];assert len(drivers)==1
driver=drivers[0];assert driver.getInst().getName()=='wire30226'and driver.getMTerm().getName()=='X'
ref=driver.getInst();rails={p:ref.findITerm(p).getNet().getName()for p in ['VDD','VSS']}
for p,n in rails.items():assert str(b.findNet(n).getSigType())in ('POWER','GROUND')
last=net;sink.disconnect();added=[]
for index in range(6):
 name='nssoc_ram_men_hold_'+str(index);assert not b.findInst(name)and not b.findNet(name+'_net')
 i=odb.dbInst.create(b,small,name);assert i
 i.setOrient(ref.getOrient());x,y=ref.getLocation();i.setLocation(x+(index+1)*b.getDbUnitsPerMicron()*2,y);i.setPlacementStatus('PLACED')
 outnet=odb.dbNet.create(b,name+'_net');outnet.setSigType('SIGNAL')
 i.findITerm('A').connect(last);i.findITerm('X').connect(outnet)
 for p,n in rails.items():i.findITerm(p).connect(b.findNet(n))
 added.append(name);last=outnet
sink.connect(last)
manifest=dict(selected_buffers=selected,new_master='sg13g2_buf_4',hold_buffers=added,hold_source_net='net30226',hold_sink='u_ram.g_ram_2048x64_ecc.u_b2/A_MEN',rails=rails,original_statuses=original_statuses,accepted=False)
(out/'eco-plan.json').write_text(json.dumps(manifest,indent=2)+'\n');odb.write_db(d,str(out/'eco-before-legalize.odb'))
