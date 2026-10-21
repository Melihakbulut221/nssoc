#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run original loaded gates only after exact fresh v18 audit and composition."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from cloud_cdr_input_access_v26_mim_stage import receipt_path
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc/'
def api(p):
    return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    from check_cdr_input_access_v26_streamed_sources import check
    check()
    path=ROOT/'docs/evidence/cdr-input-access-v26-fullwave-input-20261021.json'
    original=path.read_bytes();spec=json.loads(original);deadline=time.monotonic()+10800
    while True:
        run=api('actions/runs/'+str(spec['run']))
        assert run['head_sha']==spec['source_head']and run['path']==spec['workflow_path']
        assert run['head_branch']=='codex/complete-open-work'and run['run_attempt']==1
        if run['status']=='completed':
            assert run['conclusion']=='success',('Original audit/composition rejected',run['conclusion'])
            break
        assert time.monotonic()<deadline,'Observation expired; do not restart live prerequisite'
        print(json.dumps(dict(waiting_for_exact_validation_run=spec['run'],status=run['status'])),flush=True)
        time.sleep(30)
    jobs=api('actions/runs/'+str(spec['run'])+'/jobs?per_page=100')['jobs']
    assert {j['name']for j in jobs}=={'mim-parent-audit','mim-composition'}
    assert all(j['status']=='completed'and j['conclusion']=='success'for j in jobs)
    receipts={}
    for stage in ('mim-parent-audit','mim-composition'):
        release=api('releases/tags/cloud-results-'+str(spec['run'])+'-1-cdr-input-access-v26-'+stage)
        loaded={}
        for suffix in ('.summary.json','.parts.json'):
            found=[a for a in release['assets']if a['name'].endswith(suffix)];assert len(found)==1
            a=found[0];raw=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream',REPO+'releases/assets/'+str(a['id'])])
            assert len(raw)==a['size']and a['digest']=='sha256:'+sha(raw)
            loaded[suffix]=(a,raw)
        a,raw=loaded['.summary.json'];b,parts=loaded['.parts.json'];r=json.loads(raw)
        assert r['source_head']==spec['source_head']and r['sources_unchanged']and r['status'].startswith('PASS_')
        receipt=dict(run=spec['run'],source_head=r['source_head'],summary_asset=a['id'],summary_sha256=sha(raw),parts_asset=b['id'],parts_sha256=sha(parts),status=r['status'],outputs=r['outputs'],report=r)
        dest=receipt_path(stage)
        assert not dest.exists(),'Never replace an immutable receipt'
        dest.write_text(json.dumps(receipt,indent=2)+'\n');receipts[stage]=receipt
    audit=receipts['mim-parent-audit'];composition=receipts['mim-composition']
    assert audit['report']['capture_source']['summary_sha256']==spec['capture_summary_sha256']
    assert composition['report']['audited_source']['summary_sha256']==audit['summary_sha256']
    assert len(audit['report']['wire_controls']['cases'])==13 and len(audit['report']['intrinsic_controls'])==9
    assert len(composition['report']['controls'])==19
    assert composition['report']['composition']['counts']==dict(devices=476,R=17674,C=12694)
    assert path.read_bytes()==original
    code=subprocess.call([sys.executable,str(ROOT/'scripts/cloud_cdr_input_access_v26_mim_streamed.py'),'--case',args.case],cwd=ROOT)
    check()
    assert path.read_bytes()==original
    out=ROOT/('cloud-cdr-input-access-v26-mim-streamed-'+args.case)
    report=out/'result.json'
    if report.exists():
        r=json.loads(report.read_text())
        r['validation_prerequisite']=dict(spec=spec,spec_sha256=sha(original),receipts={k:{n:v[n]for n in ('run','source_head','summary_asset','summary_sha256','parts_asset','parts_sha256','status')}for k,v in receipts.items()})
        report.write_text(json.dumps(r,indent=2)+'\n')
    assert code==0,('Original loaded electrical gates rejected',args.case,code)
if __name__=='__main__':main()
