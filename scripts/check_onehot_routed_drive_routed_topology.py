#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check all original native cells, geometry, pins and nets after actual ECO routing."""
import copy,json,os
from pathlib import Path
import odb
from check_onehot_round4_saved_topology import capture,digest

def full_capture(path):
    result=capture(path);db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock()
    result['geometry']={i.getName():dict(location=list(i.getLocation()),origin=list(i.getOrigin()),orientation=str(i.getOrient()))for i in block.getInsts()}
    result['port_geometry']={p.getName():[(b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())for pin in p.getBPins()for b in pin.getBoxes()]for p in block.getBTerms()}
    odb.dbDatabase.destroy(db);return result

def compare(before,after):
    assert before['ports']==after['ports']and before['port_geometry']==after['port_geometry']
    assert before['nets']==after['nets']
    assert set(before['instances'])<=set(after['instances'])
    for name,row in before['instances'].items():
        assert row==after['instances'][name],('Changed original master/pin',name)
        assert before['geometry'][name]==after['geometry'][name],('Changed original geometry',name)
    added={n:r for n,r in after['instances'].items()if n not in before['instances']}
    for name,row in added.items():
        assert row['master']=='sg13g2_antennanp',('Non-diode insertion',name)
        signal={k:v for k,v in row['pins'].items()if v['sig']not in ('POWER','GROUND')}
        assert set(signal)=={'A'}and signal['A']['io']=='INPUT'and signal['A']['net']in before['nets']
    return dict(retained_instances=len(before['instances']),added_diode_count=len(added),added_diodes=added,original_masters_geometry_all_pins_nets_ndrs_ports_preserved=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    a=Path(os.environ['NSSOC_TOPOLOGY_BEFORE']);b=Path(os.environ['NSSOC_TOPOLOGY_AFTER']);out=Path(os.environ['NSSOC_TOPOLOGY_OUT'])
    pins={str(p):digest(p)for p in (a,b,Path(__file__))};before=full_capture(a);after=full_capture(b)
    assert len(before['instances'])==148871
    proof=compare(before,after);first=next(iter(before['instances']));faults=[]
    for label in ('changed_master','changed_pin','changed_location','non_diode_addition'):
        wrong=dict(after);wrong['instances']=dict(after['instances']);wrong['geometry']=dict(after['geometry'])
        if label=='non_diode_addition':wrong['instances']['NSSOC_ILLEGAL_ADDITION']=dict(master='ILLEGAL',pins={})
        elif label=='changed_location':
            wrong['geometry'][first]=copy.deepcopy(after['geometry'][first]);wrong['geometry'][first]['location'][0]+=1
        else:
            wrong['instances'][first]=copy.deepcopy(after['instances'][first])
            if label=='changed_master':wrong['instances'][first]['master']='ILLEGAL'
            else:
                pin=next(iter(wrong['instances'][first]['pins']));wrong['instances'][first]['pins'][pin]['net']='ILLEGAL'
        try:compare(before,wrong)
        except AssertionError:faults.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(faults)==4 and all(digest(p)==v for p,v in pins.items())
    out.write_text(json.dumps(dict(status='PASS_NATIVE_NEAR_DRIVER_BUFFER_ROUTED_TOPOLOGY_AND_GEOMETRY_NOT_LVS',proof=proof,rejected=faults,inputs=pins),indent=2)+'\n')
if __name__=='__main__':main()
