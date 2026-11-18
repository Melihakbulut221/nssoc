#!/usr/bin/env python3
"""Bind mailbox CDC structure to placed native cells; no metastability/timing claim."""
import os,json,hashlib
from pathlib import Path
from collections import Counter
import odb
out=Path(os.environ['NSSOC_CLOCK_AUDIT_OUT']);m=json.loads((out/'shell.json').read_text())['modules']['nssoc_chip']
db=odb.dbDatabase.create();odb.read_db(db,str(out/'chip-placed.odb'));b=db.getChip().getBlock()
flops={n:c for n,c in m['cells'].items()if c['type']=='sg13g2_dfrbpq_1'};assert len(flops)==358
q={c['connections']['Q'][0]:n for n,c in flops.items()};assert len(q)==358
names={bit:(n if len(p['bits'])==1 else f'{n}[{k}]')for n,p in m['ports'].items()for k,bit in enumerate(p['bits'])}
def net(bit):return names.get(bit,'const_'+bit if isinstance(bit,str)else 'n_'+str(bit))
for n,c in flops.items():
    i=b.findInst(n);assert i and i.getMaster().getName()==c['type'] and str(i.getPlacementStatus())=='PLACED'
    for pin,bits in c['connections'].items():
        assert len(bits)==1 and i.findITerm(pin).getNet().getName()==net(bits[0])
def bit(name):
    bits=m['netnames']['u_status.'+name]['bits'];assert len(bits)==1;return bits[0]
def reg(name):return q[bit(name)]
main=flops[reg('req_meta')]['connections']['CLK'][0];test=flops[reg('ack_meta')]['connections']['CLK'][0];assert main!=test
counts=Counter(c['connections']['CLK'][0]for c in flops.values());assert counts=={main:161,test:197}
chains=[]
for first,second,clock in [('req_meta','req_sync',main),('ack_meta','ack_sync',test),('source_meta','source_release',main),('serial_meta','serial_release',test)]:
    a=reg(first);z=reg(second)
    assert flops[z]['connections']['D']==[bit(first)]
    assert flops[a]['connections']['CLK']==flops[z]['connections']['CLK']==[clock]
    assert all(m['netnames']['u_status.'+n]['attributes']['ASYNC_REG']=='TRUE'for n in [first,second])
    ia=b.findInst(a);iz=b.findInst(z);ra=ia.getBBox();rz=iz.getBBox()
    chains.append(dict(first=first,second=second,first_cell=a,second_cell=z,clock_net=net(clock),center_manhattan_um=(abs(ra.xMin()+ra.xMax()-rz.xMin()-rz.xMax())+abs(ra.yMin()+ra.yMax()-rz.yMin()-rz.yMax()))/(2*db.getTech().getDbUnitsPerMicron())))
assert flops[reg('ack_meta')]['connections']['D']==[bit('ack')]
clock_sources={}
for label,clock in [('main',main),('test',test)]:
    pins=[(n,p)for n,c in m['cells'].items()if c['type'].startswith('sg13g2_IOPad')for p,v in c['connections'].items()if p=='p2c' and v==[clock]]
    assert len(pins)==1
    name,pin=pins[0];assert b.findInst(name).findITerm(pin).getNet().getName()==net(clock)
    clock_sources[label]=dict(cell=name,pin=pin,net=net(clock),flop_sinks=counts[clock])
snapshot=m['netnames']['u_status.snapshot']['bits'];active=[x for x in snapshot if isinstance(x,int)]
assert all(x in q for x in active)
source_bits=m['netnames']['u_status.status_i']['bits']
assert len(source_bits)==len(snapshot)==192
aliases={str(x):[i for i,y in enumerate(snapshot)if y==x]for x in set(active)if active.count(x)>1}
# Only constant status bits may share a captured storage bit. All payload bits
# remain individually backed by a flop; constant-one bits still reset to zero.
for positions in aliases.values():assert {source_bits[i]for i in positions}=={'1'}
assert all(x=='0' and source_bits[i]=='0' for i,x in enumerate(snapshot)if isinstance(x,str))
assert len(set(active))==156 and len(active)==162 and len(aliases)==1
assert len(snapshot)-len(active)==30
report=dict(status='PLACED_SHELL_CLOCK_AND_CDC_STRUCTURE_BOUND',clock_sources=clock_sources,synchronizer_chains=chains,snapshot_flops=len(set(active)),snapshot_flop_backed_positions=len(active),snapshot_aliases=aliases,snapshot_constants=len(snapshot)-len(active),protected_synchronizer_cells=[reg(n)for n in ['req_meta','req_sync','ack_meta','ack_sync','source_meta','source_release','serial_meta','serial_release']],source_hashes={n:hashlib.sha256((out/n).read_bytes()).hexdigest()for n in ['shell.json','chip-placed.odb']},accepted=False,cdc_timing_qualified=False,metastability_qualified=False)
(out/'clock-audit.json').write_text(json.dumps(report,indent=2)+'\n')
