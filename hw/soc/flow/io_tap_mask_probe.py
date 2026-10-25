#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pinned-runtime geometry controls and captured/native-mask attribution only."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def native_module():
    import klayout.db as db
    require(db.__version__ == '0.30.7', 'Expected pinned KLayout 0.30.7')
    return db


def controls(path):
    db=native_module()
    rectangle=db.Region(db.Box(0,0,80000,300))
    require((rectangle.area(),rectangle.perimeter()) == (24000000,160600), 'Rectangle control')
    ring=db.Region(db.Box(0,0,10000,10000))-db.Region(db.Box(2000,2000,4000,4000))
    require((ring.area(),ring.perimeter()) == (96000000,48000), 'Hole control')
    a=db.Region(db.Box(0,0,10000,10000));b=db.Region(db.Box(5000,0,15000,10000))
    require((a&b).area() == 50000000 and (a|b).area() == 150000000, 'Overlap control')
    require(((a|b)^(a+b).merged()).is_empty(), 'XOR control')
    # Exercise the exact polygon-string interchange used by the Ruby exporter.
    restored=db.Region()
    for poly in ring.each_merged():
        restored.insert(db.Polygon.from_s(poly.to_s()))
    require((ring^restored).is_empty(), 'Polygon interchange control')
    points=[[0,0],[10000,0],[10000,10000],[0,10000],[0,0],[2000,0],
            [2000,2000],[2000,4000],[4000,4000],[4000,2000],[2000,2000],[2000,0],[0,0]]
    bridged=db.Region(db.Polygon([db.Point(*p) for p in points])).merged()
    require(bridged.area()==96000000 and bridged.perimeter()==48000 and (bridged^ring).is_empty(),
            'Bridged Q-hole control')
    layout=db.Layout();layout.dbu=0.001
    top=layout.create_cell('CONTROL_TOP');child=layout.create_cell('CONTROL_CHILD');layer=layout.layer(1,0)
    child.shapes(layer).insert(db.Box(0,0,1000,2000))
    top.insert(db.CellInstArray(child.cell_index(),db.Trans(1,False,10000,20000)))
    store=db.DeepShapeStore()
    region=db.Region(db.RecursiveShapeIterator(layout,top,[layer]),store)
    require(region.is_deep(),'Deep hierarchy setup control')
    flattened=db.Region()
    for polygon in region.each_merged():
        flattened.insert(polygon)
    require((flattened^db.Region(db.Box(8000,20000,10000,21000))).is_empty(),
            'Transformed deep export control')
    write(path,dict(status='PASS_NATIVE_MASK_CONTROLS',
                    cases=['rectangle','hole','overlap','xor','bridged_q_hole','transformed_deep_export'],dbu_um=0.001,
                    polygon_interchange_pass=True,klayout_version=db.__version__))


def summary(region):
    region=region.merged()
    polygons=sorted(poly.to_s() for poly in region.each_merged())
    return dict(area_dbu2=region.area(),perimeter_dbu=region.perimeter(),polygons=polygons,
                polygons_sha256=hashlib.sha256(json.dumps(polygons,separators=(',',':')).encode()).hexdigest())


def masks(db,path,mode):
    value=json.loads(path.read_text())
    require(value['status']=='DERIVED_MASKS_ONLY' and value['mode']==mode and value['dbu_um']==0.001,
            'Wrong derivative mode/DBU')
    regions={}
    for name,row in value['masks'].items():
        reg=db.Region()
        for polygon in row['polygons']:
            reg.insert(db.Polygon.from_s(polygon))
        reg.merge()
        require(reg.area()==row['area_dbu2'] and reg.perimeter()==row['perimeter_dbu'],
                'Exported mask measurements differ: '+name)
        regions[name]=reg
    return regions


def captured_regions(db,rows):
    regions=[]
    for row in rows:
        region=db.Region(db.Polygon([db.Point(*p) for p in row['points_dbu']])).merged()
        require(region.area()==int(Decimal(row['area_um2'])*1000000)
                and region.perimeter()==int(Decimal(row['perimeter_um'])*1000),
                'Captured terminal polygon does not reproduce native A/P')
        regions.append(region)
    return regions


def union(db,regions):
    result=db.Region()
    for region in regions:
        result+=region
    return result.merged()


def analyze(output):
    db=native_module()
    result=dict(schema=1,status='PARTIAL_MASK_ATTRIBUTION',native_comparison_repeated=False,
                cell_lvs_accepted=False,full_chip_lvs_accepted=False,manufacturing_approval=False)
    try:
        raw=json.loads((output/'captured-geometry.json').read_text())
        capture={mode:captured_regions(db,raw[mode]) for mode in ('deep','flat')}
        derived={mode:masks(db,output/mode/'masks.json',mode) for mode in ('deep','flat')}
        result['captured_geometry_parameters_reproduced']=sum(map(len,capture.values()))
        result['derivation_to_captured_xor']={mode:summary(derived[mode]['ptap1_tie']^union(db,capture[mode]))
                                            for mode in ('deep','flat')}
        # Strict geometrical identity gates interpretation of copied derivations.
        require(all(row['area_dbu2']==0 for row in result['derivation_to_captured_xor'].values()),
                'Derived TIE geometry differs from the captured native terminal geometry')
        top='sg13g2_IOPadVss'
        def select(mode,cell,area):
            hits=[region for row,region in zip(raw[mode],capture[mode])
                  if row['cell']==cell and Decimal(row['area_um2'])==Decimal(area)]
            require(len(hits)==1,'Ambiguous captured role')
            return hits[0]
        stripe=select('deep',top,'24')
        stripe_flat=select('flat',top,'24')
        box=stripe.bbox()
        require((box.width(),box.height())==(80000,300) and (stripe^stripe_flat).is_empty(),
                'VSS stripe footprint changed')
        result['vss_stripe']=dict(geometry=summary(stripe),bbox_dbu=[box.left,box.bottom,box.right,box.top],
            coverage={mode:{name:dict(covered=summary(stripe&region),uncovered=summary(stripe-region))
                            for name,region in layers.items()} for mode,layers in derived.items()})
        parent=select('deep',top,'5379.0466')
        child=select('deep','sg13g2_DCPDiode','33.5104')
        flat=select('flat',top,'5407.1')
        overlap=parent&child
        united=parent|child
        difference=united^flat
        result['iovss_parent_dcp']=dict(parent=summary(parent),child_transformed=summary(child),
            overlap=summary(overlap),union=summary(united),captured_flat=summary(flat),
            union_minus_flat=summary(united-flat),flat_minus_union=summary(flat-united),xor=summary(difference),
            deep_sum_area_dbu2=parent.area()+child.area(),flat_area_dbu2=flat.area(),
            area_balance_dbu2=parent.area()+child.area()-flat.area(),
            interpretation=('EXACT_PARENT_CHILD_OVERLAP_EXPLAINS_AREA_DIFFERENCE'
                if overlap.area()==5457000 and difference.is_empty()
                else 'RECOGNITION_DIFFERENCE_NOT_EXPLAINED_BY_SIMPLE_PARENT_CHILD_UNION'))
        # Both outcomes are valid diagnostic results; only exact native/derivation identity
        # above is required. A recognition difference must not be called repaired or waived.
        result['status']='PASS_MASK_ATTRIBUTION_ONLY'
        result['scope']='Exact derived TIE polygons reproduce captured native footprints; measures VSS stripe and parent/DCP overlap/XOR only. No substrate contract or IOVSS conductor connectivity repair.'
    except BaseException as exc:
        result['error']=str(exc)
        raise
    finally:
        write(output/'analysis.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('controls','analyze'))
    parser.add_argument('path',type=Path)
    args=parser.parse_args()
    if args.action=='controls':
        controls(args.path)
    else:
        analyze(args.path)


if __name__=='__main__':
    main()
