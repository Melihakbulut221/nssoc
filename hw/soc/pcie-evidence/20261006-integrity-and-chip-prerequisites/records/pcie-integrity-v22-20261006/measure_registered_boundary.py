"""Measure actual native descriptor FF boundaries and complete pin ancestry."""
from pathlib import Path
import collections,functools,hashlib,json
B=Path(__file__).resolve().parent
P=Path('/dev/shm/nssoc-integrity-v22-balanced-map-01/mapped.json')
m=json.loads(P.read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v22'];cells=m['cells'];nets=m['netnames'];drivers={};sequential=set()
for name,c in cells.items():
 assert c['type'].startswith('sg13g2_')
 if 'CLK' in c['port_directions']:sequential.add(name)
 for port,direction in c['port_directions'].items():
  if direction=='output':
   for bit in c['connections'][port]:assert isinstance(bit,int) and bit not in drivers;drivers[bit]=(name,port)
start=set(nets['framer.read_ptr']['bits']);assert len(start)==7 and all(drivers[b][0] in sequential for b in start)
active=set()
@functools.lru_cache(None)
def leaves(bit):
 if not isinstance(bit,int) or bit not in drivers:return frozenset([bit])
 name,_=drivers[bit]
 if name in sequential:return frozenset([bit])
 assert bit not in active;active.add(bit);v=set()
 c=cells[name]
 for p,d in c['port_directions'].items():
  if d=='input':
   for b in c['connections'][p]:v.update(leaves(b))
 active.remove(bit);return frozenset(v)
@functools.lru_cache(None)
def pointer_depth(bit):
 if bit in start:return 0
 if not isinstance(bit,int) or bit not in drivers:return None
 name,_=drivers[bit]
 if name in sequential:return None
 c=cells[name];d=[pointer_depth(b) for p,k in c['port_directions'].items() if k=='input' for b in c['connections'][p]];d=[x for x in d if x is not None]
 return max(d)+1 if d else None
# Original ring contents must never bypass the new descriptor data bank.
# Read-pointer/control ancestry is allowed through fault/overflow enables.
ring_content_q=set()
ring_labels={}
for name,net in nets.items():
 if name.startswith(tuple('framer.'+n+'['for n in ('slot_data','slot_keep','slot_sop','slot_eop','slot_dllp','slot_sequence','slot_tag','slot_verdict','verdict'))):
  ring_labels[name]=net['bits']
  for bit in net['bits']:
   if isinstance(bit,int) and bit in drivers and drivers[bit][0]in sequential:ring_content_q.add(bit)
assert ring_content_q and any(n.startswith('framer.slot_data[')for n in ring_labels),'Original ring content labels/FFs must be present'
fields=[];descriptor_cells=set();checked_output_bits=0
for field,width in zip(('data','keep','sop','eop','dllp','sequence'),(128,16,16,16,16,48)):
 rb=nets['framer.retire_'+field]['bits'];ob=nets['framer.output_'+field]['bits'];assert len(rb)==len(ob)==width
 rows=[]
 for index,(r,o) in enumerate(zip(rb,ob)):
  if not isinstance(r,int):assert r in ('0','1');assert o==r;continue
  cell,port=drivers[r];assert cell in sequential and port=='Q';descriptor_cells.add(cell)
  assert len(cells[cell]['connections']['D'])==1;rd=cells[cell]['connections']['D'][0]
  assert isinstance(o,int);output_cell,output_port=drivers[o];assert output_cell in sequential and output_port=='Q'
  assert len(cells[output_cell]['connections']['D'])==1;od=cells[output_cell]['connections']['D'][0]
  assert r in leaves(od),('MISSING_REGISTERED_DESCRIPTOR_PAYLOAD_PATH',field,index)
  assert not leaves(od)&ring_content_q,('DIRECT_RING_CONTENT_BYPASSES_DESCRIPTOR',field,index,sorted(leaves(od)&ring_content_q))
  rows.append(dict(bit=index,descriptor_q=r,descriptor_cell=cell,descriptor_d=rd,output_cell=output_cell,output_d=od,descriptor_q_in_output_d_support=True,read_pointer_to_descriptor_d_depth=pointer_depth(rd),read_pointer_to_output_d_depth=pointer_depth(od)))
  checked_output_bits+=1
 fields.append(dict(field=field,width=width,constant_folded_bits=width-len(rows),rows=rows))
flags={}
for field in ('valid','has_data'):
 bits=nets['framer.retire_'+field]['bits'];assert len(bits)==1 and isinstance(bits[0],int)
 name,port=drivers[bits[0]];assert name in sequential and port=='Q';flags[field]=dict(bit=bits[0],cell=name,type=cells[name]['type'])
assert checked_output_bits>0 and descriptor_cells and len(set(r['cell'] for r in flags.values()))==2
availability_consumers=[]
for group in ('read_ptr','retire_valid'):
 bits=nets['framer.'+group]['bits'];assert len(bits)==(7 if group=='read_ptr' else 1)
 for index,bit in enumerate(bits):
  assert isinstance(bit,int)and bit in drivers
  name,port=drivers[bit];assert name in sequential and port=='Q'
  ds=cells[name]['connections']['D'];assert len(ds)==1
  support=leaves(ds[0])
  forbidden={b for field in ('data','keep','sop','eop','dllp','sequence') for b in nets['framer.retire_'+field]['bits'] if isinstance(b,int)}
  assert not support&forbidden,('DESCRIPTOR_PAYLOAD_IN_AVAILABILITY_CONSUMER',group,index)
  assert not support&ring_content_q,('ORIGINAL_RING_CONTENT_IN_AVAILABILITY_CONSUMER',group,index)
  availability_consumers.append(dict(group=group,bit=index,q=bit,cell=name,d=ds[0],no_descriptor_payload_q=True,no_original_ring_content_q=True,support_size=len(support)))
assert len(availability_consumers)==8
alias_inventory={group:dict(emitted=('framer.'+group in nets),bits=nets.get('framer.'+group,{}).get('bits'))for group in ('retire','retire_room','retire_pop')}
r=dict(status='PASS_EMITTED_REGISTERED_RETIRE_PAYLOAD_BOUNDARY_ONLY',mapped_source=dict(path=str(P),bytes=P.stat().st_size,sha256=hashlib.sha256(P.read_bytes()).hexdigest()),method_source=dict(bytes=Path(__file__).stat().st_size,sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),mapped_cells=len(cells),mapped_flops=len(sequential),distinct_descriptor_payload_flops=len(descriptor_cells),descriptor_flags=flags,availability_consumer_flop_d=availability_consumers,internal_alias_inventory=alias_inventory,checked_nonconstant_output_bits=checked_output_bits,original_ring_content_q_bits=len(ring_content_q),original_ring_label_count=len(ring_labels),no_original_ring_content_q_in_output_d=True,fields=fields,scope='Actual emitted native Q/D pins. Every nonconstant output payload bit structurally depends on its corresponding descriptor FF Q; no original ring content Q enters output D and no descriptor payload Q or original ring content Q enters the actual seven read_ptr D and retire_valid D availability consumers. Internal retire aliases may be optimized away and are inventoried. has_data D intentionally reads current keep and is not subject to the ring-content ban. Read-pointer and parser control ancestry is allowed via the original fault/overflow enables; not asserted absent. Longest read-pointer cell depths treat other FFs as boundaries, conservatively all cell inputs; not sensitized delay, full functional equivalence or physical acceptance.')
out=B/'native-registered-boundary.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(descriptor_cells),len(sequential))
