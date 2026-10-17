#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent native KLayout metal/via connectivity from the unchanged GDS."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gds',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    import pya
    root=Path(__file__).resolve().parents[1]
    deck=root/'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/rule_decks/general_connections.lvs'
    source=deck.read_text()
    for line in ('connect(topmetal1_con, topvia2_drw)','connect(topvia2_drw, topmetal2_con)'):
        if source.count(line)!=1:raise ValueError('Exact native metal/via connection declaration missing')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={str(p):sha(p) for p in [Path(__file__).resolve(),a.gds,a.fixture,deck]}
    record=json.loads(a.fixture.read_text());l=pya.Layout();l.read(str(a.gds));top=l.cell(record['top'])
    if top is None or l.dbu!=.001:raise ValueError('Unexpected native GDS top/grid')
    regs={layer:pya.Region(top.begin_shapes_rec(l.layer(layer,0))).merged() for layer in (126,133,134)}
    ext=pya.LayoutToNetlist('STACK',l.dbu)
    for layer,region in regs.items():ext.register(region,'gds_'+str(layer));ext.connect(region)
    ext.connect(regs[126],regs[133]);ext.connect(regs[133],regs[134]);ext.extract_netlist()
    mapped={};groups={}
    for name,pin in record['ports'].items():
        layer=pin['layer'];box=pya.DBox(*pin['box']).to_itype(l.dbu)
        actual=pya.Region(top.shapes(l.layer(layer,2)))
        if not (pya.Region(box)-actual).is_empty():raise ValueError('Missing actual GDS pin rectangle')
        texts=[s.text for s in top.each_shape(l.layer(layer,25)) if s.is_text() and s.text.string==name]
        if len(texts)!=1 or not box.contains(texts[0].trans.disp):raise ValueError('Missing or moved actual pin label')
        net=ext.probe_net(regs[layer],box.center())
        if net is None:raise ValueError('Actual endpoint conductor missing')
        groups.setdefault(net.cluster_id,[]).append(name)
        polys=[poly.to_s() for poly in regs[layer].each_merged() if poly.inside(box.center())]
        if len(polys)!=1:raise ValueError('Endpoint not on one actual merged conductor')
        mapped[name]=dict(layer=layer,point_dbu=[box.center().x,box.center().y],cluster=net.cluster_id,polygon=polys[0])
    nodes=sum(1 for _ in ext.netlist().circuit_by_name('STACK').each_net())
    if any(sha(Path(p))!=v for p,v in pins.items()):raise ValueError('Inputs changed during native audit')
    ext.write(str(a.out.with_suffix('.l2n')))
    result=dict(status='NATIVE_KLAYOUT_CONDUCTOR_PARTITION',mapping=mapped,
        partition=sorted(sorted(v) for v in groups.values()),node_count=nodes,
        inputs=pins,no_virtual_connections=True,no_devices_removed=True,
        scope='Only actualTopMetal1/TopVia2/TopMetal2 conductor fixture; not full-device LVS or PEX')
    a.out.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
