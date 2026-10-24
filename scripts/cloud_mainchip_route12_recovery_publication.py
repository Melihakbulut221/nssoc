#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Republish exact recovered evidence; no routing, native restore or inner image scan."""
import argparse,copy,hashlib,io,json,os,re,shutil,stat,subprocess,tempfile,traceback,zipfile
from pathlib import Path,PurePosixPath
import cloud_mainchip_route12_artifact_recovery as original
import ensure_cloud_tested_source_release as release
from migrate_outputs_to_cloud import publish
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-route12-recovery-publication'
METHOD=ROOT/'scripts/mainchip-route12-recovery-publication-methods.json'
RUN=40110502492
HEAD='ac1740af745fe3d62960b1e62297096c619f0c5d'
JOB=120925285512
ARTIFACT=12567520376
ZIP_BYTES=1484547934
ZIP_SHA='3d9c5f0576457f02c2a0c0783340ebc9bb71e2b6c84d55f79a1f0914e21bc4ff'
RESULT_PATH='docs/evidence/mainchip-route12-recovery-readback-result-20261024.json'
RESULT_SHA='ef688f4fbb6b238618b7e9c46a4cd7297b1aa809db020ccaa52bffd28d2e3468'
ARCHIVE='original-artifact-12564886005.zip'
ARCHIVE_PROOF={'bytes':1560640815,'sha256':'6231b9523ba15bcabac5e65b166648523a742c146321c7806ff97d01e6272e56'}
GROUP='mainchip-route12-recovery-publication'
FLAGS=dict(native_execution=False,native_process_restored=False,saved_process_validated=False,
 route_complete=False,continuation_accepted=False,final_timing_complete=False,full_phy_accepted=False)
def sha(data):return hashlib.sha256(data).hexdigest()
def file_record(p):return dict(bytes=p.stat().st_size,sha256=original.file_sha(p))
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def pins():
    m=json.loads(METHOD.read_text())
    for path,h in m['protected'].items():assert original.file_sha(ROOT/path)==h,path
    original.methods()
    return m
def safe(name):
    p=PurePosixPath(name)
    assert name and str(p)==name and not p.is_absolute()
    assert all(ord(c)>=32 and ord(c)!=127 for c in name)
    assert all(c not in ('','.','..')for c in p.parts)and '\\'not in name and ':'not in name
    return name
def expected(result,raw):
    assert sha(raw)==RESULT_SHA and len(raw)==45327 and json.loads(raw)==result
    assert result['status']=='PASS_LOSSLESS_MAINCHIP_EVIDENCE_RECOVERY_ORIGINAL_ROUTING_REMAINS_REJECTED'
    assert int(result['run_id'])==RUN and result['source_head']==HEAD
    assert result['all_65_original_members_retained']and result['native_capsule_not_accepted']
    assert all(result[k]is False for k in FLAGS)
    assert result['archive_transport']==dict(**ARCHIVE_PROOF,complete_stream_verified=True)
    d=result['diagnosis']
    assert d['all_65_members_crc_and_sha256_verified']and d['all_original_recorded_member_hashes_verified']
    assert d['unchanged_full_native_log']and d['checkpoint_image_hashes_reproduced']
    assert d['saved_process_validated']is False and d['continuation_accepted']is False
    m=copy.deepcopy(result['outputs'])
    assert len(m)==39 and m[ARCHIVE]==ARCHIVE_PROOF and 'result.json'not in m
    m['result.json']=dict(bytes=len(raw),sha256=sha(raw))
    for n,v in m.items():
        safe(n);assert type(v['bytes'])is int and v['bytes']>=0 and set(v)=={'bytes','sha256'}
        assert re.fullmatch('[0-9a-f]{64}',v['sha256'])
        if v['bytes']==0:assert v['sha256']==sha(b'')
    return m
def identity(run,job,artifact):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='failure'
    assert run['path']=='.github/workflows/mainchip-route12-artifact-recovery-cloud.yml'
    assert job['id']==JOB and job['run_id']==RUN and job['head_sha']==HEAD
    assert job['name']=='recovery'and job['status']=='completed'and job['conclusion']=='failure'
    steps={s['name']:s['conclusion']for s in job['steps']}
    assert steps['Recover only the exact failed Actions artifact without native execution']=='success'
    assert steps['Publish verified original bytes and all small diagnostic evidence']=='failure'
    assert steps['Preserve failed recovery or publication byte for byte']=='success'
    assert artifact['id']==ARTIFACT and artifact['workflow_run']['id']==RUN
    assert artifact['workflow_run']['head_sha']==HEAD and not artifact['expired']
    assert artifact['name']=='mainchip-route12-artifact-recovery-fallback'
    assert artifact['size_in_bytes']==ZIP_BYTES and artifact['digest']=='sha256:'+ZIP_SHA
def evidence():
    raw=(ROOT/RESULT_PATH).read_bytes();result=json.loads(raw);manifest=expected(result,raw)
    actual=(api('actions/runs/'+str(RUN)),api('actions/jobs/'+str(JOB)),api('actions/artifacts/'+str(ARTIFACT)))
    identity(*actual)
    return result,manifest,actual
def download(path):
    p=subprocess.Popen(['gh','api','--allow-escape-sequences',
      'repos/Melihakbulut221/nssoc/actions/artifacts/'+str(ARTIFACT)+'/zip'],stdout=subprocess.PIPE)
    try:
        proof=original.consume(p.stdout,path,ZIP_BYTES,ZIP_SHA)
        assert p.wait()==0,'Artifact stream command failed after bytes'
    except BaseException:
        if p.poll()is None:p.kill()
        p.wait();raise
    finally:p.stdout.close()
    return proof
def extract(path,destination,manifest):
    destination.mkdir(exist_ok=False);seen={}
    with zipfile.ZipFile(path)as z:
        items=original.index(z,len(manifest))
        assert set(items)==set(manifest),'Fallback member set changed'
        for name,info in items.items():
            safe(name);v=manifest[name];assert info.file_size==v['bytes'],'Fallback member size changed'
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info)as inp:original.consume(inp,target,v['bytes'],v['sha256'])
            seen[name]=file_record(target)
    assert seen==manifest
    return dict(files=len(seen),all_outer_CRC_and_member_hashes_verified=True,
      all_expected_members_byte_identical=True,inner_archives_not_decoded=True)
def plan(root,manifest):
    for n,v in manifest.items():
        p=root/safe(n)
        assert p.is_file()and not p.is_symlink()and file_record(p)==v,('Changed restored file',n)
    assert ARCHIVE in manifest and manifest[ARCHIVE]['bytes']>0
    empty=[dict(path=n,release_asset_name=Path(n).name,**v)for n,v in sorted(manifest.items())if v['bytes']==0]
    files=[n for n,v in sorted(manifest.items())if v['bytes']>0]
    assert len({Path(n).name for n in manifest})==len(manifest),'Duplicate release basename'
    return dict(nonempty_files=files,empty_files=empty,all_original_files=len(manifest),
      archive=dict(path=ARCHIVE,**manifest[ARCHIVE]),empty_standalone_files_retained_on_runner=True,
      empty_standalone_uploads=0)
def validate_plan(p,manifest):
    assert p['all_original_files']==len(manifest)and p['empty_standalone_uploads']==0
    assert p['empty_standalone_files_retained_on_runner']is True
    assert p['archive']==dict(path=ARCHIVE,**manifest[ARCHIVE])
    assert p['nonempty_files']==[n for n,v in sorted(manifest.items())if v['bytes']>0]
    assert p['empty_files']==[dict(path=n,release_asset_name=Path(n).name,**v)
      for n,v in sorted(manifest.items())if v['bytes']==0]
def send_nonempty(root,p,manifest,tag,verify,send=publish):
    validate_plan(p,manifest)
    # The zero-byte omission is explicit, and every original byte remains in
    # the independently authenticated original ZIP and preserved local files.
    inventory=root/'empty-file-inventory.json'
    assert not inventory.exists()
    write(inventory,dict(schema='exact-empty-recovery-files-v1',source_recovery_run=RUN,
      source_recovery_head=HEAD,original_result_sha256=RESULT_SHA,
      original_archive=p['archive'],empty_files=p['empty_files'],
      every_original_file_retained=True,empty_bytes_not_padded_or_rewritten=True,**FLAGS))
    receipts=[]
    for name in p['nonempty_files']+['empty-file-inventory.json']:
        path=root/name
        assert path.stat().st_size>0
        if name in manifest:assert file_record(path)==manifest[name]
        verify();receipts.append(send(path,tag))
    assert plan(root,manifest)==p
    return receipts
def controls(result,manifest,actual):
    bad=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,zipfile.BadZipFile,EOFError):bad.append(name)
        else:raise AssertionError('Accepted publication fault '+name)
    for label,which,key,val in [
      ('recovery-head',0,'head_sha','0'*40),('recovery-live',0,'status','in_progress'),
      ('recovery-not-failed-publication',0,'conclusion','success'),('recovery-attempt',0,'run_attempt',2),
      ('recovery-job',1,'id',1),('fallback-id',2,'id',1),('fallback-size',2,'size_in_bytes',1),
      ('fallback-hash',2,'digest','sha256:'+'0'*64),('fallback-expired',2,'expired',True)]:
        q=copy.deepcopy(actual);q[which][key]=val;reject(label,lambda:identity(*q))
    for label,name,val in [
      ('hide-readback-failure','Recover only the exact failed Actions artifact without native execution','failure'),
      ('invent-publication-pass','Publish verified original bytes and all small diagnostic evidence','success'),
      ('fallback-not-saved','Preserve failed recovery or publication byte for byte','failure')]:
        q=copy.deepcopy(actual)
        next(s for s in q[1]['steps']if s['name']==name)['conclusion']=val
        reject(label,lambda:identity(*q))
    raw=(ROOT/RESULT_PATH).read_bytes()
    reject('original-proof-truncated',lambda:expected(result,raw[:-1]))
    q=copy.deepcopy(result);q['outputs'][ARCHIVE]['sha256']='0'*64
    reject('original-proof-object-detached',lambda:expected(q,raw))
    q=copy.deepcopy(result);q['route_complete']=True
    reject('invent-original-route-acceptance',lambda:expected(q,json.dumps(q).encode()))
    with tempfile.TemporaryDirectory(prefix='publication-controls-')as td:
        root=Path(td);good=root/'good';good.mkdir()
        bodies={ARCHIVE:b'opaque original archive fixture\x00\xff','small/empty.log':b'','small/native.log':b'unchanged evidence\n'}
        fixture={n:dict(bytes=len(b),sha256=sha(b))for n,b in bodies.items()}
        for n,b in bodies.items():
            p=good/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        p=plan(good,fixture);validate_plan(p,fixture);sent=[];verified=[]
        def fake_send(path,tag):
            assert path.stat().st_size>0 and tag=='fixture'
            sent.append(path.name);return dict(name=path.name,**file_record(path))
        receipts=send_nonempty(good,p,fixture,'fixture',lambda:verified.append(True),fake_send)
        assert len(sent)==len(verified)==3 and 'empty.log'not in sent
        assert (good/'small/empty.log').read_bytes()==b''and plan(good,fixture)==p
        for label,edit in [
          ('omit-empty-inventory',lambda q:q['empty_files'].clear()),
          ('invent-empty-file',lambda q:q['empty_files'].append(q['empty_files'][0])),
          ('upload-empty-file',lambda q:q['nonempty_files'].append('small/empty.log')),
          ('omit-nonempty',lambda q:q['nonempty_files'].pop()),
          ('replace-archive-hash',lambda q:q['archive'].update(sha256='0'*64))]:
            q=copy.deepcopy(p);edit(q);reject(label,lambda:validate_plan(q,fixture))
        (good/'small/native.log').write_bytes(b'changed')
        reject('changed-publication-file',lambda:plan(good,fixture))
        (good/'small/native.log').write_bytes(bodies['small/native.log'])
        (good/'small/empty.log').write_bytes(b'\n')
        reject('padded-empty-file',lambda:plan(good,fixture))
        (good/'small/empty.log').write_bytes(b'')
        alias=copy.deepcopy(fixture);alias['empty.log']=alias['small/empty.log'];(good/'empty.log').write_bytes(b'')
        reject('duplicate-release-basename',lambda:plan(good,alias))
        failed=root/'failed-publication';failed.mkdir()
        for n,b in bodies.items():
            q=failed/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
        def failing_send(path,tag):raise RuntimeError('fixture publisher failure')
        try:send_nonempty(failed,p,fixture,'fixture',lambda:None,failing_send)
        except RuntimeError as exc:
            assert str(exc)=='fixture publisher failure';bad.append('upload-failure-propagates')
        else:raise AssertionError('Publication failure was swallowed')
        assert plan(failed,fixture)==p and (failed/'small/empty.log').read_bytes()==b''
        def archive(entries,target):
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED)as z:
                for n,b,kind in entries:
                    info=zipfile.ZipInfo(n);info.create_system=3;info.external_attr=(kind|0o600)<<16
                    z.writestr(info,b)
        entries=[(n,b,stat.S_IFREG)for n,b in bodies.items()]
        a=root/'good.zip';archive(entries,a);positive=extract(a,root/'restore-good',fixture)
        assert positive['files']==3 and plan(root/'restore-good',fixture)==p
        faults=[
          ('outer-extra',entries+[('extra',b'x',stat.S_IFREG)],fixture),
          ('outer-missing',entries[:-1],fixture),
          ('outer-duplicate',[entries[0],entries[0],entries[2]],fixture),
          ('outer-traversal',[('../escape',entries[0][1],stat.S_IFREG)]+entries[1:],fixture),
          ('outer-symlink',[(entries[0][0],entries[0][1],stat.S_IFLNK)]+entries[1:],fixture),
          ('outer-bad-size',entries,{**fixture,'small/native.log':dict(bytes=1,sha256=fixture['small/native.log']['sha256'])}),
          ('outer-bad-member-hash',entries,{**fixture,'small/native.log':dict(bytes=len(bodies['small/native.log']),sha256='0'*64)})]
        for label,rows,m in faults:
            a=root/(label+'.zip');archive(rows,a)
            reject(label,lambda:extract(a,root/(label+'-out'),m))
        a=root/'outer-crc.zip';archive(entries,a);raw=a.read_bytes()
        a.write_bytes(raw.replace(b'unchanged evidence\n',b'Xnchanged evidence\n',1))
        reject('outer-CRC-corruption',lambda:extract(a,root/'crc-out',fixture))
    assert len(bad)==32,len(bad)
    return dict(status='PASS_PUBLICATION_PLAN_OUTER_ARCHIVE_AND32_FAULTS',
      rejected=bad,positive_exact_outer_zip=positive,positive_nonempty_uploads=3,
      empty_member_preserved=True,actual_recovery_manifest_files=len(manifest),
      synthetic_outer_archive_only=True,remote_upload_in_controls=False,**FLAGS)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
    parser=argparse.ArgumentParser();parser.add_argument('--controls',action='store_true');parser.add_argument('--republish',action='store_true');args=parser.parse_args()
    assert args.controls!=args.republish
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],**FLAGS)
    try:
        r['method']=pins();result,manifest,actual=evidence()
        r['release_controls']=release.controls();assert len(r['release_controls']['rejected'])==17
        r['original_recovery_status']=result['status']
        r['publication_controls']=controls(result,manifest,actual)
        r['original_transport_controls']=original.controls(original.source_evidence())
        assert len(r['original_transport_controls']['rejected'])==29
        if args.controls:
            r['status']='PASS_PUBLICATION_REPAIR_CONTROLS_NO_ARCHIVE_READ';return
        tag,head=release.context(GROUP,os.environ)
        verify=lambda:release.validate_release(release.api('releases/tags/'+tag),release.api('git/ref/tags/'+tag),tag,head)
        r['source_release']=verify()
        assert shutil.disk_usage(OUT).free>=4*1024**3
        with tempfile.TemporaryDirectory(prefix='fallback-publication-only-')as td:
            archive=Path(td)/'fallback.zip';r['fallback_transport']=download(archive)
            restored=OUT/'restored';r['outer_restore']=extract(archive,restored,manifest)
            r['original_archive_proof']=dict(**ARCHIVE_PROOF,original65_proof_reused_from_authenticated_recovery=True,
              original_inner_zip_byte_identical=True,inner_process_image_not_decoded_or_rescanned=True)
        p=plan(restored,manifest);validate_plan(p,manifest);r['publication_plan']=p
        r['assets']=send_nonempty(restored,p,manifest,tag,verify)
        pins();identity(*actual);r['source_release']=verify()
        r['status']='PASS_REPUBLISHED_EXACT65_MEMBER_ARCHIVE_AND_EMPTY_INVENTORY_ROUTING_STILL_REJECTED'
    except BaseException as exc:
        r.update(status='FAIL_PUBLICATION_REPAIR',error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        path=OUT/'publication-repair.json';write(path,r)
        b=path.read_bytes()
        print('PUBLICATION_REPAIR_BYTES',len(b),'SHA256',sha(b),flush=True)
        encoded=__import__('base64').b64encode(b).decode()
        for i in range(0,len(encoded),4096):print('PUBLICATION_REPAIR_BASE64',i//4096,encoded[i:i+4096],flush=True)
    verify();print(json.dumps(publish(OUT/'publication-repair.json',tag)),flush=True)
if __name__=='__main__':main()
