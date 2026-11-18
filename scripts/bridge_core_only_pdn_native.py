#!/usr/bin/env python3
"""Connect existing core PG stripes to parent rails using checked native metal/vias."""
import os,json,gzip,hashlib
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_BRIDGE_OUT']);db=odb.dbDatabase.create();odb.read_db(db,str(out/'source-pdn.odb'));block=db.getChip().getBlock()
g=json.loads(gzip.decompress((out/'source-metal-shapes.json.gz').read_bytes()));assert g['dbu']==1000
shapes=g['layers'];assert hashlib.sha256((out/'source-pdn.odb').read_bytes()).hexdigest()=='e107f69e72ee98232a78356d4a8f54bee74009df2933cc919a6485c837c8cb42'
def snapshot(b):
    return dict(instances=sorted((i.getName(),i.getMaster().getName(),str(i.getPlacementStatus()),str(i.getOrient()),i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax())for i in b.getInsts()),connections=sorted((i.getName(),t.getMTerm().getName(),t.getNet().getName()if t.getNet()else None)for i in b.getInsts()for t in i.getITerms()),pins=sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()),sorted((str(p.getPlacementStatus()),sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for x in p.getBoxes()))for p in t.getBPins()))for t in b.getBTerms()))
before=snapshot(block)
# Reuse a native generated via whose metal landing fits the existing 2.2um stripes.
vias=[]
for via in block.getVias():
    boxes=list(via.getBoxes());layers={b.getTechLayer().getName()for b in boxes}
    if layers!={'TopMetal1','TopVia2','TopMetal2'}:continue
    if all(-1100<=b.xMin()<b.xMax()<=1100 and -1100<=b.yMin()<b.yMax()<=1100 for b in boxes):vias.append(via)
assert vias,'No existing native via fits the intended bridge'
via=sorted(vias,key=lambda v:v.getName())[0]
def clear(layer,rect,net,spacing=2000):
    a=[rect[0]-spacing,rect[1]-spacing,rect[2]+spacing,rect[3]+spacing]
    return not any(x[4]!=net and a[0]<x[2]and x[0]<a[2]and a[1]<x[3]and x[1]<a[3]for x in shapes[layer])
bridges=[]
for net in ['VDD','VSS']:
    cores=sorted([x for x in shapes['TopMetal1']if x[4]==net and x[5].startswith('pin:u_core/')and x[3]-x[1]>2000000])
    rails=[x for x in shapes['TopMetal2']if x[4]==net and x[5]=='wire'and x[2]-x[0]>3000000]
    assert len(cores)==43
    sw=odb.dbSWire.create(block.findNet(net),'ROUTED');assert sw
    for c in cores:
        assert c[2]-c[0]==2200;cx=(c[0]+c[2])//2
        for side in ['bottom','top']:
            choices=[]
            for r in rails:
                cy=(r[1]+r[3])//2
                if not r[0]+1100<=cx<=r[2]-1100:continue
                if side=='bottom'and cy<c[1]:rect=[c[0],cy-1100,c[2],c[1]+1100]
                elif side=='top'and cy>c[3]:rect=[c[0],c[3]-1100,c[2],cy+1100]
                else:continue
                if not clear('TopMetal1',rect,net):continue
                landing=[];valid=True
                for vb in via.getBoxes():
                    layer=vb.getTechLayer().getName();box=[cx+vb.xMin(),cy+vb.yMin(),cx+vb.xMax(),cy+vb.yMax()]
                    if layer=='TopVia2':continue
                    if not clear(layer,box,net):valid=False;break
                    container=rect if layer=='TopMetal1'else r
                    if not(container[0]<=box[0]<box[2]<=container[2]and container[1]<=box[1]<box[3]<=container[3]):valid=False;break
                    landing.append((layer,box))
                if valid:choices.append((rect[3]-rect[1],rect,cx,cy,landing))
            assert choices,('No clearance-safe bridge',net,c,side)
            _,rect,cx,cy,landing=min(choices)
            assert odb.dbSBox.create(sw,db.getTech().findLayer('TopMetal1'),*rect,'STRIPE')
            assert odb.dbSBox.create(sw,via,cx,cy,'STRIPE')
            shapes['TopMetal1'].append([*rect,net,'bridge'])
            for layer,box in landing:shapes[layer].append([*box,net,'bridge-via'])
            bridges.append(dict(net=net,side=side,rect_dbu=rect,via_xy_dbu=[cx,cy],native_via=via.getName()))
assert len(bridges)==172 and snapshot(block)==before
odb.write_db(db,str(out/'chip-pdn.odb'));odb.write_def(block,str(out/'chip-pdn.def'))
check=odb.dbDatabase.create();odb.read_db(check,str(out/'chip-pdn.odb'));assert snapshot(check.getChip().getBlock())==before
report=dict(bridges=bridges,bridge_count=len(bridges),native_via=via.getName(),native_via_geometry=[dict(layer=b.getTechLayer().getName(),rect=[b.xMin(),b.yMin(),b.xMax(),b.yMax()])for b in via.getBoxes()],minimum_checked_foreign_metal_spacing_um=2.0,original_logic_placement_and_ports_unchanged=True,readback_equal=True,accepted=False,ir_em_qualified=False,foundry_drc_qualified=False)
(out/'bridge-audit.json').write_text(json.dumps(report,indent=2)+'\n')
