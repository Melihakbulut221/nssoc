#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound physical pin/route compatibility; retain failed equality gate."""
import argparse,gzip,json,math
from pathlib import Path

def intersects(a,b,positive=False):
    if a[0]!=b[0]:return False
    dx=min(a[3],b[3])-max(a[1],b[1]);dy=min(a[4],b[4])-max(a[2],b[2])
    return dx>0 and dy>0 if positive else dx>=0 and dy>=0

def power_errors(item):
    errors=[]
    for pin in ('VDD','VSS'):
        net=item['pin_nets'][pin];shapes=item['pins'][pin]
        for shape in shapes:
            if not any(g['net']==net and intersects(shape,g['shape'],True)for g in item['local_planar_grid']):errors.append(dict(kind='missing_positive_planar_power_contact',pin=pin,shape=shape))
            for g in item['local_planar_grid']:
                if g['net']!=net and intersects(shape,g['shape']):errors.append(dict(kind='opposite_power_contact',pin=pin,shape=shape,grid=g))
    return errors

def collisions(row,item,spacing):
    errors=[]
    for s in row['shapes']:
        r=[s['layer'],*s['box']]
        for pin in ('VDD','VSS'):
            for pg in item['pins'][pin]:
                if intersects(r,pg):errors.append(dict(kind='signal_power_contact',net=row['net'],signal=s,power_pin=pin,power_shape=pg))
        if s['kind']=='pin':continue # Library-internal spacing is a separate GDS gate.
        for o in item['obstructions']:
            if r[0]!=o[0]:continue
            if intersects(r,o):errors.append(dict(kind='route_obstruction_contact',net=row['net'],signal=s,obstruction=o));continue
            dx=max(o[1]-r[3],r[1]-o[3],0);dy=max(o[2]-r[4],r[2]-o[4],0)
            required=spacing[r[0]]
            if dx*dx+dy*dy<required*required:errors.append(dict(kind='default_spacing_to_obstruction',net=row['net'],signal=s,obstruction=o,gap_dbu=math.sqrt(dx*dx+dy*dy),required_dbu=required))
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);args=p.parse_args();out=args.directory
    data=json.loads((out/'pin-compatibility-native.json').read_text());wire=json.loads((out/'unchanged-wire-native.json').read_text())
    assert data['source_unchanged']and data['candidate_sha256']==wire['candidate_odb_sha256']
    assert wire['all114103net_wire_records_equal']and wire['wire_detachment_control']['rejected']
    assert not wire['power_pins_equal']and not wire['master_obstructions_equal'],'This new diagnostic binds the actual previously rejected cell geometry'
    item=data['instances']['candidate'];parent=data['instances']['parent'];spacing=data['minimum_spacing_dbu']
    faults=[]
    bad=json.loads(json.dumps(item));bad['local_planar_grid']=[g for g in bad['local_planar_grid']if g['net']!=bad['pin_nets']['VDD']]
    assert power_errors(bad);faults.append('actual_local_VDD_grid_removed')
    bad=json.loads(json.dumps(item));bad['local_planar_grid'].append(dict(net=bad['pin_nets']['VSS'],shape=item['pins']['VDD'][0]))
    assert power_errors(bad);faults.append('actual_VDD_connected_to_wrong_rail')
    pg=item['pins']['VDD'][0];fake=dict(net='fault_signal',shapes=[dict(layer=pg[0],box=pg[1:],kind='wire')]);assert any(e['kind']=='signal_power_contact'for e in collisions(fake,item,spacing));faults.append('route_at_actual_power_pin')
    obs=item['obstructions'][0];fake=dict(net='fault_signal',shapes=[dict(layer=obs[0],box=obs[1:],kind='wire')]);assert any(e['kind']=='route_obstruction_contact'for e in collisions(fake,item,spacing));faults.append('route_at_actual_obstruction')
    controls=dict(actual_geometry_faults_rejected=faults)
    result=dict(status='RUNNING',accepted=False,controls=controls,candidate_sha256=data['candidate_sha256'],original_pin_and_obstruction_equality_gate_passed=False,source_unchanged=data['source_unchanged'],candidate_power_errors=power_errors(item),parent_power_errors=power_errors(parent),candidate_route_failures=[],parent_route_failures=[],nets_checked=0,shapes_checked=0)
    try:
        with gzip.open(out/'signal-geometry.jsonl.gz','rt')as stream:
            for line in stream:
                row=json.loads(line);result['nets_checked']+=1;result['shapes_checked']+=len(row['shapes'])
                # Bounding rejection only accelerates the exact same checks.
                near=[]
                for s in row['shapes']:
                    if s['layer']!='Metal1':continue
                    b=s['box']
                    if b[0]<=2774920 and b[2]>=2769080 and b[1]<=1951700 and b[3]>=1945480:near.append(s)
                if near:
                    local=dict(net=row['net'],shapes=near)
                    result['candidate_route_failures'].extend(collisions(local,item,spacing))
                    result['parent_route_failures'].extend(collisions(local,parent,spacing))
        assert set(r[0]for v in (item,parent)for rows in [*v['pins'].values(),v['obstructions']]for r in rows)=={'Metal1'}
        assert result['nets_checked']==113796
        assert not result['candidate_power_errors']and not result['parent_power_errors'],'Planar PG connectivity failure'
        assert not result['candidate_route_failures'],'Actual candidate routing contacts or default spacing failed'
        result['status']='COMPLETE_ACTUAL_PIN_ROUTE_COMPATIBILITY_SCREEN_NOT_SIGNOFF'
    except BaseException as e:result.update(status='FAIL_ACTUAL_PIN_ROUTE_COMPATIBILITY',error=repr(e));raise
    finally:
        result['scope']='Selected replacement-cell actual planar PG contacts; signal-to-PG shorts; all exported signal route metal versus selected LEF obstructions and default layer spacing. Original identical-shape gate stays failed. No full PG graph, via CUT/enclosure, conditional foundry spacing, internal GDS/LVS or final timing acceptance.'
        (out/'pin-compatibility.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('candidate_route_failures','parent_route_failures')}),flush=True)
if __name__=='__main__':main()
