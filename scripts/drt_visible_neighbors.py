# SPDX-License-Identifier: Apache-2.0
"""Phases of the visible-neighbour DRT experiment, run inside the pinned engine with -python.

prepare: restore every net of the 47-net-cleared database to its original class
(signals ROUTED, original FIXED nets stay FIXED) and record a wire census.
census: record the wire census of a routed database for comparison.
"""
import hashlib,json,os,sys
import odb
def census(block):
    out={}
    for n in block.getNets():
        w=n.getWire()
        raw=b'' if w is None else json.dumps([[w.getOpcode(i),w.getData(i)]for i in range(w.length())]).encode()
        out[n.getName()]=[str(n.getWireType()),hashlib.sha256(raw).hexdigest()[:16]]
    return out
def main():
    phase,src,dst=os.environ['PHASE'],os.environ['SRC'],os.environ['DST']
    db=odb.dbDatabase.create();odb.read_db(db,src);b=db.getChip().getBlock()
    if phase=='prepare':
        classes=json.load(open(os.environ['CLASSES']))
        changed=0
        for name,kind in classes.items():
            n=b.findNet(name);assert n is not None,name
            if kind is not None and str(n.getWireType())!=kind:n.setWireType(kind);changed+=1
        odb.write_db(db,dst);print('PREPARED restored_classes=%d'%changed)
    json.dump(census(b),open(os.environ['CENSUS'],'w'))
    types={}
    for t,_ in census(b).values():types[t]=types.get(t,0)+1
    print('WIRETYPES',json.dumps(types,sort_keys=True))
if __name__=='__main__':main()
