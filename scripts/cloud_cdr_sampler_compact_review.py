#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only source-bound diagnosis of the rejected compact sampler."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-compact-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        paths=('layout/result.json','layout/schematic.cir','physical/lvs/extracted.cir','physical/lvs/deck.log','physical/lvs/audit.json')
        r,proof=reports.restore_report('cdr-sampler-compact-v1',39090257244,
            'ad1c1ff9a6102eb9fd36bf511f610e086aa1871d9d1db3c4c5bab9777a6d1ee1',
            '515655d23aaa63f7209e65853ea9e8f48601022071c201385abf668cf029b0bd',OUT/'source',paths)
        assert r['source_head']=='6a9a5f6d2ece8ceb6bfe36b46075a61126a609ba'
        steps={s['name']:s for s in r['physical']['steps']}
        assert steps['drc']['measurement']['status']=='PASS'and steps['lvs']['audit']['status']=='FAIL'
        g=json.loads((OUT/'source/layout/result.json').read_text())
        collisions=[]
        for via in g['vias']:
            if via['net']=='SUB'and via['bottom']==1 and via['top']==4:
                x,y=via['center_um']
                for route in g['routes']:
                    # Exact center-line coincidence in the same M4 routing layer.
                    if abs(x-route['escape_lane_um'])<1e-6:
                        collisions.append(dict(tap_center_um=[x,y],device=route['device'],net=route['net'],escape_y_um=route['escape_y_um'],escape_lane_um=route['escape_lane_um']))
        assert collisions,'Need an evidenced diagnosis, not an arbitrary spacing change'
        text=(OUT/'source/physical/lvs/extracted.cir').read_text()
        result.update(status='COMPLETE_REJECTED_NATIVE_LAYOUT_DIAGNOSIS',source=proof,
            coordinate_collisions=collisions,native_extracted_netlist=text,
            reference_netlist=(OUT/'source/layout/schematic.cir').read_text(),
            native_lvs_audit=json.loads((OUT/'source/physical/lvs/audit.json').read_text()),
            original_geometry=g,repair_adopted=False,
            interpretation='Exact tap/signal M4 centerlines coincide; source-defined vertical routes overlap in y. Original native LVS independently rejects connectivity. Move taps to unused M4 lanes, then rerun complete original physical gates and new RC.')
        print('COLLISIONS',json.dumps(collisions));print('EXTRACTED',text)
        print('DECK_TAIL',(OUT/'source/physical/lvs/deck.log').read_text()[-10000:])
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
