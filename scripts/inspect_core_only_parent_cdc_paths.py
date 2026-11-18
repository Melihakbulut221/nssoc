#!/usr/bin/env python3
"""Bind original logical mailbox bits to actual routed parent terminals."""
import os,json
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PARENT_CDC_OUT'])
m=json.loads((out/'shell.json').read_text())['modules']['nssoc_chip']
db=odb.dbDatabase.create();odb.read_db(db,str(out/'chip-detailedroute.odb'));b=db.getChip().getBlock()
assert len(list(b.getInsts()))==1975
flops={n:c for n,c in m['cells'].items()if c['type']=='sg13g2_dfrbpq_1'}
q={c['connections']['Q'][0]:n for n,c in flops.items()};assert len(q)==358
ports={v:(n if len(p['bits'])==1 else f'{n}[{i}]')for n,p in m['ports'].items()for i,v in enumerate(p['bits'])}
def qpin(bit):
 name=q[bit];i=b.findInst(name);assert i and i.getMaster().getName()=='sg13g2_dfrbpq_1'
 pin=i.findITerm('Q');assert pin and pin.getNet()and pin.getNet().getName()==ports.get(bit,'n_'+str(bit))
 return name+'/Q'
def dpin(bit):
 name=q[bit];i=b.findInst(name);assert i and i.findITerm('D').getNet()
 return name+'/D'
snapshot=m['netnames']['u_status.snapshot']['bits'];shift=m['netnames']['u_status.shift']['bits']
assert len(snapshot)==len(shift)==192
payload=[]
for index,bit in enumerate(snapshot):
 if isinstance(bit,int):payload.append(dict(position=index,source=qpin(bit),destination=dpin(shift[index])))
 else:assert bit=='0'
assert len(payload)==162 and len({x['source']for x in payload})==156
assert len({x['destination']for x in payload})==162
chains=[]
for first,second in [('req_meta','req_sync'),('ack_meta','ack_sync'),('source_meta','source_release'),('serial_meta','serial_release')]:
 a=m['netnames']['u_status.'+first]['bits'][0];z=m['netnames']['u_status.'+second]['bits'][0]
 assert flops[q[z]]['connections']['D']==[a]
 assert flops[q[a]]['connections']['CLK']==flops[q[z]]['connections']['CLK']
 assert all(m['netnames']['u_status.'+x]['attributes']['ASYNC_REG']=='TRUE'for x in [first,second])
 chains.append(dict(name=first+'_'+second,source=qpin(a),destination=dpin(z)))
(out/'cdc-path-inventory.json').write_text(json.dumps(dict(payload=payload,synchronizer_chains=chains,accepted=False,physical_cdc_timing_qualified=False),indent=2)+chr(10))
