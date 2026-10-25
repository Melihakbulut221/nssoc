#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read immutable failed native connectivity/timing reports on hosted runners."""
import argparse,json,os,re
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['tx','mainchip'],required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('hw/soc/out/cloud-native-closure-review-'+a.case);out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False,case=a.case)
    try:
        if a.case=='tx':
            pin=json.loads((ROOT/'docs/evidence/tx-v5-fast-stage-lvs-rejection-20261018.json').read_text());group='tx-v5-fast-stage-assembly'
            selected=['physical/lvs/deck.log','physical/lvs/extracted.cir','layout/schematic.cir','layout/result.json']
        else:
            pin=json.loads((ROOT/'docs/evidence/onehot-load-resume-route-result-20261018.json').read_text());group='onehot-load-resume'
            selected=['run/2-openroad-checkantennas/reports/antenna.rpt']
            for corner in ('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C'):
                selected += ['run/5-nssoc-onehotroutedsta/'+corner+'/'+n for n in ('max.rpt','min.rpt','checks.rpt','violator_list.rpt')]
        original,proof=reports.restore_report(group,pin['run_id'],pin['summary_sha256'],pin['parts_sha256'],out/'source',selected)
        assert original['source_head']==pin['source_head']and original['status']==pin['observed']['status']
        r['source']=proof;r['reports']={}
        for n in selected:
            f=out/'source'/n;assert sha(f)==original['outputs'][n]
            lines=f.read_text(errors='strict').splitlines()
            # Full source remains in output archive. Explicitly identify bounded previews.
            limit=800 if a.case=='tx' else 250
            r['reports'][n]=dict(sha256=sha(f),line_count=len(lines),head=lines[:limit],tail=lines[-100:]if len(lines)>limit else [],preview_truncated=len(lines)>limit)
        if a.case=='tx':
            layout=json.loads((out/'source/layout/result.json').read_text());segments=[]
            def rect(raw):
                x=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(x)==4;return x
            for wire in layout['signal_routes']:
                net=wire['net'];x=wire['x_um'];y0,y1=wire['y_um'];w=wire['width_um']/2
                segments.append(dict(net=net,layer='TopMetal1',box=[x-w,min(y0,y1)-w,x+w,max(y0,y1)+w],kind='trunk'))
                for endpoint,y in zip(wire['endpoints'],wire['y_um'],strict=True):
                    tag,pin=endpoint.split('.');b=rect(layout['placements'][tag]['ports'][pin]);px=(b[0]+b[2])/2;py=(b[1]+b[3])/2;assert abs(py-y)<1e-8
                    segments.append(dict(net=net,layer='TopMetal2',box=[min(px,x)-w,y-w,max(px,x)+w,y+w],kind=endpoint))
            overlaps=[]
            for i,left in enumerate(segments):
                for right in segments[i+1:]:
                    if left['net']==right['net']or left['layer']!=right['layer']:continue
                    aa=left['box'];bb=right['box'];intersection=[max(aa[0],bb[0]),max(aa[1],bb[1]),min(aa[2],bb[2]),min(aa[3],bb[3])]
                    if intersection[0]<intersection[2]and intersection[1]<intersection[3]:overlaps.append(dict(left=left,right=right,intersection_um=intersection))
            r['parent_signal_conductor_overlaps']=overlaps
            r['overlap_scope']='Exact generator metadata rectangles; excludes vias, supply and child polygons. Native unsimplified LVS remains authoritative.'
            assert overlaps,'No positive-area parent signal overlap; investigate native LVS independently'
        else:
            lines=(out/'source'/selected[0]).read_text().splitlines();blocks=[];start=0
            for i,line in enumerate(lines):
                if line.startswith('Net:'):
                    if i>start:blocks.append(lines[start:i])
                    start=i
            blocks.append(lines[start:])
            r['antenna_violation_sections']=[b for b in blocks if any('VIOLAT' in x.upper() for x in b)]
        assert all(sha(out/'source'/n)==original['outputs'][n]for n in selected)
        r['status']='COMPLETE_IMMUTABLE_NATIVE_REPORT_REVIEW_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(f.relative_to(out)):sha(f)for f in out.rglob('*')if f.is_file()and f!=out/'result.json'}
        (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
