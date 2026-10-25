#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real archive/publication-wrapper fixtures; remote upload is simulated."""
import copy,io,json,os,tarfile,tempfile,types
from pathlib import Path
from unittest.mock import patch
import mainchip_saved_postroute_admission as admission
import mainchip_saved_postroute_publisher_base as base
import publish_mainchip_saved_postroute as wrapper

def controls():
    admission.methods()
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Melihakbulut221/nssoc',
        GITHUB_RUN_ID='17',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    positives=[];rejected=[]
    original_pack=wrapper.pack
    with tempfile.TemporaryDirectory(prefix='saved-postroute-publisher-controls-')as tmp,patch.dict(os.environ,env):
        top=Path(tmp)
        def setup(name,status='FAIL_OR_ERROR',report=True):
            folder=top/name;folder.mkdir();root=folder/'cloud-mainchip-route12-postroute';root.mkdir()
            out=folder/('publication-'+wrapper.GROUP)
            (root/'native.log').write_bytes(bytes(range(256))*32)
            (root/'empty.drc').write_bytes(b'')
            (root/'.native-hidden').write_bytes(b'exact hidden evidence')
            if report:
                (root/'result.json').write_text(json.dumps(dict(status=status,source_head='a'*40,
                    accepted=False,final_timing_complete=False,full_phy_accepted=False,error='preserved failure')))
            return root,out
        def snapshot(root):
            return {str(p.relative_to(root)):admission.sha(p)for p in root.rglob('*')if p.is_file()and not p.is_symlink()}
        def exercise(root,out,change=None,expect_failure=False):
            tag='cloud-results-17-1-'+wrapper.GROUP;uploads=[]
            release=dict(id=7,tag_name=tag,target_commitish='a'*40,draft=False,prerelease=True,assets=[])
            ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha='a'*40))
            def api(path):
                if path=='releases/tags/'+tag:return copy.deepcopy(release)
                if path=='git/ref/tags/'+tag:return copy.deepcopy(ref)
                raise AssertionError('Unexpected remote operation '+path)
            def upload(argv,**kwargs):
                assert argv[:4]==['gh','release','upload',tag]and '--clobber'not in argv
                p=Path(argv[4]);assert p.parent==out and p.is_file()and not p.is_symlink()
                release['assets'].append(dict(id=100+len(uploads),name=p.name,size=p.stat().st_size,
                    digest='sha256:'+admission.sha(p),browser_download_url='https://example.invalid/'+p.name))
                uploads.append(p.name);return types.SimpleNamespace(returncode=0)
            def packed(root,stem,out):
                manifest=original_pack(root,stem,out,127)
                if change is not None:change(root,out,stem,manifest)
                return manifest
            prior_release=base.migration.release
            with patch.object(wrapper.guard,'api',api),patch.object(base.migration.subprocess,'run',upload),patch.object(wrapper,'pack',packed):
                if expect_failure:
                    try:wrapper.publish_evidence(root,out)
                    except(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError,NotADirectoryError):pass
                    else:raise AssertionError('Actual publication wrapper accepted invalid evidence')
                    assert not uploads
                    result=None
                else:result=wrapper.publish_evidence(root,out)
            assert base.migration.release is prior_release
            return result,uploads
        for label,status in [('failed','FAIL_OR_ERROR'),('interrupted','RUNNING_NATIVE_COMPLETED_ROUTE_ANTENNA_RC_STA'),('missing','FAIL_MISSING_NATIVE_REPORT')]:
            root,out=setup(label,status,report=label!='missing')
            proof,uploads=exercise(root,out)
            saved=json.loads((root/'result.json').read_bytes())
            expected='INTERRUPTED_NATIVE_POSTROUTE_NOT_ACCEPTED'if label=='interrupted'else status
            assert saved['status']==expected and saved['accepted']is False
            assert saved['run_id']==17 and saved['run_attempt']==1
            assert saved['final_timing_complete']is False and saved['full_phy_accepted']is False
            if label!='missing':assert saved['error']=='preserved failure'
            stem=wrapper.GROUP+'-17-1';manifest=json.loads((out/(stem+'.parts.json')).read_bytes())
            assert len(manifest['parts'])>1
            paths=[out/(stem+'.summary.json'),out/(stem+'.parts.json'),*[out/p['name']for p in manifest['parts']]]
            assert uploads==[p.name for p in paths]and proof['files']==[dict(name=p.name,bytes=p.stat().st_size,sha256=admission.sha(p))for p in paths]
            joined=b''.join((out/p['name']).read_bytes()for p in manifest['parts'])
            with tarfile.open(fileobj=io.BytesIO(joined),mode='r:gz')as archive:
                members={str(Path(x.name).relative_to(root.name)):x for x in archive.getmembers()if x.isfile()}
                assert set(members)==set(snapshot(root))
                for name,member in members.items():assert archive.extractfile(member).read()==(root/name).read_bytes()
            assert (out/(stem+'.summary.json')).read_bytes()==(root/'result.json').read_bytes()
            positives.append(label)
        # These refusal cases must not modify any original evidence or create publication output.
        for label in ('attempt2','root-symlink','report-symlink','descendant-symlink','root-file'):
            root,out=setup(label);tracked=root;before=snapshot(root)
            if label=='root-symlink':
                alias=root.parent/'alias';alias.symlink_to(root,target_is_directory=True);root=alias
            elif label=='report-symlink':
                saved=root.parent/'saved-result.json';(root/'result.json').rename(saved);(root/'result.json').symlink_to(saved)
            elif label=='descendant-symlink':(root/'linked.log').symlink_to(root/'native.log')
            elif label=='root-file':root=root/'native.log'
            before=snapshot(tracked)
            saved_report=(tracked/'result.json').read_bytes()
            with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'2'if label=='attempt2'else'1'}):
                exercise(root,out,expect_failure=True)
            assert snapshot(tracked)==before and (tracked/'result.json').read_bytes()==saved_report and not out.exists()
            rejected.append(label)
        # Mutate the actual packed output and pass it through the shared real file-list seam.
        faults=[
            ('missing-part',lambda r,o,s,m:(o/m['parts'][0]['name']).unlink()),
            ('duplicate-part',lambda r,o,s,m:m['parts'].append(copy.deepcopy(m['parts'][0]))),
            ('changed-part-bytes',lambda r,o,s,m:(o/m['parts'][0]['name']).write_bytes(b'changed')),
            ('changed-part-digest',lambda r,o,s,m:m['parts'][0].update(sha256='0'*64)),
            ('wrong-source-directory',lambda r,o,s,m:m.update(source_directory='wrong')),
            ('changed-summary',lambda r,o,s,m:(o/(s+'.summary.json')).write_bytes(b'{}')),
            ('changed-manifest-file',lambda r,o,s,m:(o/(s+'.parts.json')).write_bytes(b'{}')),
            ('symlink-summary',lambda r,o,s,m:((o/(s+'.summary.json')).unlink(),(o/(s+'.summary.json')).symlink_to(r/'result.json'))),
        ]
        for label,change in faults:
            root,out=setup(label);exercise(root,out,change,True);rejected.append(label)
    assert len(positives)==3 and len(rejected)==13 and len(set(rejected))==13
    return dict(status='PASS_ACTUAL_SAVED_POSTROUTE_PUBLICATION_WRAPPER_CONTROLS_NOT_NATIVE',
        positives=positives,rejected=rejected,actual_pack_and_complete_members_verified=True,
        qualified_publisher_used_with_fake_remote_transport=True,network_or_native_executed=False)

if __name__=='__main__':print(json.dumps(controls(),indent=2))
