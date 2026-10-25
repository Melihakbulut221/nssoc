#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read paired actual routed clock nets with pinned native OpenDB."""
import hashlib,json
from pathlib import Path
import odb
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-geometry'
TARGETS=['clkbuf_3_5_0_pcie_clk_i','clkbuf_3_6_0_pcie_clk_i','clkbuf_6_46_0_pcie_clk_i','clkbuf_leaf_256_pcie_clk_i']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    pins=json.loads((OUT/'sources.json').read_text());result={}
    for tag,pin in pins.items():
        path=OUT/tag/'run/2-openroad-detailedrouting/soc_top.odb'
        assert sha(path)==pin['odb_sha256']
        db=odb.dbDatabase.create();odb.read_db(db,str(path))
        block=db.getChip().getBlock();scale=block.getDbUnitsPerMicron();assert scale>0
        def term(t):
            inst=t.getInst();xy=t.getAvgXY();assert len(xy)==3 and xy[0]
            return dict(instance=inst.getName(),pin=t.getMTerm().getName(),master=inst.getMaster().getName(),
                direction=str(t.getIoType()),xy_um=[xy[1]/scale,xy[2]/scale],
                location_dbu=list(inst.getLocation()),orientation=str(inst.getOrient()))
        nets=[]
        for name in TARGETS:
            inst=block.findInst(name);assert inst and inst.getMaster().getName()=='sg13g2_buf_8'
            output=inst.findITerm('X');assert output and str(output.getIoType())=='OUTPUT'
            net=output.getNet();assert net and str(net.getSigType())in ('CLOCK','SIGNAL')
            members=[term(t)for t in net.getITerms()]
            assert len({(t['instance'],t['pin'])for t in members})==len(members)
            assert [(t['instance'],t['pin'])for t in members if t['direction']=='OUTPUT']==[(name,'X')]
            assert not list(net.getBTerms())
            wire=net.getWire();assert wire and wire.getLength()>0
            driver=term(output)
            for x in members:
                x['manhattan_from_driver_um']=sum(abs(a-b)for a,b in zip(x['xy_um'],driver['xy_um']))
            rule=net.getNonDefaultRule()
            ndr=None if rule is None else dict(name=rule.getName(),hard_spacing=rule.getHardSpacing(),
              layers=[dict(name=l.getName(),width_dbu=rule.getLayerRule(l).getWidth(),spacing_dbu=rule.getLayerRule(l).getSpacing())
                      for l in db.getTech().getLayers()if rule.getLayerRule(l)])
            nets.append(dict(driver=name+'/X',net=net.getName(),sigtype=str(net.getSigType()),driver_geometry=driver,
               terminals=sorted(members,key=lambda x:(x['instance'],x['pin'])),ndr=ndr,routed_wire_total_um=wire.getLength()/scale))
        assert sha(path)==pin['odb_sha256']
        result[tag]=dict(source_odb_sha256=pin['odb_sha256'],dbu_per_um=scale,instances=len(block.getInsts()),nets=nets)
    assert [x['driver']for x in result['before']['nets']]==[x['driver']for x in result['after']['nets']]
    changes=[]
    for a,b in zip(result['before']['nets'],result['after']['nets']):
        assert a['net']==b['net']and a['driver_geometry']==b['driver_geometry']and a['ndr']==b['ndr']
        am={(x['instance'],x['pin']):x for x in a['terminals']}
        bm={(x['instance'],x['pin']):x for x in b['terminals']}
        assert set(am)<=set(bm)
        assert all(am[k]==bm[k]for k in am),'Existing clock cells or pins moved'
        changes.append(dict(driver=a['driver'],net=a['net'],original_pin_geometry_unchanged=True,
          added_pins=[bm[k]for k in bm.keys()-am.keys()],wire_um_before=a['routed_wire_total_um'],
          wire_um_after=b['routed_wire_total_um'],wire_length_delta_um=b['routed_wire_total_um']-a['routed_wire_total_um']))
    (OUT/'native-geometry.json').write_text(json.dumps(dict(status='PASS_READ_ONLY_PAIRED_CLOCK_ROUTE_GEOMETRY',sources=result,changes=changes,
      timing_or_repair_accepted=False,scope='Actual route total length, pin centers/memberships and NDR. Total length is not a branch delay.'),indent=2)+'\n')
if __name__=='__main__':main()
