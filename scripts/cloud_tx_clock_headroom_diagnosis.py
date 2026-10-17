#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual failed HBTs back to native devices and physical macro ownership."""
import json,os,re,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-clock-headroom-diagnosis'

def box(text):
    nums=re.findall(r'[-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?',text)
    assert len(nums)==4,text
    values=list(map(float,nums));assert values[0]<=values[2]and values[1]<=values[3]
    return values

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,scope='Exact source-bound failed device and geometry diagnosis; no simulation rerun or changed electrical limits.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        receipt=json.loads((ROOT/'docs/evidence/tx-tree32-headroom-composition-pass-20261017.json').read_text())
        archive=OUT/'source.tar.gz';fetch(receipt['url'],receipt['sha256'],archive);assert archive.stat().st_size==receipt['bytes']
        dest=OUT/'source';dest.mkdir()
        with tarfile.open(archive)as t:t.extractall(dest,filter='data')
        archive.unlink();source=dest/'cloud-tx-tree32-headroom-assembly'
        assert sha(source/'composition-result.json')==receipt['summary_sha256']
        report=json.loads((source/'composition-result.json').read_text());assert report['status']=='PASS_ACTUAL_TREE1674_SOURCE_BOUND_RC_COMPOSITION_AND_FAULTS_REQUIRES_TRANSIENT'
        assert all(sha(source/n)==h for n,h in report['outputs'].items())
        binding=json.loads((source/'binding96/binding01.json').read_text())
        locations=json.loads((source/'wire96/device-locations01.json').read_text())
        layout=json.loads((source/'layout/result.json').read_text())
        physical=json.loads((source/'result.json').read_text());assert physical['variant']=='budget_high3_trim'
        dx,dy=layout['origin_translation_um'];owners={}
        for name,p in layout['placements'].items():
            b=box(p['bbox_um']);owners[name]=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]
        failed=json.loads((ROOT/'docs/evidence/tx-tree32-clock-wire-compact-rejection-20261017.json').read_text())
        targets=set().union(*(set(c['failed_hbts'])for c in failed['cases']))
        assert targets=={'xtree.xd0109','xtree.xd0110','xtree.xd0111','xtree.xd0112'}
        devices={d['instance'].lower():d for d in binding['devices']};assert len(devices)==1674
        locations={str(d['native_id']):d for d in locations['devices']}
        resolved=[]
        for target in sorted(targets):
            dev=devices[target.split('.',1)[1]];loc=locations[str(dev['native_id'])];b=box(loc['pcell']['bbox'])
            matches=[name for name,p in owners.items()if p[0]-1e-9<=b[0]and p[1]-1e-9<=b[1]and p[2]+1e-9>=b[2]and p[3]+1e-9>=b[3]]
            assert len(matches)==1,(target,matches)
            owner=matches[0];nodes=[n for n in physical['plan']['nodes']if n['label']==owner]
            assert len(nodes)==1
            resolved.append(dict(instance=target,binding=dev,location=loc,owner=owner,plan_node=nodes[0],placement=layout['placements'][owner],
                observed={c['case']:c['failed_hbts'].get(target)for c in failed['cases']}))
        result.update(status='COMPLETE_NATIVE_FAILED_HBT_MACRO_BINDING_NOT_REPAIR',source_composition=receipt,resolved=resolved,
            source_inputs={str(p.relative_to(source)):sha(p)for p in [source/'composition-result.json',source/'binding96/binding01.json',source/'wire96/device-locations01.json',source/'layout/result.json',source/'result.json']})
        print(json.dumps(resolved,indent=2),flush=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
