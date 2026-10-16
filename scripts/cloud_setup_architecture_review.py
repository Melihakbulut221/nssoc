#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare preserved historical pipeline paths to current exact routed setup map."""
import hashlib,json,os,re,tarfile
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-setup-architecture-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,timing_closed=False,no_new_native=True,scope='Read-only historical pipeline route reports versus current exact pin/net timing map. Different source/layouts are not equivalent experiments; no pipeline parameter is inferred from missing names and no historical timing is inherited.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        record=ROOT/'docs/evidence/pipeline-completed-route-20260924.json';history=json.loads(record.read_text());assert history['status']=='FAIL_FINAL_TIMING'
        spec=history['archive'];archive=ROOT/spec['path'];assert sha(archive)==spec['sha256']=='c0b26aff162a18516e19dde18586693336dbe0f1402d80f82009bd06576e8e55' and archive.stat().st_size==spec['bytes']
        seen=set();selected={};configs={};headings={}
        with tarfile.open(archive,'r:xz')as tar:
            for member in tar:
                if member.isdir():continue
                assert member.isfile() and member.name in spec['members'] and member.name not in seen
                raw=tar.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==spec['members'][member.name];seen.add(member.name)
                name=member.name
                if '/09-openroad-stapostpnr/'in name and name.endswith(('/max.rpt','/min.rpt','/clock.rpt','/summary.rpt')):
                    text=raw.decode();target=OUT/'historical'/Path(name).relative_to('hw/soc/out/external-review-20260919/route-closure-20260923/runs/pipeline-final-route');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                    selected[str(target.relative_to(OUT))]=dict(source=name,sha256=sha(target))
                    sections=re.split(r'(?m)(?=^Startpoint: )',text)
                    paths=[block for block in sections if block.startswith('Startpoint: ')]
                    headings[str(target.relative_to(OUT))]=dict(native_header_excerpt=text[:14000],first_paths=[b for b in paths[:3]],native_path_count=len(paths))
                if name.endswith('config.json') and '/09-openroad-stapostpnr/'in name:
                    config=json.loads(raw);configs[name]={k:v for k,v in config.items()if any(t in k.upper()for t in ['SYNTH','CORE_REQ','CORE_WB','REQ_REG','CLOCK','STA','DIE','LIB','SDC'])}
        assert seen==set(spec['members']) and len(selected)>=6
        mapfile=OUT/'current-map.json';fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38960727302-1-nine-size-setup-map/nine-size-setup-map-38960727302-1.summary.json','2116ad39842002516bafbd8f8b84e8a8a532d536256d5cc067da283a7b632860',mapfile)
        current=json.loads(mapfile.read_text());assert current['source_unchanged']and current['path_count']==60
        paths=[]
        for p in current['paths']:
            if p['edge']!='rise':continue
            rows=p['data_rows'];paths.append(dict(marker=p['marker'],slack_seconds=p['slack_seconds'],startpoint=p['startpoint'],endpoint=p['endpoint'],data_cell_count=p['data_cell_count'],retained_launch_net=current['native']['pin_map'][rows[0]['pin']]['net'],largest_data_stages=sorted([dict(row,net=current['native']['pin_map'][row['pin']]['net'])for row in rows],key=lambda row:row['increment_ns'],reverse=True)[:5]))
        r.update(status='COMPLETE_HISTORICAL_PIPELINE_AND_CURRENT_SETUP_PATH_REVIEW_NOT_REPAIR_ACCEPTANCE',historical_manifest_sha256=sha(record),historical_archive_sha256=sha(archive),all_historical_member_hashes_verified=len(seen),historical_corners=history['corners'],historical_configuration=configs,historical_reports=headings,current_paths=paths,current_map_sha256=sha(mapfile),source_unchanged=True)
        assert sha(archive)==spec['sha256']
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
