#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate an actual wider global AVSS rail; preserve native cells and circuit."""
import argparse,hashlib,json,re
from pathlib import Path
import generate_cdr_retimed_avss256_base as placement
import generate_cdr_retimed_parent_v3 as supply
import cdr_retimed_compact_parent_plan as plan
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_pd394_compact_avss256_v1'
def generate(out):
    manifest=ROOT/'scripts/cdr-avss256-placement-delta.json'
    delta=json.loads(manifest.read_text());raw=(ROOT/delta['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==delta['baseline_sha256']
    text=raw.decode()
    for e in delta['edits']:
        assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
    candidate=(ROOT/delta['candidate_path']).read_bytes()
    assert candidate==text.encode() and hashlib.sha256(candidate).hexdigest()==delta['candidate_sha256']
    assert placement.TOP=='nssoc_cdr_pd394_avss256_base_v1'
    assert supply.TOP=='nssoc_cdr_retimed_pd394_layout_v3'
    placement.TYPES=plan.TYPES;placement.build=plan.build;placement.verify=plan.verify
    supply.base=placement;supply.TOP=TOP;supply.TYPES=plan.TYPES
    supply.generate(out)
    p=out/'layout/result.json';r=json.loads(p.read_text())
    prior=json.loads((ROOT/'docs/evidence/cdr-retimed-compact-parent-physical-pass-20261018.json').read_text())['report']['layout']
    def box(s):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)))
    def shifted(a,b):
        aa,bb=box(a),box(b)
        return all(abs(x-y-z)<1e-6 for x,y,z in zip(aa,bb,[192,0,192,0],strict=True))
    assert r['primitive_census']==prior['primitive_census']==plan.build()['primitive_census']
    assert r['source_plan']==prior['source_plan']
    assert r['routing_changes']['new_order']==prior['routing_changes']['new_order']
    for tag,item in r['placements'].items():
        old=prior['placements'][tag];assert item['kind']==old['kind'] and shifted(item['bbox_um'],old['bbox_um'])
        assert set(item['ports'])==set(old['ports'])
        assert all(shifted(v,old['ports'][k])for k,v in item['ports'].items())
    assert r['child_geometry_conservation']==prior['child_geometry_conservation']
    assert len(r['routes'])==len(prior['routes'])
    signals=0
    for item,old in zip(r['routes'],prior['routes'],strict=True):
        assert {k:v for k,v in item.items()if k!='box_um'}=={k:v for k,v in old.items()if k!='box_um'}
        if item['net']not in ('avdd','avss','sub'):
            assert shifted(item['box_um'],old['box_um']);signals+=1
    r['inputs'].update({str(x):placement.sha(x)for x in [Path(__file__),Path(plan.__file__),manifest,ROOT/delta['baseline_path'],ROOT/'docs/evidence/cdr-retimed-compact-parent-physical-pass-20261018.json']})
    r['avss256_candidate']=dict(global_avss_m6_width_before_um=64,global_avss_m6_width_after_um=256,
        child_translation_um=[192,0],all_child_drawings_preserved=True,intermacro_signal_routes_translated_unchanged=signals,
        public_signal_feeds_regenerated=True,public_supply_pin_width_um=64,original_supply_via_arrays_preserved=True,
        source_delta=delta,old_rc_reusable=False,loaded_wave_accepted=False,qualified_pex=False,full_phy_accepted=False)
    p.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
