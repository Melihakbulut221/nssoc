#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind residue replay and unchanged LCRC proofs to exact native chip sources."""
import argparse,base64,hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def main():
    p=argparse.ArgumentParser()
    for name in ('boot-run','artifact','protocol-run'):p.add_argument('--'+name,type=int,required=True)
    for name in ('boot-head','zip-sha256'):p.add_argument('--'+name,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert re.fullmatch('[0-9a-f]{40}',a.boot_head)and re.fullmatch('[0-9a-f]{64}',a.zip_sha256)
    run=api('actions/runs/'+str(a.boot_run));protocol=api('actions/runs/'+str(a.protocol_run))
    assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==a.boot_head
    assert run['path']=='.github/workflows/replay-onehot-native-boot-cloud.yml'
    assert protocol['status']=='completed'and protocol['conclusion']=='success'
    assert protocol['path']=='.github/workflows/pcie-transaction.yml'
    artifact=api('actions/artifacts/'+str(a.artifact))
    assert artifact['workflow_run']['id']==a.boot_run and not artifact['expired']
    assert artifact['name']=='corrpre-pcie-mbist-native-boot-full'
    rows=json.loads((ROOT/'cloud-replay-onehot-handoff/proof-inputs.json').read_text())
    assert len(rows)==6 and len({r['asset']for r in rows})==6
    heads={kind:{a.boot_head,protocol['head_sha'],os.environ['GITHUB_SHA']}for kind in ('replay','lcrc')};proofs=[]
    expected_cases={('replay',2,18),('replay',3,38),('replay',4,38),('lcrc',4),('lcrc',8),('lcrc',9)}
    actual_cases=set()
    for row in rows:
        raw=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(row['asset']),'-H','Accept: application/octet-stream'])
        assert hashlib.sha256(raw).hexdigest()==row['sha256']
        proof=json.loads(raw)
        assert proof['source_head']==row['source_head']and proof['sources_unchanged']
        assert proof['status']=='PASS_TX_BANK_READ_CUT_CONTROLS_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING_ACCEPTANCE'
        assert proof['kind']==row['kind']and proof['parameters']==row['parameters']
        assert proof['read_cut']['passed']and not proof['read_cut']['counterexample']and proof['read_cut']['returncode']==0
        expected_faults={'wrong_byte','wrong_slot'}if row['kind']=='replay'else {'wrong_word','wrong_order'}
        assert len(proof['controls'])==2 and {c['fault']for c in proof['controls']}==expected_faults
        assert all(c['counterexample']and not c['passed']and c['returncode']!=0 for c in proof['controls'])
        counts=proof['sequential']['counts']
        assert proof['sequential']['returncode']==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0
        params=row['parameters']
        case=('replay',params['DEPTH'],params['MAX_BYTES'])if row['kind']=='replay'else ('lcrc',params['MAX_TLP_DWORDS'])
        assert case not in actual_cases;actual_cases.add(case)
        module='soc_pcie_replay_tx'if row['kind']=='replay'else 'soc_pcie_lcrc_tx'
        path='hw/soc/rtl/pcie/'+module+'.v'
        content=base64.b64decode(api('contents/'+path+'?ref='+row['source_head'])['content'])
        actual_sha=hashlib.sha256(content).hexdigest()
        recorded=[digest for p,digest in proof['sources'].items()if p.endswith('/'+path)]
        assert recorded==[actual_sha],'Proof source differs from module at its claimed revision'
        heads[row['kind']].add(proof['source_head']);proofs.append(row)
    assert actual_cases==expected_cases

    # Each module must match its own proofs and the actual protocol/boot/current
    # sources. An old proof for the unchanged LCRC cannot validate changed replay.
    source_hashes={}
    for module in ('soc_pcie_replay_tx','soc_pcie_lcrc_tx'):
        path='hw/soc/rtl/pcie/'+module+'.v';values={}
        for head in sorted(heads['replay'if module=='soc_pcie_replay_tx'else'lcrc']):
            data=base64.b64decode(api('contents/'+path+'?ref='+head)['content'])
            values[head]=hashlib.sha256(data).hexdigest()
        assert len(set(values.values()))==1,(module,values)
        source_hashes[path]=values
    # Every other RTL source must match between the protocol and boot commits.
    rtl_sets=[]
    for head in (a.boot_head,protocol['head_sha'],os.environ['GITHUB_SHA']):
        tree=api('git/trees/'+head+'?recursive=1');assert not tree['truncated']
        rtl_sets.append({x['path']:x['sha']for x in tree['tree']if x['type']=='blob'and x['path'].startswith('hw/soc/rtl/')})
    assert rtl_sets[0]and all(t==rtl_sets[0]for t in rtl_sets[1:]),'Current, protocol and boot RTL differ'
    assert set(source_hashes['hw/soc/rtl/pcie/soc_pcie_replay_tx.v'].values())=={'b227c24f3f49bce1d8203a10e2039aabe04b6974466307737627023f60e5bc60'},'Wrong registered one-hot candidate'
    result=dict(run=a.boot_run,head=a.boot_head,artifact=a.artifact,zip_sha256=a.zip_sha256,
        protocol_run=a.protocol_run,protocol_head=protocol['head_sha'],proofs=proofs,source_hashes=source_hashes,
        matching_rtl_files=len(rtl_sets[0]),bank_proof_and_protocol_verified=True,
        accepted=False,full_phy_accepted=False,final_timing_complete=False)
    assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS_SOURCE_BOUND_BANK_PROOFS_PROTOCOL_AND_BOOT_METADATA_NOT_PHYSICAL_SIGNOFF')
if __name__=='__main__':main()
