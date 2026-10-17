#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native geometry for actual replacement-cell compatibility, not equality."""
import json
import audit_ethernet_delay_candidate_native as base
OUT=base.OUT

def placed(inst,row,flip=True):
    layer,x1,y1,x2,y2=row;ox,oy=inst.getOrigin()
    assert str(inst.getOrient())=='MX','Only the source-bound actual MX instance is supported'
    return [layer,ox+x1,oy-y2,ox+x2,oy-y1]if flip else [layer,ox+x1,oy+y1,ox+x2,oy+y2]
def shape(v):return [v.getTechLayer().getName(),v.xMin(),v.yMin(),v.xMax(),v.yMax()]
def overlap(a,b):
    return a[0]==b[0]and max(a[1],b[1])<min(a[3],b[3])and max(a[2],b[2])<min(a[4],b[4])
result=dict(status='RUNNING',accepted=False,parent_sha256=base.PARENT_SHA,candidate_sha256=base.CHILD_SHA,instances={})
for key,db in [('parent',base.old),('candidate',base.new)]:
    block=db.getChip().getBlock();inst=block.findInst(base.CELL);pins={};raw={}
    for term in inst.getITerms():
        name=term.getMTerm().getName()
        raw[name]=sorted(shape(v)for p in term.getMTerm().getMPins()for v in p.getGeometry())
        pins[name]=sorted([l.getName(),r.xMin(),r.yMin(),r.xMax(),r.yMax()]for l,r in term.getGeometries())
        assert sorted(placed(inst,r)for r in raw[name])==pins[name],('MX transform differs from native placed pins',key,name)
    assert any(sorted(placed(inst,r,False)for r in raw[p])!=pins[p]for p in raw),'Actual orientation fault not rejected'
    obs=sorted(placed(inst,shape(v))for v in inst.getMaster().getObstructions())
    bounds=[min(r[1]for rows in pins.values()for r in rows)-1000,min(r[2]for rows in pins.values()for r in rows)-1000,max(r[3]for rows in pins.values()for r in rows)+1000,max(r[4]for rows in pins.values()for r in rows)+1000]
    grid=[]
    for net in block.getNets():
        if str(net.getSigType())not in ('POWER','GROUND'):continue
        for sw in net.getSWires():
            for v in sw.getWires():
                if v.isVia():continue
                row=shape(v)
                if row[1]<=bounds[2]and row[3]>=bounds[0]and row[2]<=bounds[3]and row[4]>=bounds[1]:grid.append(dict(net=net.getName(),shape=row))
    result['instances'][key]=dict(pins=pins,obstructions=obs,local_planar_grid=grid,pin_nets={t.getMTerm().getName():t.getNet().getName()for t in inst.getITerms()},orientation_control_rejected=True,native_transform_verified_all_pins=True)
result['minimum_spacing_dbu']={l.getName():l.getSpacing()for l in base.new.getTech().getLayers()if str(l.getType())=='ROUTING'}
assert base.sha(base.SOURCE/'parent/routed.odb')==base.PARENT_SHA and base.sha(base.SOURCE/'routed.odb')==base.CHILD_SHA
result.update(status='COMPLETE_NATIVE_PLACED_PIN_OBSTRUCTION_EXPORT_NOT_SIGNOFF',source_unchanged=True,scope='Actual placed LEF pins, obstructions, default layer spacings and nearby planar PG routes. No PG via/cut/enclosure, internal cell GDS or foundry spacing qualification.')
(OUT/'pin-compatibility-native.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],flush=True)
