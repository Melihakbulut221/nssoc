#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Wait for exact native evidence, then prepare one new physical candidate."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-replay-crc-handoff'
REPO='repos/Melihakbulut221/nssoc/'
SOURCES=[(39041981816,'replay-crc-native-boot-cloud','295bb24044d5ea7ba8eefdeeb0ea22eb18df34ed'),
 (39041981763,'pcie-transaction','295bb24044d5ea7ba8eefdeeb0ea22eb18df34ed'),
 (39041981839,'replay-crc-bank-read-cloud','295bb24044d5ea7ba8eefdeeb0ea22eb18df34ed'),
 (39042052313,'replay-crc-cloud','6e33442ffcd468596b8aba319d4f27e6f18e1811')]
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='WAITING_FOR_SOURCE'if a.wait else'VALIDATING_SOURCE',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        deadline=time.monotonic()+18000;previous=None
        while True:
            rows=[]
            for number,workflow,head in SOURCES:
                run=api('actions/runs/'+str(number))
                assert run['head_sha']==head and run['head_branch']=='codex/complete-open-work'and run['run_attempt']==1
                assert run['path']=='.github/workflows/'+workflow+'.yml'
                row={k:run[k]for k in ('id','head_sha','status','conclusion','html_url')};rows.append(row)
                assert run['status']!='completed'or run['conclusion']=='success',('Source terminal unsuccessful; no successor',row)
            r['sources']=rows;save()
            if rows!=previous:print(json.dumps(rows),flush=True);previous=rows
            if all(x['status']=='completed'for x in rows):break
            assert a.wait,'Source not complete; wait job must finish before native preparation'
            assert time.monotonic()<deadline,'Observation deadline; sources not cancelled or restarted'
            time.sleep(60)
        if a.wait:
            r['status']='EXACT_NATIVE_SOURCES_COMPLETE_READY_FOR_INDEPENDENT_REVALIDATION';return
        listing=api('actions/runs/39041981816/artifacts?per_page=100');assert listing['total_count']<=100
        matches=[x for x in listing['artifacts']if x['name']=='corrpre-pcie-mbist-native-boot-full']
        assert len(matches)==1 and not matches[0]['expired'];artifact=matches[0]
        raw=subprocess.check_output(['gh','api',REPO+'actions/artifacts/'+str(artifact['id'])+'/zip'])
        digest=hashlib.sha256(raw).hexdigest()
        if artifact.get('digest'):assert artifact['digest']=='sha256:'+digest
        r['artifact']=dict(id=artifact['id'],zip_sha256=digest,bytes=len(raw));save();del raw
        spec=OUT/'verified-boot-source.json'
        subprocess.run([sys.executable,str(ROOT/'scripts/check_pcie_residue_banked_boot_source.py'),
            '--boot-run','39041981816','--boot-head',SOURCES[0][2],'--artifact',str(artifact['id']),
            '--zip-sha256',digest,'--protocol-run','39041981763','--out',str(spec)],check=True,cwd=ROOT)
        subprocess.run([sys.executable,str(ROOT/'scripts/preserve_replay_crc_boot_evidence.py'),'--source-spec',str(spec)],check=True,cwd=ROOT)
        proof=json.loads((ROOT/'cloud-corrpre-pcie-mbist-boot-evidence/result.json').read_text())
        assert proof['gate_result']['passed']and proof['gate_result']['sources_unchanged']and proof['source_spec']==json.loads(spec.read_text())
        assert proof['source_run']==39041981816 and proof['original_zip_sha256']==digest
        r.update(status='VERIFIED_RESIDUE_BOOT_PROTOCOL_BANKS_AND_ORIGINAL_NATIVE_ARTIFACT_NOT_PHYSICAL_ACCEPTANCE',source_spec=json.loads(spec.read_text()))
    except BaseException as e:r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
