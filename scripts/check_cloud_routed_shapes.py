#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Signal continuity from exact metal intersections and physical via boxes."""
import argparse,collections,copy,gzip,json,os
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree

def inspect(row):
    shapes=row['shapes'];parent=list(range(len(shapes)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(a,b):parent[find(a)]=find(b)
    layers=collections.defaultdict(list);groups={};pins=set()
    for i,s in enumerate(shapes):
        layers[s['layer']].append(i)
        if s['join'] is not None:
            if s['join'] in groups:join(i,groups[s['join']])
            else:groups[s['join']]=i
            if s['kind']=='pin':pins.add(s['join'])
    for layer,indices in layers.items():
        rects=[box(*shapes[i]['box']) for i in indices];tree=STRtree(rects)
        for local,rect in enumerate(rects):
            for other in tree.query(rect,predicate='intersects'):join(indices[local],indices[int(other)])
    components=len({find(i) for i in range(len(shapes))})
    missing=sorted(set(row['expected_pins'])-pins)
    return dict(net=row['net'],components=components,missing_terminal_geometry=missing,shapes=len(shapes),virtual_shorts=row['virtual_shorts'],passed=components==1 and not missing,
                scope='LEF-terminal equivalence plus actual same-layer intersections and physical via metal/cut groups; no virtual wire join used. Not inter-net short detection or transistor LVS.')

def controls():
    a=dict(layer='Metal2',box=[0,0,2,2],kind='pin',join='I:a/A')
    b=dict(layer='Metal2',box=[8,0,10,2],kind='pin',join='I:b/A')
    wire=dict(layer='Metal2',box=[1,0,9,2],kind='wire',join=None)
    good=dict(net='fixture',shapes=[a,b,wire],expected_pins=['I:a/A','I:b/A'],virtual_shorts=0)
    assert inspect(good)['passed'];failures=[]
    for name in ('gap','wrong_layer','missing_pin','virtual_short_only','floating_metal'):
        x=copy.deepcopy(good)
        if name=='gap':x['shapes'][2]['box']=[1,0,7,2]
        elif name=='wrong_layer':x['shapes'][2]['layer']='Metal3'
        elif name=='missing_pin':x['shapes']=x['shapes'][1:]
        elif name=='virtual_short_only':x['shapes']=x['shapes'][:2];x['virtual_shorts']=1
        else:x['shapes'].append(dict(layer='Metal2',box=[20,0,22,2],kind='wire',join=None))
        assert not inspect(x)['passed'],name;failures.append(name)
    via=copy.deepcopy(good);via['shapes'][1]['layer']='Metal3'
    via['shapes'] += [dict(layer=layer,box=[8,0,10,2],kind='via',join='V:0') for layer in ('Metal2','Metal3')]
    assert inspect(via)['passed']
    return dict(positive=2,negative=failures)

def main(directory):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    result=dict(status='RUNNING',accepted=False,controls=controls(),checked=0,failed=0,total_shapes=0,inter_net_shorts_checked=False,transistor_lvs_passed=False)
    with gzip.open(directory/'signal-geometry.jsonl.gz','rt') as source,(directory/'signal-continuity-failures.jsonl').open('w') as failed:
        for text in source:
            row=inspect(json.loads(text));result['checked']+=1;result['total_shapes']+=row['shapes']
            if not row['passed']:result['failed']+=1;failed.write(json.dumps(row)+'\n')
    export=json.loads((directory/'export.json').read_text());assert result['checked']==export['exported_nets'] and result['total_shapes']==export['shapes']
    result.update(status='COMPLETE_SIGNAL_GEOMETRIC_CONTINUITY_SCREEN_NOT_LVS',signal_continuity_passed=result['failed']==0)
    (directory/'continuity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');p.add_argument('--directory',type=Path);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.controls_only:print(json.dumps(controls()))
    else:main(a.directory)
