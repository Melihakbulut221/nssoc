#!/usr/bin/env python3
"""Resize only four measured buf1 cells on current worst setup data path."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d,b=load(out/'core-routed.odb')
text=(out/'slow-max.rpt').read_text().split('Startpoint:',2)[1]
assert text.startswith(' nssoc_sta_i_75298 ') and 'Endpoint: nssoc_sta_i_77885 'in text and 'slack (VIOLATED)'in text
text=text.split('data arrival time',1)[0]
selected={}
for line in text.splitlines():
 m=re.search(r'^\s*\d+\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+[0-9.]+\s+[\^v]\s+(\S+)/X \(sg13g2_buf_1\)',line)
 if m and float(m[3])>=.45:selected[m[4]]=dict(cap_pf=float(m[1]),slew_ns=float(m[2]),delay_ns=float(m[3]))
assert set(selected)=={'fanout4819','fanout359','nssoc_sta_i_48118','fanout311'},selected
assert len(list(b.getInsts()))==104891
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
for i in b.getInsts():
 if str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
master=d.findMaster('sg13g2_buf_4');assert master
for name in selected:
 i=b.findInst(name);assert i and i.getMaster().getName()=='sg13g2_buf_1'
 assert {t.getMTerm().getName()for t in i.getITerms()}=={'A','X','VDD','VSS'}
 assert i.swapMaster(master);i.setPlacementStatus('PLACED')
odb.write_db(d,str(out/'eco-before-legalize.odb'))
(out/'eco-plan.json').write_text(json.dumps(dict(selected_buffers=selected,new_master='sg13g2_buf_4',original_statuses=statuses,accepted=False),indent=2)+'\n')
