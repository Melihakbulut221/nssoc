#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import argparse,json,os,subprocess,sys
from pathlib import Path
from cdr500_cleaned_source import check
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('binding','rc'),required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    check();group='cdr500-cleaned-'+args.stage
    root=ROOT/('hw/soc/out/cloud-cdr500-cleaned-binding'if args.stage=='binding'else'hw/soc/out/cloud-cdr500-floating-wire-cleanup')
    assert not root.exists();code=1
    try:code=subprocess.call([sys.executable,str(ROOT/('scripts/cloud_cdr500_cleaned_'+args.stage+'.py'))],cwd=ROOT)
    finally:
        root.mkdir(parents=True,exist_ok=True);result=root/'result.json'
        if not result.exists():result.write_text(json.dumps(dict(status='FAIL_MISSING_REPORT',accepted=False,source_head=os.environ['GITHUB_SHA']))+'\n')
        stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-1';summary=ROOT/(stem+'.summary.json');summary.write_bytes(result.read_bytes())
        subprocess.run([sys.executable,'scripts/cloud_chunked_results.py','--directory',str(root),'--stem',stem],cwd=ROOT,check=True)
        manifest=ROOT/(stem+'.parts.json');m=json.loads(manifest.read_text())
        subprocess.run([sys.executable,'scripts/publish_cloud_results.py','--group',group,str(summary),str(manifest),*[v['name']for v in m['parts']]],cwd=ROOT,check=True)
    assert code==0,(args.stage,code);check()
    observed=json.loads((root/'result.json').read_text());assert observed['sources_unchanged']and observed['status'].startswith('PASS_')
if __name__=='__main__':main()
