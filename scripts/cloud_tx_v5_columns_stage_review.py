#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map failed native TX devices to exact physical macros without rerunning SPICE."""
import hashlib,json,os,re,tarfile
from collections import Counter
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-v5-columns-stage-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-v5-columns-stage-review-input-20261018.json').read_text());source=pin['composition']
        failed=json.loads((ROOT/'docs/evidence/tx-v5-columns-native-full-wire-rejection-20261018.json').read_text())
        assert failed['summary_sha256']==pin['wave_summary_sha256']and failed['source_head']==pin['source_head']
        assert failed['review']['signals']['wrong_sign_samples']==181 and len(failed['review']['failed_hbts'])==24
        archive=OUT/'source.tar.gz';fetch(source['url'],source['sha256'],archive);assert archive.stat().st_size==source['bytes']
        inputs=OUT/'inputs';inputs.mkdir();receipts={}
        with tarfile.open(archive)as tar:
            names=tar.getnames()
            def extract(rel,expected):
                hits=[n for n in names if n=='cloud-tx-v5-columns-assembly/'+rel];assert len(hits)==1,(rel,hits)
                raw=tar.extractfile(hits[0]).read();assert hashlib.sha256(raw).hexdigest()==expected
                path=inputs/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                receipts[rel]=dict(sha256=expected,bytes=len(raw),member=hits[0]);return json.loads(raw)
            binding=extract('binding96/binding01.json',source['outputs']['binding96/binding01.json'])
            interface=extract('wire96/all-interface-probes.json',source['outputs']['wire96/all-interface-probes.json'])
            assert interface['status']=='PASS_ALL124_PHYSICAL_INPUT_LEGS_AND372_DATA_BASES'
            def dependency(rel):
                hits=[h for p,h in interface['inputs'].items()if p.endswith('/'+rel)];assert len(hits)==1,(rel,hits)
                return extract(rel,hits[0])
            layout=dependency('layout/result.json');locations=dependency('wire96/device-locations01.json')
        archive.unlink()
        devices={d['native_id']:d for d in locations['devices']};bound={d['native_id']:d for d in binding['devices']}
        assert len(devices)==len(bound)==1674 and set(devices)==set(bound)
        dx,dy=layout['origin_translation_um']
        def rect(raw):
            values=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(values)==4;return values
        boxes={}
        for tag,item in layout['placements'].items():
            l,b,rr,t=rect(item['bbox_um']);boxes[tag]=(l+dx,b+dy,rr+dx,t+dy)
        assert len(boxes)==31
        rows=[]
        for instance,metrics in failed['review']['failed_hbts'].items():
            hit=re.fullmatch(r'xtree\.xd(\d+)',instance);assert hit,instance
            key=int(hit[1]);d=devices[key];model=bound[key];assert d['model']=='npn13G2'and model['instance'].lower()==instance.split('.')[1]
            box=rect(d['pcell']['bbox']);owners=[tag for tag,b in boxes.items()if box[0]>=b[0]-1e-9 and box[1]>=b[1]-1e-9 and box[2]<=b[2]+1e-9 and box[3]<=b[3]+1e-9]
            assert len(owners)==1,(instance,box,owners)
            data_refs=[dict(input_leg=leg,endpoints=x['endpoints'],terminal=t)for leg,x in interface['references'].items()for t in x['intrinsic_terminals']if t['device']==key]
            rows.append(dict(instance=instance,native_id=key,physical_macro=owners[0],macro_box_um=boxes[owners[0]],device=d,compact_binding=model,actual_data_input_references=data_refs,measured=metrics))
        assert len(rows)==24
        r.update(status='COMPLETE_ACTUAL24_FAILED_HBT_TO_PHYSICAL_MACRO_MAPPING_NOT_ACCEPTANCE',failed_devices=rows,macro_counts=dict(Counter(x['physical_macro']for x in rows)),source=source,verified_files=receipts,signals=failed['review']['signals'],interfaces=failed['review']['interfaces'],clock_common_mode_range_v=failed['review']['clock_common_mode_range_v'],native_bias_current_a=failed['review']['native_bias_current_a'],prestage_native_bias_current_a=failed['review']['prestage_native_bias_current_a'])
        assert all(sha(inputs/p)==v['sha256']for p,v in receipts.items())
        print(json.dumps(dict(status=r['status'],macro_counts=r['macro_counts'],devices=[dict(instance=x['instance'],macro=x['physical_macro'],min_vce=x['measured']['min_post_vce_v'])for x in rows]),indent=2),flush=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
