#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish unchanged complete evidence only to the pre-reserved exact source."""
import argparse,base64,copy,hashlib,json,os,re,shutil,tempfile,types
from pathlib import Path
from unittest.mock import patch
import ensure_cloud_tested_source_release as guard
import migrate_outputs_to_cloud as migration
import publish_cloud_results as publisher
from cloud_chunked_results import pack,verify_parts
GROUP='mainchip-route12-saved7200-next'
SMALL=('prior-capsule-admission.json','prior-inner-controller-result.json','prior-native.log')
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def log_file(path,label):
    raw=Path(path).read_bytes();assert len(raw)<=4_000_000,'Full result retained in artifact; exceeds bounded log limit'
    print(label+'_RESULT '+json.dumps(dict(name=Path(path).name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),chunks=(len(raw)+3071)//3072)),flush=True)
    for n in range(0,len(raw),3072):print(label+'_CHUNK '+Path(path).name+' '+str(n//3072)+' '+base64.b64encode(raw[n:n+3072]).decode(),flush=True)
def checked_files(root,output,stem,manifest,summary):
    root=Path(root);output=Path(output)
    assert stem==GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    assert manifest['stem']==stem and manifest['source_directory']==root.name
    assert all((output/p['name']).is_file()and not(output/p['name']).is_symlink()for p in manifest['parts'])
    verify_parts(manifest,output)
    paths=[output/(stem+'.summary.json'),output/(stem+'.parts.json')]
    assert paths[0].read_bytes()==(root/'result.json').read_bytes()
    assert json.loads(paths[1].read_bytes())==manifest
    paths += [output/p['name']for p in manifest['parts']]
    for n in SMALL:
        path=root/n
        if n not in summary.get('outputs',{}):
            assert not path.exists(),'Unrecorded prior diagnostic'
            continue
        assert path.is_file()and not path.is_symlink()and sha(path)==summary['outputs'][n]
        dest=output/(stem+'.'+n);assert not dest.exists()
        shutil.copyfile(path,dest);assert sha(dest)==summary['outputs'][n];paths.append(dest)
    assert len({p.name for p in paths})==len(paths)
    assert all(p.is_file()and not p.is_symlink()and p.stat().st_size>0 and p.parent==output for p in paths)
    return paths
def publish_files(group,paths):
    expected,source=guard.context(group,os.environ)
    def readonly_release(tag):
        assert tag==expected
        info=guard.api('releases/tags/'+tag)
        guard.validate_release(info,guard.api('git/ref/tags/'+tag),tag,source)
        return info
    previous=migration.release
    try:
        migration.release=readonly_release
        assert publisher.publish is migration.publish
        assert publisher.publish.__globals__['release']is readonly_release
        readonly_release(expected)
        result=publisher.publish_results(group,paths)
        assert result['tag']==expected and len(result['assets'])==len(paths)
        readonly_release(expected)
        return result
    finally:migration.release=previous
def publish():
    import mainchip_saved7200_next_admission as admission
    admission.methods()
    expected,source=guard.context(GROUP,os.environ)
    info=guard.api('releases/tags/'+expected)
    guard.validate_release(info,guard.api('git/ref/tags/'+expected),expected,source)
    root=Path('cloud-'+GROUP);assert root.is_dir()and not root.is_symlink()
    output=Path('publication-'+GROUP);output.mkdir(exist_ok=False)
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    raw=(root/'result.json').read_bytes();summary=json.loads(raw)
    assert summary['source_head']==source and str(summary['run_id'])==os.environ['GITHUB_RUN_ID']
    (output/(stem+'.summary.json')).write_bytes(raw)
    manifest=pack(root,stem,output)
    paths=checked_files(root,output,stem,manifest,summary)
    result=publish_files(GROUP,paths)
    proof=dict(status='PUBLISHED_EXACT_SOURCE_COMPLETE_EVIDENCE_NOT_ROUTE_ACCEPTANCE',
        original_status=summary['status'],source=source,publication=result,
        files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p))for p in paths])
    (output/'publication.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2),flush=True)
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Melihakbulut221/nssoc',GITHUB_RUN_ID='17',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    rejected=[];uploads=[]
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,RuntimeError,FileNotFoundError):rejected.append(label)
        else:raise AssertionError('Accepted publication corruption: '+label)
    with patch.dict(os.environ,env),tempfile.TemporaryDirectory()as temp:
        root=Path(temp)/('cloud-'+GROUP);root.mkdir();out=Path(temp)/'published';out.mkdir()
        for n in SMALL:(root/n).write_bytes(('exact fixture '+n+'\n').encode())
        summary=dict(status='REJECTED_FIXTURE_NOT_ACCEPTANCE',source_head='a'*40,run_id='17',outputs={n:sha(root/n)for n in SMALL})
        raw=(json.dumps(summary)+'\n').encode();(root/'result.json').write_bytes(raw)
        stem=GROUP+'-17-1';(out/(stem+'.summary.json')).write_bytes(raw)
        manifest=pack(root,stem,out,127)
        paths=checked_files(root,out,stem,manifest,summary);assert len(paths)==5+len(manifest['parts'])
        tag='cloud-results-17-1-'+GROUP
        release=dict(id=7,tag_name=tag,target_commitish='a'*40,draft=False,prerelease=True,assets=[])
        ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha='a'*40))
        def fake_api(path):
            if path=='releases/tags/'+tag:return copy.deepcopy(release)
            if path=='git/ref/tags/'+tag:return copy.deepcopy(ref)
            raise AssertionError('Unexpected remote operation '+path)
        def fake_run(argv,**kw):
            assert argv[:3]==['gh','release','upload']and argv[3]==tag
            assert '--clobber'not in argv
            p=Path(argv[4]);assert p in paths
            release['assets'].append(dict(id=100+len(uploads),name=p.name,size=p.stat().st_size,
                digest='sha256:'+sha(p),browser_download_url='https://example.invalid/'+p.name))
            uploads.append(p.name);return types.SimpleNamespace(returncode=0)
        with patch.object(guard,'api',fake_api),patch.object(migration.subprocess,'run',fake_run):
            first=publish_files(GROUP,paths);assert len(first['assets'])==len(paths)and len(uploads)==len(paths)
            before=len(uploads);second=publish_files(GROUP,paths);assert first==second and len(uploads)==before
            for key,value in [('target_commitish','main'),('draft',True),('prerelease',False),('tag_name','wrong')]:
                old=release[key];release[key]=value
                reject('release-'+key,lambda:publish_files(GROUP,paths));release[key]=old
            old=ref['object'];ref['object']=dict(type='tag',sha='a'*40)
            reject('annotated-tag',lambda:publish_files(GROUP,paths));ref['object']=old
            old=ref['object']['sha'];ref['object']['sha']='b'*40
            reject('wrong-tag-source',lambda:publish_files(GROUP,paths));ref['object']['sha']=old
            old=release['assets'][0]['digest'];release['assets'][0]['digest']='sha256:'+'0'*64
            reject('wrong-existing-digest',lambda:publish_files(GROUP,paths));release['assets'][0]['digest']=old
            with patch.object(guard,'api',side_effect=RuntimeError('missing reserved release')):
                reject('missing-release-no-create',lambda:publish_files(GROUP,paths))
            assert len(uploads)==before
        assert migration.release is not None
        # Rebuild a fresh output directory per call because copying extra assets is exclusive.
        def listing(label,change):
            dest=Path(temp)/label;dest.mkdir()
            (dest/(stem+'.summary.json')).write_bytes(raw)
            m=pack(root,stem,dest,127);q=copy.deepcopy(summary)
            change(dest,m,q)
            return checked_files(root,dest,stem,m,q)
        reject('changed-summary',lambda:listing('bad-summary',lambda d,m,q:(d/(stem+'.summary.json')).write_bytes(b'{}')))
        reject('changed-part',lambda:listing('bad-part',lambda d,m,q:m['parts'][0].update(sha256='0'*64)))
        reject('wrong-source-directory',lambda:listing('bad-directory',lambda d,m,q:m.update(source_directory='wrong')))
        reject('changed-prior-hash',lambda:listing('bad-prior',lambda d,m,q:q['outputs'].update({'prior-native.log':'0'*64})))
        reject('unrecorded-prior',lambda:listing('bad-unrecorded',lambda d,m,q:q['outputs'].pop('prior-native.log')))
        saved=(root/'prior-native.log').read_bytes();(root/'prior-native.log').unlink()
        reject('missing-prior',lambda:listing('bad-missing',lambda d,m,q:None))
        (root/'prior-native.log').write_bytes(saved)
        saved=(out/(stem+'.summary.json')).read_bytes();(out/(stem+'.summary.json')).unlink()
        (out/(stem+'.summary.json')).symlink_to(root/'result.json')
        # Existing extra files are removed only in the disposable fixture.
        for n in SMALL:(out/(stem+'.'+n)).unlink()
        reject('symlink-summary',lambda:checked_files(root,out,stem,manifest,summary))
    assert len(rejected)==15 and len(set(rejected))==15
    return dict(status='PASS_RESERVED_MAINCHIP_PUBLICATION_CONTROLS_NOT_NATIVE',
        actual_complete_file_list_positive=True,real_publisher_fake_transport_positive=True,
        already_published_exact_assets_reused=True,rejected=rejected,
        original_rejected_status_preserved=True,network_or_native_executed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--publish',action='store_true');g.add_argument('--controls',action='store_true');g.add_argument('--log')
    a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2))
    elif a.log:log_file(a.log,'SAVED7200')
    else:publish()
