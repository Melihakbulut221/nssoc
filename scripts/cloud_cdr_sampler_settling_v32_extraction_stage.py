#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run one native stage and bind subsequent jobs to its immutable release bytes."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from check_cdr_sampler_settling_v32_extraction_sources import check
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc'
DEPS={'planes':[],'wire-inputs':['planes'],'binding':['wire-inputs'],'rc':['wire-inputs']}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+'/'+path]))
def receipt_path(stage):
    assert stage in DEPS
    return ROOT/('docs/evidence/cdr-sampler-settling-v32-'+stage+'-pass-20261022.json')
def bind(stage):
    run=int(os.environ['GITHUB_RUN_ID']);group='cdr-sampler-settling-v32-'+stage
    tag=f'cloud-results-{run}-1-{group}'
    release=api('releases/tags/'+tag);assets={}
    for suffix in ('.summary.json','.parts.json'):
        found=[a for a in release['assets']if a['name'].endswith(suffix)];assert len(found)==1
        a=found[0];raw=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream',REPO+'/releases/assets/'+str(a['id'])])
        assert len(raw)==a['size']
        if a.get('digest'):assert a['digest']=='sha256:'+sha(raw)
        assets[suffix]=(a,raw)
    a,raw=assets['.summary.json'];b,parts=assets['.parts.json'];r=json.loads(raw)
    assert r['source_head']==os.environ['GITHUB_SHA']and r['sources_unchanged']and r['status'].startswith('PASS_')
    receipt=dict(run=run,source_head=r['source_head'],summary_asset=a['id'],summary_sha256=sha(raw),parts_asset=b['id'],parts_sha256=sha(parts),status=r['status'],outputs=r['outputs'],report=r)
    path=receipt_path(stage)
    assert not path.exists(),'Never overwrite a pinned receipt'
    path.write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=tuple(DEPS),required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Use a fresh run to preserve same-run provenance'
    check()
    for dependency in DEPS[a.stage]:bind(dependency)
    group='cdr-sampler-settling-v32-'+a.stage
    root=ROOT/('hw/soc/out/cloud-cdr-sampler-settling-v32-'+('wire-inputs'if a.stage=='rc'else a.stage))
    assert not root.exists()
    script=ROOT/('scripts/cloud_cdr_sampler_settling_v32_'+a.stage.replace('-','_')+'.py')
    code=1
    try:
        code=subprocess.call([sys.executable,str(script)],cwd=ROOT)
    finally:
        root.mkdir(parents=True,exist_ok=True)
        report=root/'result.json'
        if not report.exists():report.write_text(json.dumps(dict(status='FAIL_MISSING_REPORT',accepted=False,source_head=os.environ['GITHUB_SHA']))+'\n')
        stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-1';summary=ROOT/(stem+'.summary.json');summary.write_bytes(report.read_bytes())
        subprocess.run([sys.executable,str(ROOT/'scripts/cloud_chunked_results.py'),'--directory',str(root),'--stem',stem],cwd=ROOT,check=True)
        manifest=ROOT/(stem+'.parts.json');m=json.loads(manifest.read_text())
        subprocess.run([sys.executable,str(ROOT/'scripts/publish_cloud_results.py'),'--group',group,str(summary),str(manifest),*[part['name']for part in m['parts']]],cwd=ROOT,check=True)
    assert code==0,(a.stage,code)
    check()
    r=json.loads((root/'result.json').read_text());assert r['status'].startswith('PASS_')and r['sources_unchanged']
    print(json.dumps(dict(stage=a.stage,status=r['status'],full_phy_accepted=False)))
if __name__=='__main__':main()
