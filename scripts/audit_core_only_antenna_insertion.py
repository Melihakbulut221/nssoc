#!/usr/bin/env python3
"""Qualify additive native antenna ECO; never claims routed/signoff completion."""
import os,json,hashlib
from pathlib import Path
from audit_core_only_route_identity import snapshot
from buffer_core_only_chip_controls import load

def compare(a,b,new_cells):
 assert set(a['instances'])<=set(b['instances']),'original_instance_removed'
 changed={n:dict(before=v,after=b['instances'][n])for n,v in a['instances'].items()if b['instances'][n]!=v}
 assert not changed, 'original_instance_geometry_or_status_changed:'+repr(changed)
 assert all(b['terminals'].get(k)==v for k,v in a['terminals'].items()),'original_connection_changed'
 for k in ['special_and_ports','nets','die']:assert a[k]==b[k], 'changed:'+k
 assert new_cells and set(new_cells)==set(b['instances'])-set(a['instances']),'new_cell_inventory_mismatch'
 for name,cell in new_cells.items():
  assert cell['master']=='sg13g2_antennanp', 'unexpected_master'
  assert cell['placement']=='PLACED', 'unplaced_diode'
  assert len(cell['signal_terms'])==1 and cell['signal_terms'][0]['pin']=='A','unexpected_diode_terminals'
  assert all(t['net'] in a['nets']for t in cell['terms']),'unconnected_or_unknown_diode_net'
  for t in cell['terms']:
   if t['type']in ['POWER','GROUND']:assert a['nets'][t['net']]==t['type'],'wrong_supply_type'
   else:assert a['nets'][t['net']]=='SIGNAL','non_signal_diode_connection'
 return dict(original_instances=len(a['instances']),new_diodes=len(new_cells),total_instances=len(b['instances']),original_geometry_status_and_connections_preserved=True,power_geometry_ports_and_die_preserved=True,all_new_terminals_connected=True,signal_wire_geometry_checked=False,accepted=False)

def main():
 out=Path(os.environ['NSSOC_ANTENNA_AUDIT_OUT']);r={'accepted':False}
 try:
  paths=[Path(os.environ[x])for x in ['NSSOC_ROUTE_IDENTITY_BEFORE','NSSOC_ROUTE_IDENTITY_AFTER']]
  hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
  d0,b0=load(paths[0]);d1,b1=load(paths[1]);a=snapshot(b0);b=snapshot(b1)
  cells={}
  for i in b1.getInsts():
   if i.getName()in a['instances']:continue
   terms=[dict(pin=t.getMTerm().getName(),type=str(t.getMTerm().getSigType()),net=t.getNet().getName()if t.getNet()else None)for t in i.getITerms()]
   cells[i.getName()]=dict(master=i.getMaster().getName(),placement=str(i.getPlacementStatus()),terms=terms,signal_terms=[t for t in terms if t['type']not in ['POWER','GROUND']])
  r['new_cells']=cells;r['changed_original_instances']={n:dict(before=v,after=b['instances'].get(n))for n,v in a['instances'].items()if b['instances'].get(n)!=v}
  r.update(compare(a,b,cells))
  assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
  r.update(sources_unchanged=True,source_hashes=hashes,status='ADDITIVE_DIODE_ECO_VERIFIED_NOT_ROUTED')
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:out.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
