# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact entire native pin-driver graph through metadata/tie-only physical import."""
from pathlib import Path
import json,hashlib
ROOT=Path.cwd();OLD=Path('/dev/shm/nssoc-integrity-v24-balanced-map-01/mapped.json');NEW=Path('/dev/shm/nssoc-integrity-v24-balanced-import-01/mapped.json');TOP='soc_pcie_gen3_continuous_rx_integrity_v24'
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def drivers(m):
 d={};ties=set()
 def put(bit,value):
  assert isinstance(bit,int);assert bit not in d or d[bit]==value;d[bit]=value
 for n,p in m['ports'].items():
  if p['direction']=='input':
   for i,bit in enumerate(p['bits']):put(bit,('port',n,i))
 for n,c in m['cells'].items():
  for p,bits in c['connections'].items():
   if c['port_directions'][p]!='output':continue
   for i,bit in enumerate(bits):
    if c['type'] in ('sg13g2_tiehi','sg13g2_tielo'):put(bit,'1' if c['type']=='sg13g2_tiehi' else '0');ties.add(n)
    else:put(bit,('cell',n,p,i))
 return d,ties
def verify(a,b):
 ad,at=drivers(a);bd,bt=drivers(b);assert not at and len(bt)==2
 assert a['cells'].keys()==b['cells'].keys()-bt
 checks=0
 for name,c in a['cells'].items():
  n=b['cells'][name];assert c['type']==n['type'] and c['parameters']==n['parameters'] and c['port_directions']==n['port_directions']
  for p,bits in c['connections'].items():
   assert [ad[x] if isinstance(x,int) else x for x in bits]==[bd[x] if isinstance(x,int) else x for x in n['connections'][p]],(name,p)
   checks+=len(bits)
 assert a['ports'].keys()==b['ports'].keys()
 for name,p in a['ports'].items():
  n=b['ports'][name];assert p['direction']==n['direction'];assert [ad[x] if isinstance(x,int) else x for x in p['bits']]==[bd[x] if isinstance(x,int) else x for x in n['bits']]
 return checks
A=json.loads(OLD.read_text())['modules'][TOP];B=json.loads(NEW.read_text())['modules'][TOP];checks=verify(A,B);controls=[]
# Mutate the actual captured graph and require rejection; restore every mutation.
ff=next(n for n,c in B['cells'].items() if c['type'].startswith('sg13g2_dfrbp'))
for label,container,key,value in [('data_input_inversion',B['cells'][ff]['connections'],'D',['0']),('clock_disconnection',B['cells'][ff]['connections'],'CLK',['0']),('cell_model_change',B['cells'][ff],'type','sg13g2_inv_1'),('public_output_inversion',B['ports']['valid_o'],'bits',['1']),('port_width_change',B['ports']['data_o'],'bits',B['ports']['data_o']['bits'][:-1]),('extra_parameter',B['cells'][ff],'parameters',{'invalid':1})]:
 old=container[key];container[key]=value
 try:
  try:verify(A,B)
  except (AssertionError,KeyError):controls.append({'fault':label,'rejected':True})
  else:raise RuntimeError('Escaped fault '+label)
 finally:container[key]=old
assert verify(A,B)==checks
r={'status':'PASS_COMPLETE_NATIVE_CELL_PIN_AND_PORT_DRIVER_GRAPH','source':dict(path=str(OLD),**pin(OLD)),'physical_import':dict(path=str(NEW),**pin(NEW)),'method':pin(Path(__file__)),'original_cells':len(A['cells']),'new_literal_ties':2,'checked_cell_pin_bits':checks,'top_ports':len(A['ports']),'actual_graph_fault_controls':controls,'scope':'Every original native cell type/parameters/pin-driver and publicport; only literal0/1 replaced byactualtiecells. No arithmetic/sequential or functional change.'}
(ROOT/'hw/soc/out/pcie-integrity-v24-20261006/balanced-import-graph-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],checks,len(controls))
