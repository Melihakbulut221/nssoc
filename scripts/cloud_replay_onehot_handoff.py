#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Wait for exact native evidence, then prepare one new physical candidate."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-replay-onehot-handoff'
REPO='repos/Melihakbulut221/nssoc/'
SOURCES=[(39059432529,'replay-onehot-native-boot-cloud','5c4137e553a0eb647873bc0c41592259e0b111e0'),
 (39059432338,'pcie-transaction','5c4137e553a0eb647873bc0c41592259e0b111e0'),
 (39059432637,'replay-onehot-bank-read-cloud','5c4137e553a0eb647873bc0c41592259e0b111e0'),
 (39059432485,'replay-onehot-cloud','5c4137e553a0eb647873bc0c41592259e0b111e0')]
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))

def collect_proofs():
    # Dynamic release discovery is allowed only after exact first-attempt
    # workflow/source success. Every raw JSON is pinned and revalidated below.
    rows=[r for r in json.loads((ROOT/'docs/evidence/replay-residue-banked-read-proof-inputs-20261017.json').read_text())if r['kind']=='lcrc']
    assert len(rows)==3
    extra=[]
    for depth,cap in [(2,18),(3,38),(4,38)]:
        for run,group,onehot in [(39059432637,f'replay-onehot-bank-read-replay-d{depth}-b{cap}',False),(39059432485,f'replay-onehot-d{depth}-b{cap}',True)]:
            release=api(f'releases/tags/cloud-results-{run}-1-{group}')
            assets=[x for x in release['assets']if x['name']==f'{group}-{run}-1.summary.json'];assert len(assets)==1
            asset=assets[0];raw=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(asset['id']),'-H','Accept: application/octet-stream']);proof=json.loads(raw)
            digest=hashlib.sha256(raw).hexdigest();assert proof['source_head']=='5c4137e553a0eb647873bc0c41592259e0b111e0'and proof['sources_unchanged']
            assert proof['parameters']==dict(DEPTH=depth,MAX_BYTES=cap)
            assert proof['read_cut']['passed']and proof['read_cut']['returncode']==0 and not proof['read_cut']['counterexample']
            counts=proof['sequential']['counts'];assert proof['sequential']['returncode']==0 and len(counts)==1 and int(counts[0][0])>0 and counts[0][1]=='0'
            if onehot:
                assert proof['status']=='PASS_REPLAY_ONEHOT_CUT_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING'
                assert proof['baseline_sha256']=='1a15c0b9d6cfdfbf5ebed9a61c52901e126ca826008d167ff96bea4218a8f4dc'
                assert proof['candidate_sha256']=='b227c24f3f49bce1d8203a10e2039aabe04b6974466307737627023f60e5bc60'
                assert set(proof['controls'])=={'wrong_byte','wrong_slot'}
                assert all(p['counterexample']and not p['passed']and p['returncode']!=0 for p in proof['controls'].values())
                if depth==4:
                    assert proof['port_tests_executed']and len(proof['ports'])==5
                    expected={(label,top)for label in ['baseline','candidate']for top in ['soc_pcie_replay_tx','soc_pcie_reliable_packets']}|{('wrong_cursor','soc_pcie_replay_tx')}
                    assert {(x['case'],x['top'])for x in proof['ports']}==expected
                    for item in proof['ports']:
                        observed=item['observed_tests'];assert observed['skipped']==0
                        assert observed['passed']+observed['failed']==item['result']['expected_tests']
                        if item['case']=='wrong_cursor':assert item['returncode']!=0 and observed['failed']>0
                        else:assert item['returncode']==0 and observed['failed']==0 and observed['passed']>0
                extra.append(dict(run=run,asset=asset['id'],sha256=digest,report=proof))
            else:
                assert proof['status']=='PASS_TX_BANK_READ_CUT_CONTROLS_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING_ACCEPTANCE'
                rows.append(dict(asset=asset['id'],sha256=digest,source_head=proof['source_head'],kind='replay',parameters=proof['parameters']))
    assert len(rows)==6 and len(extra)==3
    (OUT/'proof-inputs.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'registered-cursor-proofs.json').write_text(json.dumps(extra,indent=2)+'\n')
    return dict(bank_proofs=rows,registered_cursor_proofs=[{k:v for k,v in x.items()if k!='report'}for x in extra])

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
                assert run['event']=='push','Physical source must bind the branch push, not the cancellable PR merge run'
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
        r['independent_proofs']=collect_proofs();save()
        listing=api('actions/runs/39059432529/artifacts?per_page=100');assert listing['total_count']<=100
        matches=[x for x in listing['artifacts']if x['name']=='corrpre-pcie-mbist-native-boot-full']
        assert len(matches)==1 and not matches[0]['expired'];artifact=matches[0]
        raw=subprocess.check_output(['gh','api',REPO+'actions/artifacts/'+str(artifact['id'])+'/zip'])
        digest=hashlib.sha256(raw).hexdigest()
        if artifact.get('digest'):assert artifact['digest']=='sha256:'+digest
        r['artifact']=dict(id=artifact['id'],zip_sha256=digest,bytes=len(raw));save();del raw
        spec=OUT/'verified-boot-source.json'
        subprocess.run([sys.executable,str(ROOT/'scripts/check_pcie_onehot_banked_boot_source.py'),
            '--boot-run','39059432529','--boot-head',SOURCES[0][2],'--artifact',str(artifact['id']),
            '--zip-sha256',digest,'--protocol-run','39059432338','--out',str(spec)],check=True,cwd=ROOT)
        subprocess.run([sys.executable,str(ROOT/'scripts/preserve_replay_onehot_boot_evidence.py'),'--source-spec',str(spec)],check=True,cwd=ROOT)
        proof=json.loads((ROOT/'cloud-corrpre-pcie-mbist-boot-evidence/result.json').read_text())
        assert proof['gate_result']['passed']and proof['gate_result']['sources_unchanged']and proof['source_spec']==json.loads(spec.read_text())
        assert proof['source_run']==39059432529 and proof['original_zip_sha256']==digest
        r.update(status='VERIFIED_RESIDUE_BOOT_PROTOCOL_BANKS_AND_ORIGINAL_NATIVE_ARTIFACT_NOT_PHYSICAL_ACCEPTANCE',source_spec=json.loads(spec.read_text()))
    except BaseException as e:r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
