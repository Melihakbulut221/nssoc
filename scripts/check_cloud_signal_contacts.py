#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exhaustive same-layer contacts between different named signal nets.

Exact exported integer routing rectangles only. No spacing tolerance. This is
not a foundry DRC deck, CUT/PG/macro-internal extraction or transistor LVS.
"""
import argparse,collections,gzip,json,os,random,struct
from pathlib import Path
import numpy as np
import shapely
from shapely.strtree import STRtree
KIND=('pin','wire','via','patch')

def contacts(coords,owners,chunk=2048):
    assert len(coords)==len(owners) and chunk>0
    if not len(coords):return
    geoms=shapely.box(coords[:,0],coords[:,1],coords[:,2],coords[:,3]);tree=STRtree(geoms)
    for start in range(0,len(coords),chunk):
        pairs=tree.query(geoms[start:start+chunk],predicate='intersects')
        left=pairs[0]+start;right=pairs[1]
        keep=(left<right)&(owners[left]!=owners[right])
        for a,b in zip(left[keep],right[keep]):
            a,b=int(a),int(b)
            dx=int(min(coords[a,2],coords[b,2])-max(coords[a,0],coords[b,0]))
            dy=int(min(coords[a,3],coords[b,3])-max(coords[a,1],coords[b,1]))
            assert dx>=0 and dy>=0,'Spatial index disagrees with integer geometry'
            yield a,b,'area_overlap' if dx>0 and dy>0 else 'boundary_touch'

def controls():
    def query(rects,owners,chunk=2):return set(contacts(np.asarray(rects,dtype=np.int64),np.asarray(owners,dtype=np.int64),chunk))
    assert query([[0,0,2,2],[1,1,3,3]],[0,1])=={(0,1,'area_overlap')}
    assert query([[0,0,2,2],[2,0,4,2]],[0,1])=={(0,1,'boundary_touch')}
    assert query([[0,0,2,2],[2,2,4,4]],[0,1])=={(0,1,'boundary_touch')}
    assert not query([[0,0,2,2],[1,1,3,3]],[0,0])
    assert not query([[0,0,2,2],[3,0,4,2]],[0,1])
    rng=random.Random(85261);rects=[];owners=[];layers=[]
    for i in range(96):
        x,y=rng.randrange(-15,15),rng.randrange(-15,15);rects.append([x,y,x+rng.randrange(1,9),y+rng.randrange(1,9)]);owners.append(rng.randrange(8));layers.append(rng.randrange(4))
    oracle=set()
    for i,a in enumerate(rects):
        for j in range(i+1,len(rects)):
            b=rects[j]
            if layers[i]!=layers[j] or owners[i]==owners[j]:continue
            dx=min(a[2],b[2])-max(a[0],b[0]);dy=min(a[3],b[3])-max(a[1],b[1])
            if dx>=0 and dy>=0:oracle.add((i,j,'area_overlap' if dx>0 and dy>0 else 'boundary_touch'))
    for chunk in (1,7,2048):
        found=set()
        for layer in range(4):
            ids=[i for i in range(96)if layers[i]==layer]
            for a,b,kind in query([rects[i]for i in ids],[owners[i]for i in ids],chunk):found.add((ids[a],ids[b],kind))
        assert found==oracle,'Layer/owner/chunk handling differs from exhaustive integer oracle'
    assert oracle
    return dict(exact_integer_reference_pairs=len(oracle),chunk_sizes=[1,7,2048],area_edge_corner_contacts_detected=True,same_net_and_disjoint_excluded=True,layer_partition_checked=True)

def inspect(directory):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    result=dict(status='RUNNING',accepted=False,controls=controls(),shape_count=0,net_count=0,layers={},contact_shape_pairs=0,contact_net_pairs=0,transistor_lvs_passed=False,foundry_drc_passed=False,
      scope='All exported signal/clock routing rectangles, patch rectangles, via routing-metal boxes and LEF pin boxes. Counts area overlaps and boundary contacts between different named nets on the same layer; no virtual via joins. Excludes PG, CUT layers, cell/macro internal geometry, spacing/ESD/full-chip LVS, and any timing acceptance.')
    def save():(directory/'signal-contacts.json').write_text(json.dumps(result,indent=2)+'\n')
    save();files={};counts=collections.Counter();names=[];seen=set();record=struct.Struct('<7q')
    try:
        with gzip.open(directory/'signal-geometry.jsonl.gz','rt') as source:
            for line in source:
                row=json.loads(line);name=row['net'];assert name not in seen;seen.add(name);owner=len(names);names.append(name)
                for index,s in enumerate(row['shapes']):
                    layer=s['layer'];assert layer and '/'not in layer and '\\'not in layer and layer not in ('.','..')
                    rect=s['box'];assert len(rect)==4 and all(type(v)is int and abs(v)<2**52 for v in rect) and rect[0]<rect[2] and rect[1]<rect[3]
                    assert s['kind'] in KIND
                    if layer not in files:files[layer]=(directory/('contacts-'+layer+'.bin')).open('wb')
                    files[layer].write(record.pack(owner,index,KIND.index(s['kind']),*rect));counts[layer]+=1
        for file in files.values():file.close()
        result['net_count']=len(names);result['shape_count']=sum(counts.values())
        export=json.loads((directory/'export.json').read_text());assert result['net_count']==export['exported_nets'] and result['shape_count']==export['shapes']
        (directory/'contact-net-names.json').write_text(json.dumps(names)+'\n');save();net_pairs=set()
        with gzip.open(directory/'signal-contact-pairs.jsonl.gz','wt') as output:
            for layer in sorted(counts):
                data=np.memmap(directory/('contacts-'+layer+'.bin'),dtype='<i8',mode='r').reshape((-1,7));assert len(data)==counts[layer]
                stats=dict(shapes=len(data),area_overlap=0,boundary_touch=0)
                for a,b,kind in contacts(data[:,3:],data[:,0]):
                    one,two=data[a],data[b];n1,n2=int(one[0]),int(two[0]);net_pairs.add(tuple(sorted((n1,n2))));stats[kind]+=1
                    output.write(json.dumps(dict(layer=layer,contact=kind,a=dict(net=names[n1],shape=int(one[1]),kind=KIND[int(one[2])],box=one[3:].tolist()),b=dict(net=names[n2],shape=int(two[1]),kind=KIND[int(two[2])],box=two[3:].tolist())),separators=(',',':'))+'\n')
                result['layers'][layer]=stats;result['contact_shape_pairs']+=stats['area_overlap']+stats['boundary_touch'];result['contact_net_pairs']=len(net_pairs);save();print('CONTACT_LAYER',layer,json.dumps(stats),flush=True)
                del data
        result.update(status='COMPLETE_ALL_EXPORTED_SIGNAL_RECTANGLE_CONTACT_SCREEN_NOT_SIGNOFF',no_cross_net_contacts=result['contact_shape_pairs']==0)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        for file in files.values():file.close()
        save()
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');p.add_argument('--directory',type=Path);a=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    print(json.dumps(controls() if a.controls_only else inspect(a.directory)),flush=True)
