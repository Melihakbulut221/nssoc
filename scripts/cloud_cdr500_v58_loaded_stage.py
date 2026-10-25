#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Gate exact prepared/full loaded PD500 cases and publish all terminal evidence."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
CASES=['nominal_early','nominal_late','hot_early','hot_late','cold_early','cold_late','constant_zero','constant_one','clock_stopped','vi_bias_off']
def check():
    record=json.loads((ROOT/'scripts/cdr500-v58-loaded-methods.json').read_text())
    for path,digest in record['protected'].items():assert sha(ROOT/path)==digest,path
    return record

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1';check()
    group='cdr500-v58-loaded-'+('preparation'if args.prepare_only else args.case)
    root=ROOT/('cloud-cdr500-v58-loaded-'+args.case);assert not root.exists();code=1
    try:
        cmd=[sys.executable,str(ROOT/'scripts/cloud_cdr500_v58_loaded.py'),'--case',args.case]
        if args.prepare_only:cmd.append('--prepare-only')
        code=subprocess.call(cmd,cwd=ROOT)
    finally:
        root.mkdir(parents=True,exist_ok=True);result=root/'result.json'
        if not result.exists():result.write_text(json.dumps(dict(status='FAIL_MISSING_REPORT',accepted=False,source_head=os.environ['GITHUB_SHA'],case=args.case,preparation_only=args.prepare_only))+'\n')
        stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-1';summary=ROOT/(stem+'.summary.json');summary.write_bytes(result.read_bytes())
        subprocess.run([sys.executable,'scripts/cloud_chunked_results.py','--directory',str(root),'--stem',stem],cwd=ROOT,check=True)
        manifest=ROOT/(stem+'.parts.json');parts=json.loads(manifest.read_text())
        subprocess.run([sys.executable,'scripts/publish_cloud_results.py','--group',group,str(summary),str(manifest),*[x['name']for x in parts['parts']]],cwd=ROOT,check=True)
    assert code==0,(args.case,code);check();result=json.loads((root/'result.json').read_text())
    assert result['sources_unchanged']and result['source_head']==os.environ['GITHUB_SHA']and result['case']==args.case
    assert len(result['source_bits'])==256 and len(result['binding_controls']['rejected'])==13
    if args.prepare_only:assert result['status']=='PASS_PD500_LOADED_PREPARATION_AND13_BINDING_CONTROLS_NO_TRANSIENT'and not result['transient_executed']
    else:
        assert result['status']=='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'
        assert result['actual_fault_detected']if args.case in ('clock_stopped','vi_bias_off')else result['devices_passed']and result['data_passed']and result['vi']['passed']
if __name__=='__main__':main()
