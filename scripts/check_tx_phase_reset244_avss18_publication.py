#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls execute the actual template publication assembly with fake transport."""
import ast,contextlib,copy,hashlib,io,json,os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import cloud_tx_phase_reset244_avss18_physical as c
import ensure_cloud_tested_source_release as guard
import migrate_outputs_to_cloud as migration
import publish_cloud_results as publisher
TEMPLATE='.github/workflow-templates/tx-phase-reset244-avss18-physical-cloud.yml'
HEADER='          python3 - "$stem" "$group" "$root" <<\'PYCODE\'\n'

def program():
    c.methods()
    text=(c.ROOT/TEMPLATE).read_text()
    assert text.count(HEADER)==1
    body=text.split(HEADER,1)[1].split('          PYCODE\n',1)[0]
    assert all(line.startswith('          ') for line in body.splitlines())
    source='\n'.join(line[10:] for line in body.splitlines())+'\n'
    ast.parse(source)
    return source

def controls():
    code=program()
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=guard.REPO,GITHUB_RUN_ID='123',
             GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    group='tx-phase-reset244-avss18-physical';stem=group+'-123-1'
    tag,sha=guard.context(group,env)
    info=dict(id=5,tag_name=tag,target_commitish=sha,draft=False,prerelease=True,assets=[])
    reference=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=sha))
    rejected=[];positives=[]
    with tempfile.TemporaryDirectory()as td:
        base=Path(td);root=base/('cloud-'+group);root.mkdir()
        (root/'result.json').write_text('{"status":"original rejection remains"}\n')
        (base/(stem+'.summary.json')).write_bytes((root/'result.json').read_bytes())
        for name in ('physical-p-native-material.json','physical-n-native-material.json',
                     'baseline-restoration.json','source-controls-prerequisite.json'):
            (root/name).write_text(json.dumps(dict(kind=name))+'\n')
        part_names=[stem+'.tar.gz.part0000',stem+'.tar.gz.part0001']
        for i,name in enumerate(part_names):(base/name).write_bytes(b'opaque archive part '+bytes([i]))
        manifest=dict(parts=[dict(name=n) for n in part_names])
        parts=base/(stem+'.parts.json');parts.write_text(json.dumps(manifest)+'\n')
        expected=[stem+'.summary.json',stem+'.parts.json',
                  *sorted(p.name for p in root.glob('*.json') if p.name!='result.json'),*part_names]
        assert len(expected)==8
        def exercise(candidate,remote=None,tag_ref=None,missing=False,bad_upload_digest=False):
            remote=copy.deepcopy(info if remote is None else remote)
            tag_ref=copy.deepcopy(reference if tag_ref is None else tag_ref)
            calls=[];uploads=[];forbidden=[]
            def read(path,missing=False):
                calls.append(path)
                if path.startswith('releases/'):
                    if missing:raise AssertionError('HTTP404 existing release missing')
                    return copy.deepcopy(remote)
                assert path=='git/ref/tags/'+tag
                return copy.deepcopy(tag_ref)
            # Avoid shadowing the missing-state fixture with the API's compatibility keyword.
            def read_api(path,missing_arg=False,**kwargs):
                if missing and path.startswith('releases/'):
                    calls.append(path);raise AssertionError('HTTP404 existing release missing')
                return read(path)
            def subprocess_run(argv,*args,**kwargs):
                if argv[:3]!=['gh','release','upload']:
                    forbidden.append(argv);raise AssertionError('Unexpected subprocess/create path')
                assert argv[3]==tag and argv[-2:]==['-R',migration.REPO]
                path=Path(argv[4]);assert path.is_file() and not path.is_symlink()
                assert path.name not in {a['name']for a in remote['assets']}
                # An upload follows a fresh exact release and tag lookup, not an unchecked fallback.
                assert calls[-2:]==['releases/tags/'+tag,'git/ref/tags/'+tag]
                with path.open('rb')as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                remote['assets'].append(dict(id=100+len(uploads),name=path.name,size=path.stat().st_size,
                    digest='sha256:'+('0'*64 if bad_upload_digest else digest),browser_download_url='https://example.invalid/'+path.name))
                uploads.append(path.name)
                return SimpleNamespace(returncode=0)
            oldrelease=migration.release;oldpath=list(sys.path);cwd=Path.cwd()
            try:
                os.chdir(base)
                with mock.patch.dict(os.environ,env),mock.patch.object(sys,'argv',['publication',stem,group,str(root)]),\
                     mock.patch.object(guard,'api',read_api),mock.patch.object(migration.subprocess,'run',subprocess_run),\
                     mock.patch.object(migration.time,'sleep',side_effect=AssertionError('No retry expected in fixture')),\
                     contextlib.redirect_stdout(io.StringIO())as output:
                    exec(compile(candidate,'actual-template-publication-program','exec'),{})
                result=json.loads(output.getvalue())
                assert result['tag']==tag and [a['name']for a in result['assets']]==expected
                assert not forbidden and all(a['digest'].startswith('sha256:')for a in remote['assets'])
                assert calls[-2:]==['releases/tags/'+tag,'git/ref/tags/'+tag]
                return dict(result=result,remote=remote,uploads=uploads,reads=len(calls))
            finally:
                migration.release=oldrelease;sys.path[:]=oldpath;os.chdir(cwd)
        first=exercise(code)
        assert first['uploads']==expected
        assert first['reads']==4+4*len(expected)
        positives.append('actual_program_all8_paths_two_archive_parts_real_publisher_digest_roundtrip')
        second=exercise(code,first['remote'])
        assert second['uploads']==[] and second['reads']==4+2*len(expected)
        positives.append('identical_existing_assets_preserved_without_upload')
        def reject(label,fn):
            try:fn()
            except (AssertionError,KeyError,ValueError,TypeError,RuntimeError,FileNotFoundError):rejected.append(label)
            else:raise AssertionError('Accepted publication fault '+label)
        reject('unbound_legacy_create_seam',lambda:exercise(code.replace('migration.release=readonly_release','pass')))
        wrong=copy.deepcopy(info);wrong['target_commitish']='b'*40
        reject('wrong_release_source',lambda:exercise(code,wrong))
        wrongref=copy.deepcopy(reference);wrongref['object']['sha']='b'*40
        reject('wrong_tag_source',lambda:exercise(code,tag_ref=wrongref))
        wrongtag=copy.deepcopy(info);wrongtag['tag_name']='other'
        reject('wrong_release_tag',lambda:exercise(code,wrongtag))
        reject('missing_reserved_release',lambda:exercise(code,missing=True))
        reject('Path_indexed_as_manifest',lambda:exercise(code.replace(
            "part_names=[p['name'] for p in manifest['parts']]","part_names=[part_file['name']]")))
        reject('post_upload_digest_mismatch',lambda:exercise(code,bad_upload_digest=True))
        conflict=copy.deepcopy(first['remote']);conflict['assets'][0]['digest']='sha256:'+'0'*64
        reject('existing_asset_never_overwritten',lambda:exercise(code,conflict))
        original_parts=parts.read_bytes()
        for label,badnames in [('duplicate_part',[part_names[0],part_names[0]]),
            ('traversal_part',['../outside']),('backslash_part',['folder\\outside'])]:
            parts.write_text(json.dumps(dict(parts=[dict(name=n)for n in badnames]))+'\n')
            reject(label,lambda:exercise(code))
        parts.write_bytes(original_parts)
        collision=root/(stem+'.summary.json');collision.write_bytes(b'collision')
        reject('duplicate_asset_basename',lambda:exercise(code));collision.unlink()
        chosen=root/'baseline-restoration.json';saved=chosen.read_bytes();chosen.unlink()
        chosen.symlink_to(root/'physical-p-native-material.json')
        reject('symlink_json',lambda:exercise(code));chosen.unlink();chosen.write_bytes(saved)
        # Prove actual fixed program assembly includes every selected JSON and excludes result.json.
        assert all('result.json'!=a['name']for a in first['result']['assets'])
    assert len(rejected)==13
    return dict(status='PASS_AVSS18_ACTUAL_PUBLICATION_PROGRAM_CONTROLS_ONLY',
        positive_cases=positives,rejected=rejected,actual_template_program_executed=True,
        real_file_list_assembly=True,real_publisher_retry_and_digest_function_used=True,
        remote_network_or_upload_executed=False,release_creation_executed=False,native_executed=False)

if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    print(json.dumps(controls(),indent=2),flush=True)
