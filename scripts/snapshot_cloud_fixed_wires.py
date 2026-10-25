#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native actual-route design signature and encoded route-type observations."""
import collections,hashlib,json,os
from pathlib import Path
import odb

def digest(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    db=odb.dbDatabase.create();odb.read_db(db,os.environ['NSSOC_FIXED_INPUT']);b=db.getChip().getBlock()
    cells=[];nets=[];fixed=[];types=collections.Counter();paths=collections.Counter();negative=[];wired=0
    for i in b.getInsts():
        cells.append((i.getName(),i.getMaster().getName(),list(i.getLocation()),list(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus()),sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms())))
    for n in b.getNets():
        rule=n.getNonDefaultRule()
        nets.append((n.getName(),str(n.getSigType()),sorted((t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()),sorted(t.getName() for t in n.getBTerms()),rule.getName() if rule else None))
        if rule:fixed.append(('ndr',n.getName(),rule.getName(),rule.getHardSpacing(),[(l.getName(),rule.getLayerRule(l).getWidth(),rule.getLayerRule(l).getSpacing()) for l in db.getTech().getLayers() if rule.getLayerRule(l)]))
        if str(n.getSigType()) in ('POWER','GROUND'):
            fixed.append(('power',n.getName(),[(s.isVia(),s.getTechVia().getName() if s.isVia() and s.getTechVia() else None,s.getBlockVia().getName() if s.isVia() and s.getBlockVia() else None,s.getTechLayer().getName() if not s.isVia() else None,s.xMin(),s.yMin(),s.xMax(),s.yMax()) for w in n.getSWires() for s in w.getWires()]))
            continue
        w=n.getWire()
        if not w:continue
        wired+=1;d=odb.dbWireDecoder();d.begin(w);net_types=set()
        while True:
            op=d.next()
            if op==d.END_DECODE:break
            if op in (d.PATH,d.JUNCTION,d.SHORT,d.VWIRE):
                kind=str(d.getWireType());net_types.add(kind);paths[kind]+=1
        assert len(net_types)==1,(n.getName(),net_types)
        types.update(net_types)
        if len(negative)<1 and net_types=={'ROUTED'}:
            previous=str(n.getWireType());n.setWireType('FIXED');nd=odb.dbWireDecoder();nd.begin(w);op=nd.next();assert op in (nd.PATH,nd.SHORT,nd.VWIRE)
            negative.append(dict(net=n.getName(),metadata=str(n.getWireType()),encoded=str(nd.getWireType())))
            assert negative[-1]['metadata']=='FIXED' and negative[-1]['encoded']=='ROUTED';n.setWireType(previous)
    for p in b.getBTerms():
        fixed.append(('port',p.getName(),str(p.getIoType()),str(p.getSigType()),[(s.getTechLayer().getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()) for pin in p.getBPins() for s in pin.getBoxes()]))
    result=dict(counts=dict(instances=len(cells),nets=len(nets),wired_nets=wired),instances_sha256=digest(sorted(cells)),nets_sha256=digest(sorted(nets)),fixed_data_sha256=digest(fixed),wire_type_net_counts=dict(types),encoded_path_counts=dict(paths),metadata_only_negative_control=negative,metadata_only_negative_control_rejected=bool(negative))
    assert result['counts']==dict(instances=113791,nets=113863,wired_nets=113556)
    Path(os.environ['NSSOC_FIXED_OUTPUT']).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
