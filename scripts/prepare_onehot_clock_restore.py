#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare and audit one actual historical clock route in the latest routed chip."""
import hashlib,json,os,re
from pathlib import Path
import odb
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-restore'
NET='clknet_3_5_0_pcie_clk_i'
ODB='run/2-openroad-detailedrouting/soc_top.odb'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    db=odb.dbDatabase.create();odb.read_db(db,str(p));return db,db.getChip().getBlock()
def term(t):
    inst=t.getInst()
    return [inst.getName(),t.getMTerm().getName(),inst.getMaster().getName(),str(t.getIoType()),
       list(inst.getLocation()),str(inst.getOrient()),list(t.getAvgXY())]
def identity(net):
    assert not list(net.getBTerms())
    return dict(name=net.getName(),sigtype=str(net.getSigType()),terminals=sorted(term(t)for t in net.getITerms()),
      rule=net.getNonDefaultRule().getName()if net.getNonDefaultRule()else None)
def boxes(v):
    return sorted((b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())for b in v.getBoxes())
def scan_def(path):
    other=hashlib.sha256();found=[];record=None;inside=False
    with path.open('rb')as f:
        for line in f:
            if line.startswith(b'NETS '):inside=True
            if inside and re.match(rb'^-\s+'+NET.encode()+rb'\s',line):
                assert record is None;record=[]
            if record is not None:
                record.append(line)
                if b';'in line:
                    assert line.count(b';')==1
                    found.append(b''.join(record).decode());record=None
            else:other.update(line)
            if line.startswith(b'END NETS'):inside=False
    assert record is None and len(found)==1
    return found[0],other.hexdigest()
def export(block,name):
    path=OUT/name;odb.write_def(block,str(path))
    return scan_def(path)
def main():
    pins=json.loads((OUT/'sources.json').read_text())
    for tag,pin in pins.items():assert sha(OUT/tag/ODB)==pin['odb_sha256']
    mode=os.environ.get('NSSOC_CLOCK_RESTORE_MODE','prepare')
    if mode=='prepare':
        olddb,old=load(OUT/'before'/ODB);db,block=load(OUT/'after'/ODB)
        a,b=old.findNet(NET),block.findNet(NET);assert a and b
        assert identity(a)==identity(b),'Changed actual clock pin, position, master, direction or NDR'
        assert a.getWire().getLength()<b.getWire().getLength()
        # Every physical via name used by the imported route must already mean
        # exactly the same layer/cut geometry in the recipient database.
        d=odb.dbWireDecoder();d.begin(a.getWire());vias={}
        while True:
            op=d.next()
            if op==d.END_DECODE:break
            if op in (d.VIA,d.TECH_VIA):
                v=d.getVia()if op==d.VIA else d.getTechVia()
                other=block.findVia(v.getName())if op==d.VIA else db.getTech().findVia(v.getName())
                assert other is not None,('Missing native via definition',v.getName())
                assert boxes(v)==boxes(other),('Different native via geometry',v.getName())
                vias[v.getName()]=boxes(v)
        original_statement,_=export(old,'old.def')
        current_statement,unrelated=export(block,'current.def')
        assert original_statement.count('+ ROUTED')==1 and '+ FIXED'not in original_statement
        replacement=original_statement.replace('+ ROUTED','+ FIXED')
        patch='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN '+block.getName()+' ;\nUNITS DISTANCE MICRONS '+str(block.getDbUnitsPerMicron())+' ;\nNETS 1 ;\n'+replacement+'END NETS\nEND DESIGN\n'
        (OUT/'clock-patch.def').write_text(patch)
        plan=dict(status='PREPARED_NATIVE_CLOCK_WIRE_TRANSFER_REQUIRES_IMPORT_PROOF',net=NET,
           old_length_dbu=a.getWire().getLength(),current_length_dbu=b.getWire().getLength(),
           native_pin_identity=identity(b),native_via_definitions=vias,
           current_unrelated_def_sha256=unrelated,expected_statement=replacement,
           current_statement=current_statement,patch_sha256=sha(OUT/'clock-patch.def'),
           native_dimensions=dict(dbu_per_um=block.getDbUnitsPerMicron()),
           full_timing_complete=False,accepted=False)
        # Remove only this wire. All other native routing remains present.
        odb.dbWire.destroy(b.getWire());assert b.getWire()is None
        odb.write_db(db,str(OUT/'import-base.odb'))
        plan['import_base_sha256']=sha(OUT/'import-base.odb')
        (OUT/'transfer-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    elif mode=='audit':
        plan=json.loads((OUT/'transfer-plan.json').read_text())
        assert sha(OUT/'clock-patch.def')==plan['patch_sha256']
        db,block=load(OUT/'candidate.odb');net=block.findNet(NET)
        fault=os.environ.get('NSSOC_CLOCK_RESTORE_FAULT','none')
        assert fault in ('none','unrelated_location','wire_type')
        if fault=='unrelated_location':
            inst=block.findInst('clkbuf_3_6_0_pcie_clk_i');assert inst
            x,y=inst.getLocation();inst.setLocation(x+block.getDbUnitsPerMicron(),y)
        elif fault=='wire_type':net.setWireType('ROUTED')
        assert identity(net)==plan['native_pin_identity']
        assert str(net.getWireType())=='FIXED','Clock route is not physically fixed'
        assert net.getWire().getLength()==plan['old_length_dbu']
        actual,unrelated=export(block,'candidate.def'if fault=='none'else 'fault-'+fault+'.def')
        assert unrelated==plan['current_unrelated_def_sha256'],'Unrelated DEF geometry, cells or connectivity changed'
        assert actual.split()==plan['expected_statement'].split(),'Imported native route differs from original physical route'
        d=odb.dbWireDecoder();d.begin(net.getWire());d.next();assert str(d.getWireType())=='FIXED'
        r=dict(status='PASS_NATIVE_SINGLE_CLOCK_ROUTE_TRANSFER_REQUIRES_DRC_RC_AND_STA',
           net=NET,source_pin_positions_unchanged=True,all_unrelated_def_content_unchanged=True,
           original_clock_route_restored_exactly=True,physical_via_definitions_exact=True,
           length_before_um=plan['current_length_dbu']/block.getDbUnitsPerMicron(),
           length_after_um=net.getWire().getLength()/block.getDbUnitsPerMicron(),
           candidate_odb_sha256=sha(OUT/'candidate.odb'),candidate_def_sha256=sha(OUT/'candidate.def'),
           fixed_scope='Only actual clock net route is fixed for physical legalization; no timing constraint changed.',
           routing_drc_passed=False,final_timing_complete=False,accepted=False)
        (OUT/'transfer-proof.json').write_text(json.dumps(r,indent=2)+'\n')
    else:raise AssertionError(mode)
if __name__=='__main__':main()
