#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Private Magic area-product promotion; native device/RC acceptance required.

Promote an operand BEFORE multiplication in all eight ResMakeRes.c geometric
area calculations. Keep native float storage, coordinate/struct ABI, resistance
equations, topology, capacitance totals and PDK untouched. No clipping.
"""
import argparse
import hashlib
import json
from pathlib import Path

EDITS = (
    ('height * (RIGHT(tile) - LEFT(tile))', '(double)height * (RIGHT(tile) - LEFT(tile))'),
    ('height * (p2->br_loc.p_x - LEFT(tile))', '(double)height * (p2->br_loc.p_x - LEFT(tile))'),
    ('((p2->br_loc.p_x - p1->br_loc.p_x) * height) / 2', '((double)(p2->br_loc.p_x - p1->br_loc.p_x) * height) / 2'),
    ('height * (RIGHT(tile) - p2->br_loc.p_x)', '(double)height * (RIGHT(tile) - p2->br_loc.p_x)'),
    ('width * (TOP(tile) - BOTTOM(tile))', '(double)width * (TOP(tile) - BOTTOM(tile))'),
    ('width * (p2->br_loc.p_y - BOTTOM(tile))', '(double)width * (p2->br_loc.p_y - BOTTOM(tile))'),
    ('((p2->br_loc.p_y - p1->br_loc.p_y) * width) / 2', '((double)(p2->br_loc.p_y - p1->br_loc.p_y) * width) / 2'),
    ('width * (TOP(tile) - p2->br_loc.p_y)', '(double)width * (TOP(tile) - p2->br_loc.p_y)'),
)
# Filled from the exact frozen private-v3 parent; no source discovery/substitution.
SOURCE_SHA = '90aec7e13bfdc4b6c14aabc8dfdf77dd2e0752d03f9ad9e919e402a602e025f0'


def pin(path):
    path=Path(path)
    with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(bytes=path.stat().st_size,sha256=digest)


def transform(text):
    if hashlib.sha256(text.encode()).hexdigest()!=SOURCE_SHA:
        raise ValueError('Exact native ResMakeRes.c required')
    for old,new in EDITS:
        if text.count(old)!=1:raise ValueError('Missing/duplicate native area-product site')
        text=text.replace(old,new)
    return text


def patch(source,out):
    source=Path(source);out=Path(out)
    if out.exists():raise ValueError('Fresh private patch output required')
    old=source/'resis/ResMakeRes.c';header=source/'resis/resis.h'
    before={str(p):pin(p) for p in [old,header]};text=transform(old.read_text())
    out.mkdir(parents=True);(out/'ResMakeRes.c').write_text(text)
    if any(pin(p)!=v for p,v in before.items()):raise ValueError('Parent changed during patch')
    result=dict(status='PRIVATE_AREA_PRODUCT_PATCH_NATIVE_ACCEPTANCE_PENDING',method=pin(__file__),
        inputs=before,outputs={'ResMakeRes.c':pin(out/'ResMakeRes.c')},changed_products=8,
        struct_or_field_type_changed=False,resistance_formula_changed=False,geometry_changed=False,
        cap_clipping_or_deletion=False,installed_runtime_changed=False,native_accepted=False)
    (out/'patch.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();print(patch(a.source,a.out)['status'])


if __name__=='__main__':main()
