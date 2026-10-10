"""Measure actual emitted combinational pin-graph depth, not RTL loop depth."""
from pathlib import Path
import argparse,collections,functools,hashlib,json

def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def analyze(path,version):
 m=json.loads(path.read_text())['modules'][f'soc_pcie_gen3_continuous_rx_integrity_v{version}']
 cells=m['cells'];nets=m['netnames'];drivers={};sequential=set()
 for name,c in cells.items():
  assert c['type'].startswith('sg13g2_')
  seq='CLK' in c['port_directions']
  if seq:sequential.add(name)
  for port,direction in c['port_directions'].items():
   if direction=='output':
    for bit in c['connections'][port]:
     assert isinstance(bit,int) and bit not in drivers,(name,port,bit)
     drivers[bit]=(name,port)
 start=set(nets['framer.read_ptr']['bits'])
 assert len(start)==7 and all(b in drivers and drivers[b][0] in sequential for b in start)
 groups={};endpoint_notes={}
 for field in ['keep','sop','eop','dllp']:
  raw=list(nets['framer.read_'+field]['bits']);groups['read_'+field]=[b for b in raw if b in drivers]
  endpoint_notes['read_'+field]=dict(original_label_bits=len(raw),constant_bits=sum(not isinstance(b,int) for b in raw),undriven_dead_alias_bits=sum(isinstance(b,int) and b not in drivers for b in raw))
 for field in ['data','keep','sop','eop','dllp','sequence']:
  bits=nets['framer.output_'+field]['bits'];target=[]
  for b in bits:
   if not isinstance(b,int):
    assert b in ('0','1'),('UNKNOWN_OUTPUT_BIT',field,b)
    continue
   name,_=drivers[b];assert name in sequential and len(cells[name]['connections']['D'])==1
   target.extend(cells[name]['connections']['D'])
  groups['output_'+field+'_flop_D']=target
  endpoint_notes['output_'+field+'_flop_D']=dict(original_register_bits=len(bits),constant_folded_bits=sum(not isinstance(b,int) for b in bits))
 active=set()
 @functools.lru_cache(None)
 def depth(bit):
  if bit in start:return (0,())
  if not isinstance(bit,int) or bit not in drivers:return None
  name,port=drivers[bit]
  if name in sequential:return None
  assert bit not in active,('COMBINATIONAL_CYCLE',bit,name)
  active.add(bit)
  c=cells[name];best=None
  for p,direction in c['port_directions'].items():
   if direction!='input':continue
   for b in c['connections'][p]:
    predecessor=depth(b)
    if predecessor is not None:
     row=(predecessor[0]+1,predecessor[1]+((name,c['type'],p,port,b,bit),))
     if best is None or row[0]>best[0]:best=row
  active.remove(bit);return best
 results={}
 for group,bits in groups.items():
  rows=[(depth(b),b) for b in bits];reachable=[(x,b) for x,b in rows if x is not None]
  if not reachable:
   assert group.startswith('read_'),('NO_POINTER_TO_OUTPUT_REGISTER_CONE',group)
   results[group]=dict(status='DEAD_INTERNAL_ALIAS_NOT_EMITTED_ENDPOINT',maximum_cell_depth=None,endpoint_notes=endpoint_notes[group]);continue
  longest,endbit=max(reachable,key=lambda r:r[0][0])
  counts=collections.Counter(row[1] for row in longest[1])
  results[group]=dict(endpoint_notes=endpoint_notes[group],endpoint_bits=len(bits),pointer_reachable_bits=len(reachable),maximum_cell_depth=longest[0],minimum_reachable_cell_depth=min(x[0] for x,b in reachable),maximum_endpoint_bit=endbit,maximum_path_cell_types=dict(counts),maximum_path=[dict(cell=n,type=t,input_port=i,output_port=o,input_bit=b,output_bit=e) for n,t,i,o,b,e in longest[1]])
 return dict(source={'path':str(path),**pin(path)},top=f'soc_pcie_gen3_continuous_rx_integrity_v{version}',mapped_cells=len(cells),flops=len(sequential),source_pointer_bits=sorted(start),groups=results,method='Longest emitted combinational cell pin-dependency path from actual seven read_ptr flop Q bits to named read metadata and output-register D. All other flop Q bits are boundaries. Each native combinational output conservatively depends on all declared input pins; this is structural depth, not a sensitized path, STA delay or a frequency acceptance claim.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--rejected',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 assert not a.out.exists()
 candidate=analyze(a.candidate,18);rejected=analyze(a.rejected,14)
 delta={g:dict(candidate_depth=row['maximum_cell_depth'],rejected_V14_depth=rejected['groups'][g]['maximum_cell_depth'],difference=(row['maximum_cell_depth']-rejected['groups'][g]['maximum_cell_depth']) if row['maximum_cell_depth'] is not None and rejected['groups'][g]['maximum_cell_depth'] is not None else None) for g,row in candidate['groups'].items()}
 a.out.write_text(json.dumps(dict(status='MEASURED_NATIVE_PIN_GRAPH_DEPTH_NOT_TIMING_ACCEPTANCE',method_source=pin(Path(__file__)),candidate=candidate,rejected_V14=rejected,comparison=delta,physical_acceptance=False),indent=2)+'\n')
 print(json.dumps(delta))
