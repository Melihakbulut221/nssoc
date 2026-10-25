#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Identify actual fixed-route ECO contacts; preserve every intersecting shape."""
import gzip,json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-protected-contact-review'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],full_serial_phy_complete=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        selected=('signal-contact-pairs.jsonl.gz','signal-geometry.jsonl.gz','signal-contacts.json','source/geometry-proof.json','protected-load-eco-source/summary.json')
        source,proof=reports.restore_report('candidate-geometry',38834266592,'7fcdd4a26f94e2089b4249dc7ab3226827ddab395e0128306aa91706815f51f9','de213d44825749a0c7e5655ee4d8e62acdf621af06e36b2217e7b24ef9c201cd',OUT/'source',selected)
        assert source['source_unchanged'] and source['profile']=='protected_load_batch'
        assert source['restoration']['run']==38830273683
        candidate=json.loads((OUT/'source/protected-load-eco-source/summary.json').read_text())
        assert sha(OUT/'source/protected-load-eco-source/summary.json')=='6fd4d72ad02e0f5396f102d5fe792e8b5a40b051959b50019fde46ec1191e9c5'
        changed=set(candidate['guide_provenance']['selected_native_nets']);assert len(changed)==100
        with gzip.open(OUT/'source/signal-contact-pairs.jsonl.gz','rt') as f:pairs=[json.loads(line) for line in f]
        assert len(pairs)==source['contacts']['contact_shape_pairs']==25
        targets={(row[side]['net'],row[side]['shape']) for row in pairs for side in ('a','b')};shapes={}
        with gzip.open(OUT/'source/signal-geometry.jsonl.gz','rt') as f:
            for line in f:
                row=json.loads(line)
                for index,shape in enumerate(row['shapes']):
                    if (row['net'],index) in targets:shapes[(row['net'],index)]=shape
        assert set(shapes)==targets
        groups={}
        for row in pairs:
            for side in ('a','b'):
                item=row[side];shape=shapes[(item['net'],item['shape'])]
                assert shape['box']==item['box'] and shape['layer']==row['layer'] and shape['kind']==item['kind']
                item['native_export_shape']=shape
                item['route_selection']='changed_or_new' if item['net'] in changed else 'protected'
            a,b=row['a']['box'],row['b']['box']
            rect=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
            assert rect[0]<rect[2] and rect[1]<rect[3]
            row['intersection_dbu']=rect
            key=tuple(sorted((row['a']['net'],row['b']['net'])))
            groups.setdefault(key,[]).append(row)
        assert len(groups)==source['contacts']['contact_net_pairs']==8
        result.update(status='COMPLETE_SOURCE_BOUND_CONTACT_DIAGNOSIS_NOT_REPAIR',source=proof,contact_shape_pairs=len(pairs),contact_net_pairs=len(groups),pairs=pairs,net_pairs=[dict(nets=list(k),shape_pairs=len(v)) for k,v in sorted(groups.items())],scope='Exact geometry source: all25same-layer area intersections across8netpairs. No waiver, no physical modification, no transistor extraction or signoff. Classify new/changed versus protected geometry to drive repair.')
        for name,pin in proof['restore']['selected_files'].items():assert sha(OUT/'source'/name)==pin['sha256']
        result['source_unchanged']=True
        print(json.dumps(result),flush=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:save()
if __name__=='__main__':main()
