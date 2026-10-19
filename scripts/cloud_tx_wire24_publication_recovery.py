#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover unchanged successful native RC bytes after release publication failed."""
import hashlib,io,json,os,stat,subprocess,sys,time,zipfile
from pathlib import Path,PurePosixPath
from cloud_chunked_results import pack
from migrate_outputs_to_cloud import publish
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc/'
RUN=39340687625
HEAD='1b51dd2c56591b87b3b614c28315d4d44bd51d4f'
ARTIFACT=12228916534
DIGEST='d4cd6d865458e1bc69ff3545105bc52ac93e9ea0186b33258cdceac89f471bbe'
GROUP='tx-fast-wire24-extraction'
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ensure_release(tag):
    for attempt in range(6):
        p=subprocess.run(['gh','api',REPO+'releases/tags/'+tag],capture_output=True)
        if p.returncode==0:return json.loads(p.stdout)
        if '(HTTP 404)'in p.stderr.decode(errors='replace'):
            data=dict(tag_name=tag,target_commitish=HEAD,name=tag,prerelease=True,make_latest='false',
                body='Recovered unchanged native RC results from artifact12228916534 after source run39340687625 passed native extraction but release creation returned HTTP500. Recovery run '+os.environ['GITHUB_RUN_ID']+'. The source run remains failed; no CAD computation rerun or electrical acceptance implied.')
            q=subprocess.run(['gh','api','--method','POST',REPO+'releases','--input','-'],input=json.dumps(data).encode(),capture_output=True)
            if q.returncode==0:return json.loads(q.stdout)
        # Check by tag again before retrying uncertain creation; never duplicate.
        time.sleep(min(30,5*(attempt+1)))
    raise RuntimeError('Release API unavailable; retained recovered evidence must not be overwritten')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source=api('actions/runs/'+str(RUN))
    assert source['head_sha']==HEAD and source['run_attempt']==1 and source['status']=='completed'and source['conclusion']=='failure'
    jobs=api('actions/runs/'+str(RUN)+'/jobs')['jobs'];assert len(jobs)==1
    steps={s['name']:s for s in jobs[0]['steps']}
    assert steps['Extract actual31macro32to1 metal and enforce native RC graph and13fault controls']['conclusion']=='success'
    assert steps['Preserve physical results including rejected geometry']['conclusion']=='failure'
    assert steps['Retain evidence after publication failure']['conclusion']=='success'
    artifact=api('actions/artifacts/'+str(ARTIFACT))
    assert not artifact['expired']and artifact['name']=='tx-fast-wire24-extraction-'+str(RUN)
    assert artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==HEAD
    assert artifact['size_in_bytes']==19967840 and artifact['digest']=='sha256:'+DIGEST
    raw=subprocess.check_output(['gh','api',REPO+'actions/artifacts/'+str(ARTIFACT)+'/zip'])
    assert len(raw)==artifact['size_in_bytes']and sha(raw)==DIGEST
    out=ROOT/'hw/soc/out/cloud-tx-fast-wire24-physical';out.mkdir(parents=True,exist_ok=False)
    members={}
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        entries=[i for i in z.infolist()if not i.is_dir()]
        assert len({i.filename for i in entries})==len(entries)
        matches=[i.filename for i in entries if PurePosixPath(i.filename).name=='extraction-result.json'];assert len(matches)==1
        prefix=matches[0][:-len('extraction-result.json')]
        for info in entries:
            assert info.filename.startswith(prefix)
            name=info.filename[len(prefix):];rel=PurePosixPath(name)
            assert not rel.is_absolute()and '..'not in rel.parts and name and not stat.S_ISLNK(info.external_attr>>16)
            data=z.read(info);assert len(data)==info.file_size
            p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            members[name]=dict(bytes=len(data),sha256=sha(data))
    original=(out/'extraction-result.json').read_bytes();r=json.loads(original)
    assert r['source_head']==HEAD and r['status']=='PASS_ACTUAL_NATIVE_RC_GRAPH_AND_13_FAULT_CONTROLS_REQUIRES_WAVEFORMS'
    assert r['native_geometry_census']==dict(wire_component_count=377,native_electrical_net_count=378,native_device_count=1674,native_terminal_count=4774)
    assert r['physical_source']['summary_sha256']=='00aa1d6cef157845fe73f185e0350b54f372d2c6e0c7dba2773ed629131f6263'
    assert r['capture']['returncode']==0 and r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
    assert r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
    assert len(r['controls']['cases'])==13
    for name,digest in r['physical_source']['report']['outputs'].items():
        assert members[name]['sha256']==digest
    tag=f'cloud-results-{RUN}-1-{GROUP}'
    existing=ensure_release(tag);assert not existing['assets'],'Unexpected existing publication; inspect exact hosted digests before retry'
    stem=f'{GROUP}-{RUN}-1'
    summary=ROOT/(stem+'.summary.json');summary.write_bytes(original)
    manifest=pack(out,stem,ROOT)
    paths=[summary,ROOT/(stem+'.parts.json'),*[ROOT/p['name']for p in manifest['parts']]]
    published=[]
    for path in paths:
        for attempt in range(6):
            try:result=publish(path,tag);break
            except subprocess.CalledProcessError:
                if attempt==5:raise
                time.sleep(min(30,5*(attempt+1)))
        published.append(result)
    assert (out/'extraction-result.json').read_bytes()==original
    assert all(sha((out/n).read_bytes())==d['sha256']for n,d in members.items())
    report=dict(status='PASS_ORIGINAL_NATIVE_EXTRACTION_BYTES_RECOVERED_NO_CAD_RERUN',
        recovery_run=int(os.environ['GITHUB_RUN_ID']),recovery_source_head=os.environ['GITHUB_SHA'],
        original_run=RUN,original_source_head=HEAD,original_run_conclusion='failure',
        original_native_step_conclusion='success',artifact_id=ARTIFACT,artifact_sha256=DIGEST,
        original_summary_sha256=sha(original),published=published,original_files=members,
        qualified_pex=False,electrical_accepted=False,full_phy_accepted=False)
    p=ROOT/'tx-wire24-publication-recovery.json';p.write_text(json.dumps(report,indent=2)+'\n')
    subprocess.run([sys.executable,'scripts/publish_cloud_results.py','--group','tx-wire24-publication-recovery',str(p)],cwd=ROOT,check=True)
    print(json.dumps({k:report[k]for k in ['status','original_summary_sha256','published']}),flush=True)
if __name__=='__main__':main()
