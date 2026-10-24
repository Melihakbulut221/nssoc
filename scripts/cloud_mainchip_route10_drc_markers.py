#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Expose exact retained DRT marker reports without touching the running router."""
import hashlib,json,os,re,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-route10-drc-markers'
SUMMARY='c4aa184c22b3f9be9a5065a0a50f49d5eb6458eee859934209cc36b8c64471cb'
PARTS='809f6b139794cc2efcf3f35e8dbfec73071c75a9f44af2ef00ddb0cc4e7259f4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir();reports.OUT=OUT
    r={'status':'RUNNING','source_head':os.environ['GITHUB_SHA'],'routing_started_or_modified':False,'full_phy_accepted':False,'final_timing_complete':False,
       'scope':'Read-only exact route10 retained report text. Live route11 is not accessed, restarted or modified. DRT intermediate markers are not final chip DRC.'}
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        names=['work/detailed-route.drc-'+str(i)+'.rpt'for i in [20,25,30]]+['work/native.log']
        report,proof=reports.restore_report('mainchip-repair-deep-drt-cross',39868561968,SUMMARY,PARTS,OUT/'source',names)
        assert report['native_process_saved']and not report['route_complete']and report['sources_unchanged']
        assert report['candidate_netlist_sha256']=='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030'
        r['source']=proof
        r['exact_report_text']={n:(OUT/'source'/n).read_text()for n in names if n.endswith('.rpt')}
        r['candidate_netlist_sha256']=report['candidate_netlist_sha256']
        r['native_summary']=report['native_log']
        r['literal_marker_counts']={n:t.lower().count('violation type:')for n,t in r['exact_report_text'].items()}
        assert all(sha(OUT/'source'/n)==report['outputs'][n]for n in names)
        r.update(status='PASS_EXACT_RETAINED_INTERMEDIATE_DRT_REPORT_READ_NOT_FINAL_DRC',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
