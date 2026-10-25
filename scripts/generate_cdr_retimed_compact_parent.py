#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Regenerate all PD394 wires and supply shunts around four compact samplers."""
import argparse,json
from pathlib import Path
import generate_cdr_retimed_parent_v2 as placement
import generate_cdr_retimed_parent_v3 as supply
import cdr_retimed_compact_parent_plan as plan
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_retimed_pd394_compact_supply_v1'
def generate(out):
    assert placement.TOP=='nssoc_cdr_retimed_pd394_layout_v2'
    assert supply.TOP=='nssoc_cdr_retimed_pd394_layout_v3'
    # Explicit physical-identity adaptation only. Original routing and shunt
    # functions execute against real new child geometry; no layout is scaled.
    placement.TOP='nssoc_cdr_retimed_pd394_compact_base_v1'
    placement.TYPES=plan.TYPES;placement.build=plan.build;placement.verify=plan.verify
    supply.TOP=TOP;supply.TYPES=plan.TYPES
    supply.generate(out)
    p=out/'layout/result.json';r=json.loads(p.read_text())
    assert sum(v['kind']=='sampler'for v in r['placements'].values())==4
    assert r['primitive_census']==plan.build()['primitive_census']
    r['inputs'].update({str(x):placement.sha(x)for x in [Path(__file__),Path(plan.__file__)]})
    r['compact_sampler_integration']=dict(count=4,physical_top=plan.TYPES['sampler']['top'],
        source_run=39090817026,unchanged_frozen_device_graph=True,
        routing_regenerated_from_actual_child_pins=True,old_rc_reusable=False,
        loaded_wave_accepted=False,qualified_pex=False,full_phy_accepted=False)
    p.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
