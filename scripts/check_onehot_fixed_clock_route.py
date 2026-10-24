#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify pinned native DRT actually preserved the physical fixed clock route."""
import json,os
from pathlib import Path
import odb
from prepare_onehot_clock_restore import load,sha,identity,scan_def,route_signature,NET
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    before=Path(os.environ['NSSOC_TOPOLOGY_BEFORE']);after=Path(os.environ['NSSOC_TOPOLOGY_AFTER'])
    out=Path(os.environ['NSSOC_CLOCK_ROUTE_PROOF_OUT']);out.parent.mkdir(parents=True,exist_ok=True)
    pins={str(p):sha(p)for p in (before,after,Path(__file__))}
    observed={}
    for name,path in [('before',before),('after',after)]:
        db,block=load(path);net=block.findNet(NET);assert net and net.getWire()
        assert str(net.getWireType())=='FIXED'
        d=odb.dbWireDecoder();d.begin(net.getWire());d.next();assert str(d.getWireType())=='FIXED'
        deffile=out.parent/('fixed-clock-'+name+'.def')
        odb.write_def(block,str(deffile));statement,_=scan_def(deffile)
        observed[name]=dict(identity=identity(net),length_dbu=net.getWire().getLength(),statement_signature=route_signature(statement))
        odb.dbDatabase.destroy(db)
    assert observed['before']==observed['after'],'Native DRT changed fixed clock physical route or pin geometry'
    assert all(sha(Path(p))==h for p,h in pins.items())
    out.write_text(json.dumps(dict(status='PASS_NATIVE_DRT_FIXED_CLOCK_GEOMETRY_EXACT',
      fixed_net=NET,original_physical_route_preserved=True,source_hashes=pins,
      clock=observed['after'],scope='Only fixed clock preservation. Other geometry/topology, DRC, antenna, connectivity, RC and STA are separate gates.',
      accepted=False),indent=2)+'\n')
if __name__=='__main__':main()
