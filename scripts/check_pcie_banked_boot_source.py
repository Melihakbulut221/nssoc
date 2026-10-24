#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind bank proofs and successful native protocol to the actual new boot source."""
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
    assert run['path']=='.github/workflows/corrpre-pcie-mbist-native-boot-cloud.yml'
    assert protocol['status']=='completed'and protocol['conclusion']=='success'
    assert protocol['path']=='.github/workflows/pcie-transaction.yml'
    artifact=api('actions/artifacts/'+str(a.artifact))
    assert artifact['workflow_run']['id']==a.boot_run and not artifact['expired']
    assert artifact['name']=='corrpre-pcie-mbist-native-boot-full'
    rows=json.loads((ROOT/'docs/evidence/pcie-banked-read-proof-inputs-20261017.json').read_text())
    assert len(rows)==6 and len({r['asset']for r in rows})==6
    heads={a.boot_head,protocol['head_sha']};proofs=[]
    for row in rows:
        raw=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(row['asset']),'-H','Accept: application/octet-stream'])
        assert hashlib.sha256(raw).hexdigest()==row['sha256']
        proof=json.loads(raw)
        assert proof['source_head']==row['source_head']and proof['sources_unchanged']
        assert proof['status']=='PASS_TX_BANK_READ_CUT_CONTROLS_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING_ACCEPTANCE'
        assert proof['kind']==row['kind']and proof['parameters']==row['parameters']
        heads.add(proof['source_head']);proofs.append(row)
    # The same exact two changed modules must be used in all proof, protocol and
    # boot commits. A new RTL candidate cannot inherit an earlier green result.
    source_hashes={}
    for module in ('soc_pcie_replay_tx','soc_pcie_lcrc_tx'):
        path='hw/soc/rtl/pcie/'+module+'.v';values={}
        for head in sorted(heads):
            data=base64.b64decode(api('contents/'+path+'?ref='+head)['content'])
            values[head]=hashlib.sha256(data).hexdigest()
        assert len(set(values.values()))==1,(module,values)
        source_hashes[path]=values
    # Every other RTL source must match between the protocol and boot commits.
    rtl_sets=[]
    for head in (a.boot_head,protocol['head_sha']):
        tree=api('git/trees/'+head+'?recursive=1');assert not tree['truncated']
        rtl_sets.append({x['path']:x['sha']for x in tree['tree']if x['type']=='blob'and x['path'].startswith('hw/soc/rtl/')})
    assert rtl_sets[0]and rtl_sets[0]==rtl_sets[1],'Protocol and boot RTL differ'
    result=dict(run=a.boot_run,head=a.boot_head,artifact=a.artifact,zip_sha256=a.zip_sha256,
        protocol_run=a.protocol_run,protocol_head=protocol['head_sha'],proofs=proofs,source_hashes=source_hashes,
        matching_rtl_files=len(rtl_sets[0]),bank_proof_and_protocol_verified=True,
        accepted=False,full_phy_accepted=False,final_timing_complete=False)
    assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS_SOURCE_BOUND_BANK_PROOFS_PROTOCOL_AND_BOOT_METADATA_NOT_PHYSICAL_SIGNOFF')
if __name__=='__main__':main()
