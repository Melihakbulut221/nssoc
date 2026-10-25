#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover retained failed-screen artifacts on hosted runners without resimulation."""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
from publish_cloud_results import publish_results

def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    p=argparse.ArgumentParser();p.add_argument('--length',choices=['1.2','1.6'],required=True);p.add_argument('--case',choices=['nominal_early','nominal_late'],required=True);a=p.parse_args()
    name=f'cdr-load-resistor-screen-{a.length}-{a.case}-39149512255'
    pin=json.loads(Path('docs/evidence/cdr-load-screen-retained-artifacts-20261018.json').read_text())
    selected=[x for x in pin['artifacts']if x['name']==name];assert len(selected)==1;x=selected[0]
    assert x['workflow_run']['id']==39149512255 and x['workflow_run']['head_sha']==pin['source_head']
    folder=Path('recovered-screen');folder.mkdir(exist_ok=False);archive=Path('retained.zip')
    with archive.open('wb')as f:subprocess.run(['gh','api',f"repos/Melihakbulut221/nssoc/actions/artifacts/{x['id']}/zip"],stdout=f,check=True)
    assert archive.stat().st_size==x['size_in_bytes'] and 'sha256:'+sha(archive)==x['digest']
    with zipfile.ZipFile(archive)as z:
        assert len(set(z.namelist()))==len(z.namelist())
        for i in z.infolist():
            q=Path(i.filename);assert not q.is_absolute()and '..'not in q.parts and not((i.external_attr>>16)&0o170000==0o120000)
        z.extractall(folder)
    archive.unlink()
    report=json.loads((folder/'result.json').read_text())
    assert report['source_head']==pin['source_head']and report['case']==a.case
    assert report['status']=='REJECTED_LOAD_RESISTOR_SCREEN'and report['sources_unchanged']and report['returncode']==0 and not report['diagnostics']
    assert not report['accepted']and not report['full_phy_accepted']and not report['load_resistor_screen']['actual_candidate_layout_verified']
    for n,h in report['outputs'].items():
        q=Path(n);assert not q.is_absolute()and '..'not in q.parts
        assert sha(folder/q)==h,n
    assert len(report['load_resistor_screen']['changes'])==16
    group=f'cdr-load-screen-recovered-{a.length.replace(".","p")}-{a.case}'
    stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    Path(stem+'.summary.json').write_bytes((folder/'result.json').read_bytes())
    receipt=dict(status='RECOVERED_ORIGINAL_REJECTED_SCREEN_NOT_ACCEPTED',source_artifact=x,original_result_sha256=sha(folder/'result.json'),verified_output_count=len(report['outputs']),simulation_rerun=False,accepted=False)
    Path(stem+'.recovery.json').write_text(json.dumps(receipt,indent=2)+'\n')
    subprocess.run([sys.executable,'scripts/cloud_chunked_results.py','--directory',str(folder),'--stem',stem],check=True)
    manifest=Path(stem+'.parts.json');m=json.loads(manifest.read_text())
    print(json.dumps(publish_results(group,[stem+'.summary.json',stem+'.recovery.json',str(manifest),*[p['name']for p in m['parts']]])),flush=True)
if __name__=='__main__':main()
