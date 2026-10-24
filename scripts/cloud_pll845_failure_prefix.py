#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read only bounded metadata from one verified published PLL archive prefix."""
import hashlib,json,os,subprocess,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-failure-prefix'
REPO='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);r=dict(status='OBSERVING_PREFIX',source_head=os.environ['GITHUB_SHA'],whole_archive_verified=False,native_activation_allowed=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=api('actions/runs/39551551389')
        assert run['head_sha']=='21ceb87f7b83008497eb4cc7e44fca5973e605b1'
        job=api('actions/jobs/119061816414')
        failed=[s for s in job['steps']if s['name'].startswith('Run whole845')]
        assert len(failed)==1 and failed[0]['conclusion']=='failure'
        r['observed_native_failure']=failed[0]
        asset=api('releases/assets/661613918')
        assert asset['name']=='pll845-native-acquisition-initial-39551551389-1.tar.gz.part0000'
        assert asset['size']==268435456 and asset['digest']=='sha256:45d946227bc7948bc560529a6e7119709ecc353a8d2c2aada6594f6238fb0d41'
        p=Path(os.environ['RUNNER_TEMP'])/'pll845-prefix-part0000'
        with p.open('xb')as f:subprocess.run(['gh','api','-H','Accept: application/octet-stream',REPO+'releases/assets/661613918'],stdout=f,check=True)
        assert p.stat().st_size==asset['size']and 'sha256:'+sha(p)==asset['digest']
        r['verified_single_part']={k:asset[k]for k in ('id','name','size','digest')}
        r['members_seen']=[];r['metadata']={};budget=0
        try:
            with tarfile.open(p,mode='r|gz')as t:
                for m in t:
                    q=PurePosixPath(m.name)
                    assert not q.is_absolute()and'..'not in q.parts and q.parts[0]=='cloud-pll845-native-acquisition'
                    r['members_seen'].append(dict(name=m.name,size=m.size,type=m.type.decode(errors='replace')))
                    if m.isfile()and m.size>16*1024**2:
                        r['stopped_before_large_member']=m.name;break
                    budget+=m.size
                    if budget>32*1024**2 or len(r['members_seen'])>2048:
                        r['stopped_at_metadata_budget']=True;break
                    if m.isfile()and(m.name.endswith(('.json','.log'))or 'diagnostic'in m.name):
                        f=t.extractfile(m);raw=f.read();assert len(raw)==m.size
                        name='metadata-'+str(len(r['metadata'])).zfill(4)+'.txt'
                        (OUT/name).write_bytes(raw)
                        entry=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),saved_as=name)
                        if m.name.endswith('.json'):
                            try:entry['json']=json.loads(raw)
                            except (ValueError,UnicodeDecodeError):entry['valid_json']=False
                        r['metadata'][m.name]=entry
        except (EOFError,tarfile.ReadError)as e:r['incomplete_prefix_boundary']=repr(e)
        # This is a read-only observation. Neither source capsule nor live publisher is touched.
        assert p.stat().st_size==asset['size']and 'sha256:'+sha(p)==asset['digest']
        r['status']='OBSERVED_VERIFIED_SINGLE_PART_METADATA_NOT_COMPLETE_CHECKPOINT'
    except BaseException as e:r.update(status='FAIL_PREFIX_OBSERVATION',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
