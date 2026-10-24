#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read existing failed cloud-native logs; no simulation or acceptance."""
import hashlib,io,json,os,subprocess,tarfile
def asset(i,digest):
    data=subprocess.check_output(['gh','api',f'repos/Melihakbulut221/nssoc/releases/assets/{i}','-H','Accept: application/octet-stream'])
    assert hashlib.sha256(data).hexdigest()==digest
    return data
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    summary=json.loads(asset(672185904,'916c12c6cb7422915672ecc16c870eccb58f55046263c4510cce2f1601d5c33e'))
    parts=json.loads(asset(672185941,'5d61f5a59ba6f843a3f32f7ce6301247b1f9e20a42524e8dc41a3e5acacf3402'))
    assert summary['source_head']=='f640313c17acf29a302bf9ef06727eda38aa8979'
    assert summary['status']=='REJECTED_INTRINSIC_RESET_DIAGNOSTIC_PRESERVE_ALL_FAILURES'
    raw=asset(672185986,'bfe23f175c0954fdf8abd8f5bee13690ba621623bb995a548e796e27ae447f9a')
    assert len(parts['parts'])==1 and len(raw)==parts['bytes']==10537888
    assert parts['sha256']==parts['parts'][0]['sha256']==hashlib.sha256(raw).hexdigest()
    result=dict(status='READBACK_EXISTING_FAILED_INTRINSIC_LOGS_NO_NATIVE_EXECUTION',source_run=40092958226,
      summary_sha256='916c12c6cb7422915672ecc16c870eccb58f55046263c4510cce2f1601d5c33e',cases={},
      native_execution=False,full_PHY_accepted=False)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as ar:
        members=ar.getmembers();names=[m.name for m in members];assert len(names)==len(set(names))
        for case,row in summary['native_cases'].items():
            p=case+'/native.log';matches=[m for m in members if m.name=='cloud-tx-phase-async-preset-intrinsic/'+p]
            assert len(matches)==1 and matches[0].isfile()and matches[0].size<131072
            data=ar.extractfile(matches[0]).read();assert hashlib.sha256(data).hexdigest()==summary['outputs'][p]
            result['cases'][case]=dict(native_log=data.decode(),sha256=summary['outputs'][p],
              returncode=row['returncode'],elapsed_s=row['elapsed_s'],original_reader_error=row['error'])
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
