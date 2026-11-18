#!/usr/bin/env python3
"""Exact pre/post route identity. Wire geometry is qualified separately."""
import os,json,hashlib
from pathlib import Path
from buffer_core_only_chip_controls import load,identity,connections,geom

def snapshot(b):
 r=b.getDieArea()
 return dict(instances={i.getName():(identity(i),str(i.getPlacementStatus())) for i in b.getInsts()},
   terminals=connections(b), special_and_ports=geom(b),
   nets={n.getName():str(n.getSigType()) for n in b.getNets()},
   die=(r.xMin(),r.yMin(),r.xMax(),r.yMax()))

def compare(before,after):
 for key in before:
  assert before[key]==after[key], 'route_identity_changed:'+key
 return dict(instances=len(before['instances']),nets=len(before['nets']),
   exact_instance_geometry_status_and_masters=True,exact_terminal_connections=True,
   exact_net_names_and_signal_types=True,exact_special_wires_ports_and_die=True,
   signal_wire_geometry_checked=False,transistor_lvs=False,accepted=False)

def main():
 a=Path(os.environ['NSSOC_ROUTE_IDENTITY_BEFORE']);b=Path(os.environ['NSSOC_ROUTE_IDENTITY_AFTER'])
 out=Path(os.environ['NSSOC_ROUTE_IDENTITY_OUT']);out.mkdir(parents=True,exist_ok=True)
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in (a,b)}
 d0,b0=load(a);d1,b1=load(b);r=compare(snapshot(b0),snapshot(b1))
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
 r['source_hashes']=hashes;r['sources_unchanged']=True
 (out/'route-identity.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
