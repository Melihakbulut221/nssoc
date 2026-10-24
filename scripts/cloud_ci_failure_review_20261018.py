#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read immutable failed CI artifacts on a hosted worker; retain exact diagnostics."""
import hashlib,io,json,os,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-ci-failure-review-20261018'
SOURCES=[(39089804846,12122960491,56039,'23e4f0c6c081a615c78ebc630712f33ea8b13c443c3b3c959a8ab5755af61e42','lint'),
    (39088317644,12121864262,1077646,'8f48580f95a7dd98006a7098dbe3cc9b2d5661999d0a6cce735d8ff4da7c0d09','ethernet')]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,records=[])
    try:
        for run,aid,size,digest,kind in SOURCES:
            raw=subprocess.check_output(['gh','api',f'repos/Melihakbulut221/nssoc/actions/artifacts/{aid}/zip'])
            assert len(raw)==size and hashlib.sha256(raw).hexdigest()==digest
            with zipfile.ZipFile(io.BytesIO(raw))as z:
                selected=[n for n in z.namelist()if (kind=='ethernet'and n.endswith('soc_pcie_ethernet.log'))or(kind=='lint'and '/lint-'in n and n.endswith(('.json','.log')))]
                assert selected,(kind,z.namelist());members=[]
                for n in selected:
                    b=z.read(n);assert len(b)<2000000
                    members.append(dict(name=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),text=b.decode()))
                    print('MEMBER',kind,n,flush=True);print(b.decode()[-20000:],flush=True)
            r['records'].append(dict(source_run=run,artifact_id=aid,zip_sha256=digest,zip_bytes=size,members=members))
        r['status']='COMPLETE_CLOUD_READBACK_OF_FAILED_CI_DIAGNOSTICS'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
