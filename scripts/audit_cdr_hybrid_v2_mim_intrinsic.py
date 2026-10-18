#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Require eleven actual MIM identities in source, replacement and both SPICE views."""
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def require(ok,message):
    if not ok:raise ValueError(message)
def validate_mim(rows,rep,before,after,original,owners,anchors):
    binding=json.loads((ROOT/'docs/evidence/cdr-retimed-hybrid-v2-binding-pass-20261018.json').read_text())['report']['binding']
    terminal={(r['device'],r['terminal']):r for r in anchors['rows']};expected=Counter()
    for d in binding['devices']:
        if d['model']!='cap_cmim':continue
        pair=tuple(terminal[d['native_id'],t]['wire_component']for t in ('mim_top','mim_btm'))
        params=tuple((k,Decimal(d['native_parameters'][k])*Decimal('1e-6'))for k in ('l','w'))
        expected[pair,'cap_cmim',params]+=1
    require(len(expected)==sum(expected.values())==11,'Native MIM census changed')
    def norm(devices,mapping):
        result=Counter()
        for ns,model,params in devices:
            require(model=='cap_cmim'and len(ns)==2 and all(n in mapping for n in ns)and {k for k,v in params}=={'w','l'},'Unexpected native MIM model/terminal/parameter')
            result[tuple(mapping[n]for n in ns),model,params]+=1
        return result
    require(norm(before['devices'],original)==expected,'Baseline native MIM identity/order/value changed')
    require(norm(after['devices'],owners)==expected,'Export native MIM identity/order/value changed')
    require([r for r in rows if r[0]=='parameters']==[['parameters','cap_cmim','w=w','l=l']],'Native MIM parameter declaration changed')
    sources={};source_devices=[]
    for r in rows:
        if r[0]!='device':continue
        require(len(r)==16 and r[:3]==['device','csubckt','cap_cmim']and r[9]=='None','Unexpected source intrinsic device record')
        box=tuple(map(int,r[3:7]));require(box not in sources,'Duplicate native MIM location')
        p=dict(x.split('=')for x in r[7:9]);require(set(p)=={'w','l'}and r[10]in original and r[13]in original,'Native MIM source parameter/terminal changed')
        signature=((original[r[10]],original[r[13]]),'cap_cmim',tuple((k,Decimal(p[k])*Decimal('5e-9'))for k in ('l','w')))
        sources[box]=signature;source_devices.append(r)
    require(Counter(sources.values())==expected,'Source native MIM identity/order/value changed')
    seen=set();replacement_devices=[]
    for r in rep:
        if r[0]!='device':continue
        require(len(r)==14 and r[:3]==['device','csubckt','cap_cmim']and r[7]=='None','Unexpected replacement intrinsic device record')
        box=tuple(map(int,r[3:7]));require(box in sources and box not in seen,'Replacement native MIM location changed');seen.add(box)
        require(r[8]in owners and r[11]in owners and (owners[r[8]],owners[r[11]])==sources[box][0],'Replacement native MIM terminal ownership changed')
        replacement_devices.append(r)
    require(seen==set(sources),'Missing replacement native MIM device')
    return dict(status='PASS_ELEVEN_NATIVE_MIM_SOURCE_REPLACEMENT_BASELINE_EXPORT_IDENTITIES',devices=11,source_records=source_devices,replacement_records=replacement_devices,parameter_source='Native source w/l in5nm units, exact match to KLayout native dimensions; explicit PDK subcircuit uses w/l.',replacement_perimeter_metadata_used_for_model=False,intrinsic_devices_excluded_from_wire_C_matrix=True,full_pex_qualified=False)
