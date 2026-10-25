#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual pack/file-list/publisher fixtures; fake remote only, no saved capture."""
import copy,io,json,os,tarfile,tempfile,types
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_v59_headroom_readback as w
def controls():
    m=w.a.methods();assert m['source_controls_authorized']is True
    positives=[];rejected=[]
    def refuse(label,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError,NotADirectoryError):rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    env=dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',GITHUB_REPOSITORY='Melihakbulut221/nssoc',
        GITHUB_RUN_ID='17',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    with patch.dict(os.environ,env),tempfile.TemporaryDirectory(prefix='cdr-headroom-publish-')as folder:
        top=Path(folder);original_pack=w.pack
        def setup(label,status='FAIL_EXISTING_CAPTURE_ANALYSIS'):
            repo=top/label;repo.mkdir();root=repo/('cloud-'+w.GROUP);root.mkdir()
            (root/'frames.jsonl').write_bytes(bytes(range(256))*8);(root/'.hidden').write_bytes(b'hidden')
            (root/'empty').write_bytes(b'');(root/'nested').mkdir();(root/'nested/cache.bin').write_bytes(b'partial cache')
            r=dict(status=status,source_head='a'*40,run_id=17,run_attempt=1,source_run=w.a.RUN,
                cases=[],new_simulation=False,new_extraction=False,geometry_changed=False,
                accepted=False,cdr_accepted=False,qualified_pex=False,full_phy_accepted=False)
            if status.startswith('PASS_'):
                r['cases']=[dict(case=c,original_rejection=True,accepted=False,causality_proven=False)for c in ('nominal_early','nominal_late')]
            if label=='oversize':r['synthetic_padding']='x'*(4*1024**2)
            r['outputs']={str(p.relative_to(root)):w.a.sha(p)for p in root.rglob('*')if p.is_file()}
            w.write(root/'result.json',r)
            return repo,root,repo/'hw/soc/out'/(w.GROUP+'-publication')
        def exercise(repo,root,out,change=None,fail=False):
            tag='cloud-results-17-1-'+w.GROUP;uploads=[]
            info=dict(id=7,tag_name=tag,target_commitish='a'*40,draft=False,prerelease=True,assets=[])
            ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha='a'*40))
            def api(path,missing=False):
                if path=='releases/tags/'+tag:return copy.deepcopy(info)
                if path=='git/ref/tags/'+tag:return copy.deepcopy(ref)
                raise AssertionError('Unexpected remote operation '+path)
            def upload(argv,**kw):
                assert argv[:4]==['gh','release','upload',tag]and '--clobber'not in argv
                p=Path(argv[4]);assert p.parent==out and p.is_file()and not p.is_symlink()
                info['assets'].append(dict(id=100+len(uploads),name=p.name,size=p.stat().st_size,
                    digest='sha256:'+w.a.sha(p),browser_download_url='https://example.invalid/'+p.name))
                uploads.append(p.name);return types.SimpleNamespace(returncode=0)
            def packed(root,stem,out,size):
                manifest=original_pack(root,stem,out,127)
                if change:change(root,out,stem,manifest)
                return manifest
            previous=w.publisher.release
            with redirect_stdout(io.StringIO()),patch.object(w.a,'ROOT',repo),patch.object(w.waiter,'wait',lambda *args:dict(fixture=True)),patch.object(w.release,'api',api),patch.object(w.publisher.subprocess,'run',upload),patch.object(w,'pack',packed),patch.object(w.shutil,'disk_usage',lambda p:types.SimpleNamespace(free=16*1024**3)):
                if fail:
                    refuse(repo.name,lambda:w.publish(root,dict(readback_authorized=True,source_controls_authorized=True)))
                    result=None;assert not uploads
                else:result=w.publish(root,dict(readback_authorized=True,source_controls_authorized=True))
            assert w.publisher.release is previous
            return result,uploads
        for label,status in [('failed','FAIL_EXISTING_CAPTURE_ANALYSIS'),('interrupted','RUNNING'),
            ('oversize','FAIL_EXISTING_CAPTURE_ANALYSIS'),('completed','PASS_EXISTING_CAPTURE_HEADROOM_ANALYSIS_NOT_ACCEPTANCE')]:
            repo,root,out=setup(label,status);before={str(p.relative_to(root)):w.a.sha(p)for p in root.rglob('*')if p.is_file()}
            proof,uploads=exercise(repo,root,out)
            assert all(w.a.sha(root/n)==h for n,h in before.items())
            stem=w.GROUP+'-17-1';manifest=json.loads((out/(stem+'.parts.json')).read_bytes())
            assert len(manifest['parts'])>1
            assert uploads==[stem+'.summary.json',stem+'.parts.json',*[p['name']for p in manifest['parts']]]
            combined=b''.join((out/p['name']).read_bytes()for p in manifest['parts'])
            found={}
            with tarfile.open(fileobj=io.BytesIO(combined),mode='r:gz')as archive:
                for entry in archive:
                    if entry.isdir():continue
                    assert entry.isfile()
                    rel=Path(entry.name).relative_to(root.name).as_posix();assert rel not in found
                    payload=archive.extractfile(entry).read();assert payload==(root/rel).read_bytes()
                    found[rel]=w.a.sha(root/rel)
            assert found==before and (out/(stem+'.summary.json')).read_bytes()==(root/'result.json').read_bytes()
            assert json.loads((root/'result.json').read_bytes())['status']==status
            assert proof['status']=='PASS_EXISTING_CAPTURE_EVIDENCE_PUBLISHED_NOT_ELECTRICAL_ACCEPTANCE'
            positives.append('actual_complete_pack_and_qualified_publisher_'+label)
        for label in ('attempt2','root_link','report_link','descendant_link','root_file','missing_report','changed_original'):
            repo,root,out=setup(label)
            if label=='root_link':
                real=repo/'real';root.rename(real);root.symlink_to(real,target_is_directory=True)
            elif label=='report_link':
                real=repo/'saved-result.json';(root/'result.json').rename(real);(root/'result.json').symlink_to(real)
            elif label=='descendant_link':(root/'link').symlink_to(root/'frames.jsonl')
            elif label=='root_file':
                real=repo/'real';root.rename(real);root.write_bytes(b'not directory')
            elif label=='missing_report':(root/'result.json').unlink()
            elif label=='changed_original':(root/'frames.jsonl').write_bytes(b'changed')
            with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'2'if label=='attempt2'else'1'}):exercise(repo,root,out,fail=True)
            assert not out.exists()
        mutations=[
            ('wrong_source',lambda r:r.update(source_head='b'*40)),
            ('wrong_run',lambda r:r.update(run_id=18)),
            ('wrong_attempt',lambda r:r.update(run_attempt=2)),
            ('wrong_original_run',lambda r:r.update(source_run=0)),
            ('wrong_status',lambda r:r.update(status='PASS_NATIVE')),
            ('wrong_case_order',lambda r:r.update(cases=[dict(case='nominal_late')])),
            ('false_complete',lambda r:r.update(status='PASS_EXISTING_CAPTURE_HEADROOM_ANALYSIS_NOT_ACCEPTANCE')),
            ('simulation_claim',lambda r:r.update(new_simulation=True)),
            ('accepted_claim',lambda r:r.update(accepted=True)),
            ('missing_inventory',lambda r:r['outputs'].pop('empty')),
            ('invented_inventory',lambda r:r['outputs'].update(extra='0'*64))]
        for label,change in mutations:
            repo,root,out=setup(label);p=root/'result.json';r=json.loads(p.read_bytes());change(r);w.write(p,r)
            exercise(repo,root,out,fail=True);assert not out.exists()
        faults=[
            ('missing_part',lambda r,o,s,m:(o/m['parts'][0]['name']).unlink()),
            ('duplicate_part',lambda r,o,s,m:m['parts'].append(copy.deepcopy(m['parts'][0]))),
            ('changed_part',lambda r,o,s,m:(o/m['parts'][0]['name']).write_bytes(b'changed')),
            ('changed_digest',lambda r,o,s,m:m['parts'][0].update(sha256='0'*64)),
            ('wrong_directory',lambda r,o,s,m:m.update(source_directory='wrong')),
            ('changed_summary',lambda r,o,s,m:(o/(s+'.summary.json')).write_bytes(b'{}')),
            ('changed_manifest',lambda r,o,s,m:(o/(s+'.parts.json')).write_bytes(b'{}'))]
        for label,change in faults:
            repo,root,out=setup(label);exercise(repo,root,out,change,True)
    assert len(positives)==4 and len(rejected)==25 and len(set(rejected))==25
    return dict(status='PASS_HEADROOM_REAL_PUBLICATION_FIXTURES_NOT_CAPTURE_ANALYSIS',
        positives=positives,rejected=rejected,actual_complete_pack_roundtrips=4,
        actual_publisher_with_fake_remote=True,actual_capture_accessed=False,simulator_executed=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
