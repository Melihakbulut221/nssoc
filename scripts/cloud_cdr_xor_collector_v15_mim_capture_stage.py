#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Continue only after every pinned fresh native extraction stage passes."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc'
OUT=ROOT/'hw/soc/out/cloud-cdr-xor-collector-v15-mim-parent-rc'
def api(path):
    return json.loads(subprocess.check_output(['gh','api',REPO+'/'+path]))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    specpath=ROOT/'docs/evidence/cdr-xor-collector-v15-mim-capture-input-20261019.json'
    rawspec=specpath.read_bytes();spec=json.loads(rawspec)
    from check_cdr_xor_collector_v15_mim_capture_sources import check
    check()
    # A live prerequisite is a wait, never a failure/restart. Bound to a single run.
    deadline=time.monotonic()+10800
    while True:
        run=api('actions/runs/'+str(spec['run']))
        assert run['head_sha']==spec['source_head']and run['path']==spec['workflow_path']
        assert run['head_branch']=='codex/complete-open-work'and run['run_attempt']==1
        if run['status']=='completed':
            assert run['conclusion']=='success',('Prerequisite native extraction rejected',run['conclusion'])
            break
        assert time.monotonic()<deadline,'Prerequisite still live; observation deadline reached, do not restart it'
        print(json.dumps(dict(waiting_for_exact_native_run=spec['run'],status=run['status'])),flush=True)
        time.sleep(30)
    jobs=api('actions/runs/'+str(spec['run'])+'/jobs?per_page=100')['jobs']
    assert {j['name']for j in jobs}==set(spec['stages'])and all(j['status']=='completed'and j['conclusion']=='success'for j in jobs)
    pinned={}
    for stage in spec['stages']:
        group='cdr-xor-collector-v15-'+stage
        release=api('releases/tags/cloud-results-'+str(spec['run'])+'-1-'+group)
        loaded={}
        for suffix in ('.summary.json','.parts.json'):
            assets=[a for a in release['assets']if a['name'].endswith(suffix)]
            assert len(assets)==1
            a=assets[0];raw=subprocess.check_output(['gh','api','-H','Accept: application/octet-stream',REPO+'/releases/assets/'+str(a['id'])])
            assert len(raw)==a['size']and a['digest']=='sha256:'+digest(raw)
            loaded[suffix]=(a,raw)
        a,raw=loaded['.summary.json'];b,parts=loaded['.parts.json'];r=json.loads(raw)
        assert r['source_head']==spec['source_head']and r['sources_unchanged']and r['status'].startswith('PASS_')
        receipt=dict(run=spec['run'],source_head=r['source_head'],summary_asset=a['id'],summary_sha256=digest(raw),parts_asset=b['id'],parts_sha256=digest(parts),status=r['status'],outputs=r['outputs'],report=r)
        p=ROOT/('docs/evidence/cdr-xor-collector-v15-'+stage+'-pass-20261019.json')
        assert not p.exists(),'Do not overwrite immutable source receipt'
        p.write_text(json.dumps(receipt,indent=2)+'\n');pinned[stage]=receipt
    assert pinned['planes']['report']['physical_source']['summary_sha256']==spec['parent_summary_sha256']
    assert pinned['wire-inputs']['report']['physical_source']['summary_sha256']==spec['parent_summary_sha256']
    assert pinned['binding']['report']['physical_source']['summary_sha256']==pinned['wire-inputs']['summary_sha256']
    assert pinned['rc']['report']['physical_inputs']['summary_sha256']==pinned['wire-inputs']['summary_sha256']
    assert specpath.read_bytes()==rawspec
    # Original native controller creates OUT exclusively, so execute before adding handoff evidence.
    rc=subprocess.call([sys.executable,str(ROOT/'scripts/cloud_cdr_xor_collector_v15_mim_parent_rc.py')],cwd=ROOT)
    if OUT.exists():
        proof=OUT/'extraction-prerequisites.json'
        proof.write_text(json.dumps(dict(spec=spec,spec_sha256=digest(rawspec),receipts=pinned),indent=2)+'\n')
        p=OUT/'result.json'
        if p.exists():
            r=json.loads(p.read_text())
            r['outputs'][str(proof.relative_to(OUT))]=digest(proof.read_bytes())
            r['extraction_prerequisites']={k:{n:v[n]for n in ('run','source_head','summary_asset','summary_sha256','parts_asset','parts_sha256','status')}for k,v in pinned.items()}
            p.write_text(json.dumps(r,indent=2)+'\n')
    assert rc==0,('Native MIM capture failed',rc)
    check()
if __name__=='__main__':main()
