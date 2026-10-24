#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read immutable native extractor coordinates for measured return-loss branches."""
import hashlib,json,os,re,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-v5-final-strap6-return-geometry'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,scope='Read-only localization of measured static resistor branches. Raw native coordinates and extraction metadata only; no geometric or electrical acceptance.')
    try:
        pinpath=ROOT/'docs/evidence/tx-v5-final-strap6-composition-pass-20261019.json'
        pin=json.loads(pinpath.read_text())
        assert pin['source_run']==39218951433 and pin['source_head']=='0a38fc8312e4d5252038502044653ca493491990'
        r['source']=pin;r['source_pin_sha256']=sha(pinpath)
        packed=OUT/'source.tar.gz';fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
        prefix='cloud-tx-v5-final-strap6-assembly/'
        wanted=('n5354','n5353','n5366','n5415','n5488')
        expression=re.compile(r'(?<![A-Za-z0-9_])(?:'+ '|'.join(wanted)+r')(?![0-9])')
        records=[];indices=[];methods={}
        with tarfile.open(packed)as tar:
            members=tar.getmembers()
            for member in members:
                if not member.isfile()or not member.name.startswith(prefix):continue
                rel=member.name[len(prefix):]
                if rel.startswith('wire96/rc03/'):indices.append(dict(path=rel,bytes=member.size))
                selected=rel.startswith('wire96/rc03/')and rel.endswith(('.ext','.spice','.sim','.res'))
                if selected:
                    data=tar.extractfile(member).read();text=data.decode(errors='replace');lines=text.splitlines()
                    matches=[i for i,line in enumerate(lines)if expression.search(line)]
                    if matches:
                        keep=sorted(set(j for i in matches for j in range(max(0,i-1),min(len(lines),i+2))))
                        records.append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),matching_lines=len(matches),header=lines[:12],snippets=[dict(line=i+1,text=lines[i])for i in keep]))
                if rel in ('wire96/compose-tree.py','wire96/compose49.py','wire96/run-rc01.py'):
                    data=tar.extractfile(member).read();text=data.decode();lines=text.splitlines()
                    hits=[i for i,line in enumerate(lines)if any(k in line for k in ('avss','P_','rnode','.ext','.res','scale','units','node_map'))]
                    keep=sorted(set(j for i in hits for j in range(max(0,i-2),min(len(lines),i+3))))
                    methods[rel]=dict(sha256=hashlib.sha256(data).hexdigest(),snippets=[dict(line=i+1,text=lines[i])for i in keep])
                if rel=='layout/result.json':
                    data=tar.extractfile(member).read();layout=json.loads(data)
                    r['layout']=dict(sha256=hashlib.sha256(data).hexdigest(),origin_translation_um=layout['origin_translation_um'],return_rectangles=layout['parent_return_geometry_before_origin_translation'],final_placement=layout['placements']['f'],public_avss=layout['ports']['avss'])
            assert len(indices)>0
            r.update(status='COMPLETE_NATIVE_RETURN_COORDINATE_REVIEW_REQUIRES_INTERPRETATION',requested_nodes=list(wanted),native_coordinate_matches=records,extractor_directory_inventory=indices,composition_mapping_methods=methods)
        packed.unlink()
        assert sha(pinpath)==r['source_pin_sha256']
        r['sources_unchanged']=True
        print(json.dumps(dict(status=r['status'],files_with_matches=len(records),extractor_files=len(indices))),flush=True)
    except BaseException as e:r.update(status='FAIL_NATIVE_COORDINATE_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
