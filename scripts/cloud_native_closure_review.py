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
        assert all(sha(out/'source'/n)==original['outputs'][n]for n in selected)
        r['status']='COMPLETE_IMMUTABLE_NATIVE_REPORT_REVIEW_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(f.relative_to(out)):sha(f)for f in out.rglob('*')if f.is_file()and f!=out/'result.json'}
        (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
