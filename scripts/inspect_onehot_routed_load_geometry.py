#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read real routed data-net geometry without changing the database."""
import hashlib,json
from pathlib import Path
import odb
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-routed-load-geometry'
SOURCE=OUT/'source/run/2-openroad-detailedrouting/soc_top.odb'
EXPECTED='1f6f3a87a157e8829d4248faef249907712d8ec1d33b87ee01271fc3a8be4236'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def different_native_terminal(t,driver):
    # SWIG can return different Python proxies for the same database terminal.
    return t.getId()!=driver.getId()
def controls():
    class Proxy:
        def __init__(self,n):self.n=n
        def getId(self):return self.n
    driver=Proxy(1);alias=Proxy(1);sink=Proxy(2)
    assert driver is not alias and driver!=alias
    assert not different_native_terminal(alias,driver)
    assert different_native_terminal(sink,driver)
    return dict(distinct_proxies_of_same_terminal_excluded=True,distinct_native_sink_retained=True)
def main():
    tested=controls()
    assert digest(SOURCE)==EXPECTED
    db=odb.dbDatabase.create();odb.read_db(db,str(SOURCE))
    block=db.getChip().getBlock();scale=block.getDbUnitsPerMicron();assert scale>0
    targets=json.loads((OUT/'targets.json').read_text())['targets'];assert targets
    def terminal(t):
        point=t.getAvgXY();assert len(point)==3 and point[0],('Missing native pin geometry',t.getInst().getName(),t.getMTerm().getName(),point)
        inst=t.getInst();b=inst.getBBox()
        return dict(instance=inst.getName(),pin=t.getMTerm().getName(),master=inst.getMaster().getName(),direction=str(t.getIoType()),xy_um=[point[1]/scale,point[2]/scale],instance_bbox_um=[b.xMin()/scale,b.yMin()/scale,b.xMax()/scale,b.yMax()/scale])
    rows=[]
    for target in targets:
        inst=block.findInst(target['instance']);assert inst and inst.getMaster().getName()==target['master']
        pin=inst.findITerm(target['pin']);assert pin and str(pin.getIoType())=='OUTPUT'
        net=pin.getNet();assert net and str(net.getSigType())=='SIGNAL'
        terms=list(net.getITerms());ports=list(net.getBTerms())
        assert len(terms)+len(ports)-1==target['reported_fanout'],('Reported/native fanout mismatch',target,net.getName(),len(terms),len(ports))
        assert sum(str(t.getIoType())=='OUTPUT'for t in terms)==1
        driver=terminal(pin);sinks=[terminal(t)for t in terms if different_native_terminal(t,pin)]
        assert len(sinks)+len(ports)==target['reported_fanout']
        assert all(s['direction']=='INPUT' for s in sinks),('Non-input classified as sink',net.getName(),sinks)
        assert all((s['instance'],s['pin'])!=(driver['instance'],driver['pin'])for s in sinks)
        for sink in sinks:
            sink['manhattan_from_driver_um']=sum(abs(a-b)for a,b in zip(driver['xy_um'],sink['xy_um']))
        bports=[]
        for p in ports:
            boxes=[dict(layer=b.getTechLayer().getName(),bbox_um=[b.xMin()/scale,b.yMin()/scale,b.xMax()/scale,b.yMax()/scale])for bp in p.getBPins()for b in bp.getBoxes()]
            bports.append(dict(name=p.getName(),direction=str(p.getIoType()),shapes=boxes))
        wire=net.getWire();assert wire,('No native detailed route',net.getName())
        length=wire.getLength()/scale;assert length>0
        row=dict(selection=target,net=net.getName(),driver=driver,sinks=sorted(sinks,key=lambda x:-x['manhattan_from_driver_um']),ports=bports,routed_wire_total_um=length,maximum_sink_manhattan_um=max([s['manhattan_from_driver_um']for s in sinks],default=0),ndr=net.getNonDefaultRule().getName()if net.getNonDefaultRule()else None)
        rows.append(row)
    assert digest(SOURCE)==EXPECTED
    result=dict(controls=tested,status='COMPLETE_READ_ONLY_NATIVE_ROUTED_LOAD_GEOMETRY',accepted=False,final_timing_complete=False,full_phy_accepted=False,source_odb_sha256=EXPECTED,dbu_per_um=scale,source_instance_count=len(block.getInsts()),selected_net_count=len(rows),rows=rows,sources_unchanged=True,scope='Native pin-shape centers, routed wire total lengths and actual pin memberships for source-measured weak data drivers. Manhattan distance is geometric, not an extracted branch delay or capacitance. No edits, new STA, routing or signoff.')
    (OUT/'geometry.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
