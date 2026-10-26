#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Expose exact saved headroom JSONs after whole-archive/member authentication."""
import argparse,ast,base64,hashlib,json,os,re,shutil,subprocess,tarfile,traceback
from pathlib import Path,PurePosixPath
from cloud_verified_parts import JoinedParts
from cloud_chunked_results import verify_parts
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
import migrate_outputs_to_cloud as publisher
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/cdr-v59-headroom-json-recovery-methods.json'
OUT=ROOT/'cloud-cdr-v59-headroom-json-recovery'
GROUP='cdr-v59-headroom-json-recovery'
ORIGINAL=40322375915
HEAD='6b43c7f32997a3dec1a37b0221cbdaf5f68933ec'
PREFIX='docs/evidence/cdr-v59-headroom-readback-terminal-20261026'
SELECT=tuple(c+'/'+f for c in ('nominal_early','nominal_late') for f in
 ('diagnosis.json','original-measurements-reproduced.json','restore-proof.json','cache.json','frames.json'))
PASS='PASS_EXACT_EXISTING_HEADROOM_JSONS_NO_RECOMPUTATION'
FALSE=('new_analysis','simulation','native_execution','geometry_changed','extraction','accepted','cdr_accepted','qualified_pex','full_phy_accepted')
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def methods():
    m=json.loads(METHOD.read_bytes())
    for name,h in m['protected'].items():
        p=ROOT/name;assert p.is_file()and not p.is_symlink()and sha(p)==h,name
    assert all(m[k]is False for k in ('native_authorized','simulation_authorized','analysis_authorized','geometry_authorized','extraction_authorized','accepted'))
    assert m['original_run']==ORIGINAL and m['original_source']==HEAD
    return m
def guard(m,kind,env=os.environ):
    assert env.get('GITHUB_ACTIONS')=='true'and env['GITHUB_REPOSITORY']==release.REPO
    assert env['GITHUB_RUN_ATTEMPT']=='1'and re.fullmatch('[0-9a-f]{40}',env['GITHUB_SHA'])
    assert m['source_controls_authorized']is True
    if kind=='recovery':assert m['recovery_authorized']is True
def reference(m):
    paths=[PREFIX+s for s in ('.summary.json','.parts.json','.json')]
    for p in paths:assert sha(ROOT/p)==m['protected'][p]
    summary,manifest,receipt=[json.loads((ROOT/p).read_bytes())for p in paths]
    assert summary['status']=='PASS_EXISTING_CAPTURE_HEADROOM_ANALYSIS_NOT_ACCEPTANCE'
    assert summary['source_head']==HEAD and summary['run_id']==ORIGINAL and summary['run_attempt']==1
    assert summary['source_run']==40219397958 and len(summary['outputs'])==14
    assert [c['case']for c in summary['cases']]==['nominal_early','nominal_late']
    assert set(summary['outputs'])==set(SELECT)|{c+'/'+f for c in ('nominal_early','nominal_late')for f in ('all-critical-native-frames.jsonl','selected-all-native-rows.bin')}
    assert all(summary[k]is False for k in ('new_simulation','new_extraction','geometry_changed','accepted','cdr_accepted','qualified_pex','full_phy_accepted'))
    for c in summary['cases']:
        assert c['original_rejection']is True and c['accepted']is False and c['causality_proven']is False
        assert c['restore_members']==5642 and c['cache']['rows']==113475 and c['cache']['all_native_rows_retained']is True
        assert set(c['targets'])=={'61','62','115','116'}
    assert manifest['source_directory']=='cloud-cdr-v59-cn-headroom-readback'
    assert manifest['stem']=='cdr-v59-cn-headroom-readback-40322375915-1'
    return summary,manifest,receipt
def identity(run,jobs,info,ref,receipt):
    old=receipt['run']
    for key in ('id','head_sha','run_attempt','event','workflow_id','path','head_branch'):
        assert run[key]==old[key],key
    assert run['id']==ORIGINAL and run['head_sha']==HEAD and run['status']=='completed'and run['conclusion']=='success'
    expected={x['name']:x['id']for x in receipt['jobs']['jobs']}
    assert expected=={'controls':121570295285,'readback':121570507854}
    assert len(jobs['jobs'])==2 and {j['name']:j['id']for j in jobs['jobs']}==expected
    for j in jobs['jobs']:
        assert j['run_id']==ORIGINAL and j['head_sha']==HEAD and j['run_attempt']==1 and j['status']=='completed'and j['conclusion']=='success'
    oldrel=receipt['release'];assert info['id']==oldrel['id']==424219618
    release.validate_release(info,ref,oldrel['tag_name'],HEAD)
    fields=('id','name','size','digest')
    assert {tuple(a[k]for k in fields)for a in info['assets']}=={tuple(a[k]for k in fields)for a in oldrel['assets']}
    assert all(a['state']=='uploaded'for a in info['assets'])
def download(asset,target):
    assert not target.exists()
    with target.open('xb')as f:
        p=subprocess.run(['gh','api','repos/'+release.REPO+'/releases/assets/'+str(asset['id']),'-H','Accept: application/octet-stream','--allow-escape-sequences'],stdout=f)
    assert p.returncode==0 and target.stat().st_size==asset['size']and 'sha256:'+sha(target)==asset['digest']
def relative(name,prefix):
    assert isinstance(name,str)and name and chr(92)not in name and '\x00'not in name and ':'not in name
    p=PurePosixPath(name)
    assert str(p)==name and not p.is_absolute()and '..'not in p.parts and p.parts[0]==prefix
    return str(p.relative_to(prefix))
def extract(manifest,parts_dir,dest,outer,summary_hash):
    assert not dest.exists();dest.mkdir()
    archive=verify_parts(manifest,parts_dir)
    expected={**outer['outputs'],'result.json':summary_hash}
    wanted=set(SELECT)|{'result.json'}
    assert wanted<=set(expected)
    seen=set();files=set();proof={}
    with JoinedParts([parts_dir/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as tar:
            for item in tar:
                p=relative(item.name,manifest['source_directory'])
                assert item.name not in seen and(item.isfile()or item.isdir())
                seen.add(item.name)
                if item.isdir():continue
                assert p in expected and p not in files;files.add(p)
                target=None
                if p in wanted:
                    target=dest/p;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256();size=0
                handle=target.open('xb')if target else None
                try:
                    with tar.extractfile(item)as f:
                        while b:=f.read(4*1024**2):
                            size+=len(b);h.update(b)
                            if handle:handle.write(b)
                finally:
                    if handle:handle.close()
                assert size==item.size and h.hexdigest()==expected[p],p
                if target:proof[p]=dict(bytes=size,sha256=h.hexdigest())
    assert files==set(expected)and set(proof)==wanted
    return dict(archive=archive,all_member_hashes_verified=len(files),selected=proof)
def only_reserved(group,env,read):
    tag,head=release.context(group,env)
    def lookup(requested):
        assert requested==tag
        info=read('releases/tags/'+tag,missing=True)
        assert info is not None,'Exact-source prerelease absent; never create'
        release.validate_release(info,read('git/ref/tags/'+tag),tag,head)
        return info
    return lookup

def output_name(member):
    assert member in set(SELECT)|{'result.json'}
    return 'headroom-original-'+member.replace('/','--')
def expected_exports(m,summary):
    return {output_name(n):h for n,h in {**{n:summary['outputs'][n]for n in SELECT},'result.json':m['protected'][PREFIX+'.summary.json']}.items()}
def recover(m):
    guard(m,'recovery');summary,manifest,receipt=reference(m)
    run=release.api('actions/runs/'+str(ORIGINAL)+'/attempts/1')
    jobs=release.api('actions/runs/'+str(ORIGINAL)+'/attempts/1/jobs?per_page=100')
    info=release.api('releases/424219618');ref=release.api('git/ref/tags/'+receipt['release']['tag_name'])
    identity(run,jobs,info,ref,receipt)
    transport=OUT/'transport';transport.mkdir()
    assets={a['name']:a for a in info['assets']}
    for suffix in ('.summary.json','.parts.json'):
        asset=assets[manifest['stem']+suffix];target=transport/asset['name'];download(asset,target)
        assert target.read_bytes()==(ROOT/(PREFIX+suffix)).read_bytes()
    assert shutil.disk_usage(OUT).free>=manifest['bytes']+2*1024**3
    for part in manifest['parts']:
        a=assets[part['name']];assert a['size']==part['bytes']and a['digest']=='sha256:'+part['sha256']
        download(a,transport/part['name'])
    saved=OUT/'verified'
    proof=extract(manifest,transport,saved,summary,m['protected'][PREFIX+'.summary.json'])
    assert proof['all_member_hashes_verified']==15 and set(proof['selected'])==set(SELECT)|{'result.json'}
    assert (saved/'result.json').read_bytes()==(ROOT/(PREFIX+'.summary.json')).read_bytes()
    exports=OUT/'json';exports.mkdir()
    for member,record in proof['selected'].items():
        data=(saved/member).read_bytes()
        # Validate syntax only; never recompute, round or rewrite any diagnostic.
        json.loads(data);target=exports/output_name(member);target.write_bytes(data)
        assert sha(target)==record['sha256']
    assert {p.name:sha(p)for p in exports.iterdir()}==expected_exports(m,summary)
    return proof
def publication_files(m):
    assert OUT.is_dir()and not OUT.is_symlink()
    result=OUT/'result.json';assert result.is_file()and not result.is_symlink()
    r=json.loads(result.read_bytes())
    assert r['source_head']==os.environ['GITHUB_SHA']and r['run_id']==int(os.environ['GITHUB_RUN_ID'])and r['run_attempt']==1
    assert r['original_run']==ORIGINAL and r['original_source']==HEAD and all(r[k]is False for k in FALSE)
    assert r['status']in ('RUNNING','FAIL_EXACT_JSON_RECOVERY',PASS)
    if r['status']!=PASS:return [result]
    summary,manifest,_=reference(m);expected=expected_exports(m,summary)
    assert r['member_proof']['all_member_hashes_verified']==15 and set(r['member_proof']['selected'])==set(SELECT)|{'result.json'}
    assert r['member_proof']['archive']==manifest['verification']
    for name,record in r['member_proof']['selected'].items():
        assert record['sha256']==expected[output_name(name)] and type(record['bytes'])is int and record['bytes']>0
    path=OUT/'json';assert path.is_dir()and not path.is_symlink()
    found={}
    for p in path.iterdir():
        assert p.is_file()and not p.is_symlink()and p.name in expected
        found[p.name]=sha(p);assert found[p.name]==expected[p.name]
    assert found==expected and r['outputs']==expected
    return [result]+[path/name for name in sorted(expected)]
def publish(m):
    guard(m,'recovery');waiter.wait(GROUP,os.environ)
    files=publication_files(m);tag,_=release.context(GROUP,os.environ)
    previous=publisher.release;publisher.release=only_reserved(GROUP,os.environ,release.api)
    proof=dict(status='RUNNING',assets=[])
    try:
        for p in files:
            before=sha(p);proof['assets'].append(publisher.publish(p,tag));assert sha(p)==before
        proof['status']='PASS_EXACT_JSON_ASSETS_PUBLISHED_NO_RECOMPUTATION'
    except BaseException as e:proof.update(status='FAIL_PUBLICATION',error=repr(e));raise
    finally:publisher.release=previous;write(OUT/'publication.json',proof)
    return proof
def emit(path,marker):
    data=path.read_bytes()
    assert len(data)<=4*1024**2,'Complete file remains durable; console limit exceeded'
    encoded=base64.b64encode(data).decode()
    print(marker+'_BEGIN '+json.dumps(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),chunks=(len(encoded)+4095)//4096)),flush=True)
    for i in range(0,len(encoded),4096):print(marker+'_CHUNK '+str(i//4096)+' '+encoded[i:i+4096],flush=True)
    print(marker+'_END',flush=True)
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--recover',action='store_true');g.add_argument('--publish',action='store_true');a=p.parse_args()
    m=methods();guard(m,'recovery')
    if a.publish:print(json.dumps(publish(m),indent=2));return
    waiter.wait(GROUP,os.environ);OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,
        original_run=ORIGINAL,original_source=HEAD,**{k:False for k in FALSE})
    try:
        result['member_proof']=recover(m)
        result['outputs']={p.name:sha(p)for p in (OUT/'json').iterdir()}
        methods();result['status']=PASS
    except BaseException as e:result.update(status='FAIL_EXACT_JSON_RECOVERY',error=repr(e),traceback=traceback.format_exc());raise
    finally:write(OUT/'result.json',result);emit(OUT/'result.json','CDR_HEADROOM_JSON_RECOVERY')
if __name__=='__main__':main()
