#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only native exact-route comparison after the one-cell delay change."""
import hashlib,json
# This executes the independent full cell/net/PG/NDR/port audit and its actual
# input-disconnection/old-master controls before returning the native objects.
import audit_ethernet_delay_candidate_native as base
OUT=base.OUT;old,new=base.old,base.new
ob,nb=old.getChip().getBlock(),new.getChip().getBlock()
def wires(block):
    records={}
    for n in block.getNets():
        w=n.getWire()
        records[n.getName()]=dict(wire=None if w is None else hashlib.sha256(json.dumps([(str(w.getOpcode(k)),w.getData(k))for k in range(w.length())],separators=(',',':')).encode()).hexdigest(),wire_type=str(n.getWireType()),special=n.isSpecial())
    return records
before=wires(ob)
def verify():
    actual=wires(nb)
    assert actual==before,'Physical dbWire opcodes/data or wire classification changed'
    assert sum(r['wire']is not None for r in actual.values())==113796
    return hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest()
fingerprint=verify()
# An actual selected wire detachment must fail the exact same complete audit.
victim=nb.findNet('net27952');wire=victim.getWire();assert wire
wire.detach()
try:verify()
except AssertionError as e:reason=str(e)
else:raise AssertionError('Detached physical route escaped audit')
wire.attach(victim);assert verify()==fingerprint

def shape(b):
    return [b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax()]
def pins(inst):
    return {p.getMTerm().getName():sorted([layer.getName(),r.xMin(),r.yMin(),r.xMax(),r.yMax()]for layer,r in p.getGeometries())for p in inst.getITerms()}
a=ob.findInst(base.CELL);b=nb.findInst(base.CELL);ap,bp=pins(a),pins(b)
assert ap.keys()==bp.keys()=={'A','X','VDD','VSS'}
for p in ['VDD','VSS']:assert ap[p]==bp[p],('Power pin geometry changed',p)
aobs=sorted(shape(v)for v in a.getMaster().getObstructions());bobs=sorted(shape(v)for v in b.getMaster().getObstructions())
result=dict(status='RUNNING',accepted=False,parent_odb_sha256=base.PARENT_SHA,candidate_odb_sha256=base.CHILD_SHA,all114103net_wire_records_equal=True,routed_nets=113796,complete_wire_fingerprint=fingerprint,selected_pin_geometry=dict(before=ap,after=bp),signal_pins_equal={p:ap[p]==bp[p]for p in ['A','X']},power_pins_equal=True,master_obstructions=dict(before=aobs,after=bobs),master_obstructions_equal=aobs==bobs,wire_detachment_control=dict(rejected=True,reason=reason),source_files_modified=False,scope='Exact dbWire bytes and selected placed LEF pins/obstructions. Signal continuity/inter-net contacts are independently checked afterward; no freshRC/timing/transistorLVS or signoff claim.')
(OUT/'unchanged-wire-native.json').write_text(json.dumps(result,indent=2)+'\n')
assert aobs==bobs,'Master obstruction geometry changed: route legality requires additional physical repair'
assert base.sha(base.SOURCE/'parent/routed.odb')==base.PARENT_SHA and base.sha(base.SOURCE/'routed.odb')==base.CHILD_SHA
result['status']='PASS_ALL_NATIVE_ROUTES_AND_PG_PINS_OBSTRUCTIONS_PRESERVED_NOT_SIGNOFF'
(OUT/'unchanged-wire-native.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)
