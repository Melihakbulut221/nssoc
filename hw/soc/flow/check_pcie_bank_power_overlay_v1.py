#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check complete native overlay geometry/graph and export wire-only material.

This does not run or accept extracted RC or powered operation. All old real
terminal points and finite body devices must remain; no connectivity by labels.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import make_pcie_bank_power_overlay_v1 as method
from audit_klayout_lvs import assess, read_pairs


def check_drc(path):
    root=ET.parse(path).getroot()
    if root.findtext('top-cell')!=method.TOP or len(root.findall('.//category/name'))!=560:
        raise ValueError('Incomplete/wrong native main DRC')
    items=root.findall('.//item')
    if items:raise ValueError('Native DRC violations retained: '+str(Counter(x.findtext('category') for x in items)))


def canonical_anchors(anchors):
    rows=anchors['anchors'];labels=[r['label'] for r in rows]
    if len(rows)!=804 or len(set(labels))!=804:
        raise ValueError('Complete804actualterminal/publicpoint census required')
    if Counter(r['kind'] for r in rows)!=dict(INTRINSIC_DEVICE_TERMINAL_REFERENCE=748,PUBLIC_PORT_REFERENCE=56):
        raise ValueError('Actual point role census differs')
    if len(anchors['unmodeled_body_well_terminals'])!=313:
        raise ValueError('Body/well inventory differs')
    return rows


def component_contract(probed, anchors):
    rows=canonical_anchors(anchors);mapping={};reverse={}
    if set(probed)!={r['label'] for r in rows}:raise ValueError('Missing real probe')
    for r in rows:
        old=r['wire_component'];new=probed[r['label']]
        if new is None:raise ValueError('Actual metal terminal is disconnected')
        if old in mapping and mapping[old]!=new:raise ValueError('Original conductor split')
        if new in reverse and reverse[new]!=old:raise ValueError('Distinct original conductors shorted')
        mapping[old]=new;reverse[new]=old
    if len(mapping)!=128 or len(reverse)!=128:raise ValueError('Complete128component bijection required')
    return mapping


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('layout','native','original_gds','original_native','anchors','out'):
        ap.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() or not str(a.out.resolve()).startswith('/dev/shm/nssoc-power-overlay-'):
        ap.error('Fresh bounded output required')
    if method.pin(a.original_gds)['sha256']!=method.PINS['gds']:
        raise ValueError('Frozen original GDS changed')
    if method.pin(a.anchors)['sha256']!='43af0aeceedd31327aa73e20710288811205aa4dd72c1b2432736ba91e010b8d':
        raise ValueError('Frozen real terminal witness changed')
    generated=json.loads((a.layout/'result.json').read_text())
    for path,expected in generated['inputs'].items():
        if method.pin(path)!=expected:raise ValueError('Generator input changed: '+path)
    for name,expected in generated['outputs'].items():
        if method.pin(a.layout/name)!=expected:raise ValueError('Generated output changed')
    native=json.loads((a.native/'result.json').read_text())
    if native['status']!='COMPLETE_NATIVE_DECKS_REQUIRE_RAW_VERDICT_REVIEW':raise ValueError('Native deck completion missing')
    for row in native['runs']:
        if row['returncode']!=0:raise ValueError('Native deck failure')
        for path,expected in row['deck_inputs'].items():
            if method.pin(path)!=expected:raise ValueError('Native deck dependency changed')
        for name,expected in row['outputs'].items():
            if method.pin(a.native/row['kind']/name)!=expected:raise ValueError('Native output changed')
    check_drc(a.native/'drc/drc.lyrdb')
    diagnostics=[];pairs=read_pairs(a.native/'lvs_flat/result.lvsdb',diagnostics)
    verdict=assess(pairs,method.TOP,(a.native/'lvs_flat/deck.log').read_text(),diagnostics)
    if verdict['status']!='PASS within comparison scope' or len(pairs)!=1:
        raise ValueError('Strict native full graph mismatch')
    if pairs[0]['layout_devices_recursive']!=351 or pairs[0]['schematic_devices_recursive']!=351:
        raise ValueError('Unsimplified351device census changed')
    import pya
    old=pya.Layout();old.read(str(a.original_gds));oc=old.top_cell()
    new=pya.Layout();new.read(str(a.layout/(method.TOP+'.gds')));nc=new.cell(method.TOP)
    if old.dbu!=.001 or new.dbu!=old.dbu:raise ValueError('Native geometry grid differs')
    layers=set(old.layer_infos())|set(new.layer_infos());geometry=[];regions={}
    for info in sorted(layers,key=lambda x:(x.layer,x.datatype)):
        before=pya.Region(oc.begin_shapes_rec(old.layer(info))).merged()
        after=pya.Region(nc.begin_shapes_rec(new.layer(info))).merged()
        allowed=info.datatype==0 and info.layer in method.METALS+method.VIAS
        if not (before-after).is_empty() or (not allowed and not (after-before).is_empty()):
            raise ValueError('Original device/pin/body/routing material changed')
        if not after.is_empty():geometry.append(dict(layer=str(info),before_area_nm2=before.area(),after_area_nm2=after.area(),added_area_nm2=(after-before).area()))
        if allowed:regions[info.layer]=after
    # A fresh purely geometric extractor proves every actual anchor and public
    # pad is still on its original distinct conductor, without adding aliases.
    e=pya.LayoutToNetlist('OVERLAY_WIRES',new.dbu)
    for layer,reg in regions.items():e.register(reg,'gds_'+str(layer));e.connect(reg)
    for lo,via,hi in zip(method.METALS,method.VIAS,method.METALS[1:]):
        e.connect(regions[lo],regions[via]);e.connect(regions[via],regions[hi])
    e.extract_netlist();c=e.netlist().top_circuit()
    if len(list(c.each_net()))!=128 or list(c.each_device()):raise ValueError('Wire-only128conductor inventory differs')
    anchors=json.loads(a.anchors.read_text());probed={}
    for r in canonical_anchors(anchors):
        n=e.probe_net(e.layer_by_name('gds_'+str(r['metal'])),pya.Point(*r['point_dbu']))
        probed[r['label']]=None if n is None else n.cluster_id
    mapping=component_contract(probed,anchors)
    # The actual native device parameters/body identities participate in the
    # strict complete LVS above; confirm all original geometry-device census.
    model_counts=[];native_ports=[]
    for path in (a.original_native,a.native/'lvs_flat/result.lvsdb'):
        lvs=pya.LayoutVsSchematic();lvs.read(str(path));c=lvs.netlist().top_circuit()
        model_counts.append(dict(Counter(d.device_class().name for d in c.each_device())))
        native_ports.append(sorted(p.name() for p in c.each_pin()))
    if model_counts[0]!=model_counts[1] or native_ports[0]!=native_ports[1] or len(native_ports[1])!=56:
        raise ValueError('Complete native device model/port census differs')
    a.out.mkdir();wg=pya.Layout();wg.dbu=.001;wc=wg.create_cell('bank_wires')
    for layer,reg in regions.items():wc.shapes(wg.layer(layer,0)).insert(reg)
    wg.write(str(a.out/'wires.gds'));e.write(str(a.out/'wires.l2n'))
    # Original semantic component IDs and all exact point coordinates remain.
    # Their new geometry ownership was independently proven above.
    updated=dict(anchors);updated['source_geometry']=method.pin(a.out/'wires.gds')
    updated['inputs']={str(p):method.pin(p) for p in [Path(__file__),Path(method.__file__),a.original_gds,a.anchors,a.layout/(method.TOP+'.gds'),a.native/'lvs_flat/result.lvsdb',a.out/'wires.gds']}
    updated['overlay_component_bijection']=mapping
    (a.out/'anchors.json').write_text(json.dumps(updated,indent=2)+'\n')
    record=dict(status='PASS_GEOMETRY_STRICT351DEVICE56PORT_LVS804ANCHORS128CONDUCTORS_NO_RC_YET',
        inputs=updated['inputs'],native_source=method.pin(a.native/'result.json'),drc_categories=560,drc_violations=0,lvs=verdict,
        native_device_counts=model_counts[1],native_ports=native_ports[1],geometry=geometry,
        component_bijection=mapping,probed_actual_points=probed,unchanged_finite_contacts=109,
        unmodeled_body_well_terminals=313,full_pex_qualified=False,powered_bank_accepted=False,
        outputs={p.name:method.pin(p) for p in a.out.iterdir() if p.is_file()})
    (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'])


if __name__=='__main__':main()
