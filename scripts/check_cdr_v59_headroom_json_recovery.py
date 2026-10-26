#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic recovery/file/publication fixtures; no original archive."""
import ast,copy,hashlib,io,json,os,sys,tarfile,tempfile
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_v59_headroom_json_recovery as c
from cloud_chunked_results import pack
def same_functions():
    pairs=[('scripts/cdr_v59_headroom_readback_admission.py',('relative','extract')),
           ('scripts/cloud_cdr_v59_binding_rc.py',('only_reserved',))]
    target={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(Path(c.__file__).read_text()).body if isinstance(n,ast.FunctionDef)}
    for path,names in pairs:
        old={n.name:ast.dump(n,include_attributes=False)for n in ast.parse((c.ROOT/path).read_text()).body if isinstance(n,ast.FunctionDef)}
        for name in names:assert target[name]==old[name],name
    return dict(frozen_functions=['relative','extract','only_reserved'],exact_AST=True)
def import_closure(m):
    queue=['scripts/cloud_cdr_v59_headroom_json_recovery.py','scripts/check_cdr_v59_headroom_json_recovery.py'];seen={}
    while queue:
        name=queue.pop()
        if name in seen:continue
        p=c.ROOT/name;assert name in m['protected']and c.sha(p)==m['protected'][name]
        seen[name]=c.sha(p)
        for n in ast.walk(ast.parse(p.read_text())):
            modules=[a.name for a in n.names]if isinstance(n,ast.Import)else [n.module]if isinstance(n,ast.ImportFrom)and n.level==0 else []
            for module in modules:
                top=module.split('.')[0];candidate='scripts/'+top+'.py';path=c.ROOT/candidate
                if path.exists():
                    assert candidate in m['protected']and not path.is_symlink()
                    queue.append(candidate)
                else:assert top in sys.stdlib_module_names,(name,module)
    return seen
def controls():
    m=c.methods();c.guard(m,'controls');positive=[];bad=[]
    def reject(name,fn,types=(AssertionError,KeyError,ValueError,FileNotFoundError,RuntimeError)):
        try:fn()
        except types:bad.append(name)
        else:raise AssertionError('Accepted '+name)
    same=same_functions();positive.append('exact_three_frozen_functions')
    closure=import_closure(m);positive.append('complete_stdlib_repository_import_closure')
    summary,manifest,receipt=c.reference(m)
    def identity(r):c.identity(r['run'],r['jobs'],r['release'],r['tag'],receipt)
    identity(receipt);positive.append('actual_pinned_terminal_metadata')
    for label,change in [
        ('wrong_source',lambda r:r['run'].__setitem__('head_sha','0'*40)),
        ('wrong_attempt',lambda r:r['run'].__setitem__('run_attempt',2)),
        ('nonterminal',lambda r:r['run'].__setitem__('status','in_progress')),
        ('failed_readback',lambda r:r['jobs']['jobs'][1].__setitem__('conclusion','failure')),
        ('missing_job',lambda r:r['jobs']['jobs'].pop()),
        ('wrong_release',lambda r:r['release'].__setitem__('id',1)),
        ('wrong_tag',lambda r:r['tag']['object'].__setitem__('sha','0'*40)),
        ('not_prerelease',lambda r:r['release'].__setitem__('prerelease',False)),
        ('changed_archive_digest',lambda r:r['release']['assets'][-1].__setitem__('digest','sha256:'+'0'*64)),
        ('missing_asset',lambda r:r['release']['assets'].pop())]:
        r=copy.deepcopy(receipt);change(r);reject(label,lambda r=r:identity(r))
    with tempfile.TemporaryDirectory(prefix='cdr-json-recovery-fixture-')as tmp:
        root=Path(tmp);payload={n:(json.dumps({'fixture':n})+'\n').encode()for n in c.SELECT}
        payload.update({'result.json':b'{"fixture":"result"}\n'})
        payload.update({name:bytes(range(256))*2 for name in summary['outputs']if name not in c.SELECT})
        assert len(payload)==15
        source=root/'cloud-cdr-v59-cn-headroom-readback';source.mkdir()
        for n,b in payload.items():
            p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        outer={'outputs':{n:hashlib.sha256(b).hexdigest()for n,b in payload.items()if n!='result.json'}}
        rh=hashlib.sha256(payload['result.json']).hexdigest()
        packed=pack(source,'fixture',root,127);assert len(packed['parts'])>1
        saved=root/'selected';proof=c.extract(packed,root,saved,outer,rh)
        assert proof['all_member_hashes_verified']==15
        assert set(str(p.relative_to(saved))for p in saved.rglob('*')if p.is_file())==set(c.SELECT)|{'result.json'}
        assert all((saved/n).read_bytes()==payload[n]for n in proof['selected'])
        positive.append('actual_multipart_all15_verified_only11_JSONs_saved')
        # Rebuild a valid complete archive digest for each inner-member fault.
        def archive_trial(label,entries):
            p=root/(label+'.tar.gz.part0000')
            with tarfile.open(p,'w:gz')as tar:
                for n,b,kind in entries:
                    item=tarfile.TarInfo(n);item.type=kind;item.size=len(b)if kind==tarfile.REGTYPE else 0
                    if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE):item.linkname='outside'
                    tar.addfile(item,io.BytesIO(b)if item.size else None)
            size=p.stat().st_size;h=c.sha(p)
            mat=dict(format='ordered-tar-gzip-parts-v1',stem=label,source_directory=source.name,bytes=size,sha256=h,parts=[dict(index=0,name=p.name,bytes=size,sha256=h)])
            return c.extract(mat,root,root/(label+'-selected'),outer,rh)
        entries=[(source.name+'/'+n,b,tarfile.REGTYPE)for n,b in payload.items()]
        selected_index=next(i for i,x in enumerate(entries)if x[0].endswith('/diagnosis.json'))
        unselected_index=next(i for i,x in enumerate(entries)if x[0].endswith('.bin'))
        for label,change in [
            ('missing_selected',lambda e:e.pop(selected_index)),
            ('missing_unselected',lambda e:e.pop(unselected_index)),
            ('changed_selected',lambda e:e.__setitem__(selected_index,(e[selected_index][0],b'changed',tarfile.REGTYPE))),
            ('changed_unselected',lambda e:e.__setitem__(unselected_index,(e[unselected_index][0],b'changed',tarfile.REGTYPE))),
            ('duplicate_member',lambda e:e.append(e[0])),
            ('unexpected_member',lambda e:e.append((source.name+'/extra',b'',tarfile.REGTYPE))),
            ('symlink',lambda e:e.append((source.name+'/link',b'',tarfile.SYMTYPE))),
            ('hardlink',lambda e:e.append((source.name+'/link',b'',tarfile.LNKTYPE))),
            ('traversal',lambda e:e.append((source.name+'/../bad',b'',tarfile.REGTYPE))),
            ('wrong_root',lambda e:e.append(('other/bad',b'',tarfile.REGTYPE))),
            ('backslash',lambda e:e.append((source.name+'/a'+chr(92)+'b',b'',tarfile.REGTYPE)))]:
            e=list(entries);change(e);reject(label,lambda label=label,e=e:archive_trial(label,e))
        for label,change in [('part_order',lambda x:x['parts'].reverse()),('whole_digest',lambda x:x.__setitem__('sha256','0'*64))]:
            x=copy.deepcopy(packed);change(x);reject(label,lambda x=x,label=label:c.extract(x,root,root/label,outer,rh))
        # Exercise actual publishing function plus unchanged qualified upload/digest logic.
        env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=c.release.REPO,GITHUB_SHA='a'*40,GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1')
        out=root/'export';out.mkdir();(out/'json').mkdir()
        expected={c.output_name(n):hashlib.sha256(payload[n]).hexdigest()for n in proof['selected']}
        for n in proof['selected']:(out/'json'/c.output_name(n)).write_bytes(payload[n])
        result=dict(status=c.PASS,source_head=env['GITHUB_SHA'],run_id=123,run_attempt=1,original_run=c.ORIGINAL,original_source=c.HEAD,
            member_proof=proof,outputs=expected,**{k:False for k in c.FALSE})
        c.write(out/'result.json',result)
        fixture_m=dict(m,source_controls_authorized=True,recovery_authorized=True)
        tag,head=c.release.context(c.GROUP,env)
        info=dict(id=1,tag_name=tag,target_commitish=head,prerelease=True,draft=False,assets=[])
        ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=head))
        uploads=[]
        def read(path,missing=False):return copy.deepcopy(info if path.startswith('releases/')else ref)
        def upload(argv,**kwargs):
            assert argv[:3]==['gh','release','upload']and argv[3]==tag
            p=Path(argv[4]);assert p.name not in [a['name']for a in info['assets']]
            info['assets'].append(dict(id=len(info['assets'])+1,name=p.name,size=p.stat().st_size,digest='sha256:'+c.sha(p),browser_download_url='fixture/'+p.name))
            uploads.append(p.name)
            return type('Result',(),{'returncode':0})()
        with patch.object(c,'OUT',out),patch.dict(os.environ,env),patch.object(c,'expected_exports',return_value=expected),patch.object(c.waiter,'wait',return_value={}),patch.object(c.release,'api',side_effect=read),patch.object(c.publisher.subprocess,'run',side_effect=upload):
            result_pub=c.publish(fixture_m);assert len(result_pub['assets'])==12 and len(uploads)==12
            again=c.publish(fixture_m);assert len(again['assets'])==12 and len(uploads)==12
            positive.append('actual_complete_file_list_publisher_fake_remote_no_clobber')
            for label,change in [('wrong_output_hash',lambda r:r['outputs'].__setitem__(next(iter(expected)),'0'*64)),
                ('acceptance_claim',lambda r:r.__setitem__('accepted',True)),('missing_member_proof',lambda r:r['member_proof'].__setitem__('all_member_hashes_verified',14)),
                ('wrong_recovery_source',lambda r:r.__setitem__('source_head','b'*40))]:
                r=copy.deepcopy(result);change(r);c.write(out/'result.json',r);reject(label,lambda:c.publication_files(fixture_m))
            c.write(out/'result.json',result)
            victim=out/'json'/next(iter(expected));old= victim.read_bytes();victim.unlink();victim.symlink_to(out/'result.json')
            reject('selected_symlink',lambda:c.publication_files(fixture_m));victim.unlink();victim.write_bytes(old)
            olddigest=info['assets'][0]['digest'];info['assets'][0]['digest']='sha256:'+'0'*64
            reject('remote_existing_digest_no_overwrite',lambda:c.publish(fixture_m));info['assets'][0]['digest']=olddigest
            for status in ('RUNNING','FAIL_EXACT_JSON_RECOVERY'):
                r=copy.deepcopy(result);r['status']=status;c.write(out/'result.json',r)
                assert c.publication_files(fixture_m)==[out/'result.json']
            positive.append('failed_interrupted_result_only_never_partial_JSONs')
        reject('local_recovery_guard',lambda:c.guard(fixture_m,'recovery',dict(env,GITHUB_ACTIONS='false')))
        reject('attempt2_guard',lambda:c.guard(fixture_m,'recovery',dict(env,GITHUB_RUN_ATTEMPT='2')))
        reject('unauthorized_recovery',lambda:c.guard(dict(fixture_m,recovery_authorized=False),'recovery',env))
    assert len(positive)==6 and len(bad)==32,(positive,bad)
    return dict(status='PASS_SYNTHETIC_EXISTING_JSON_RECOVERY_CONTROLS',positive=positive,rejected=bad,
        frozen_functions=same,import_closure=closure,original_archive_downloaded=False,new_analysis=False,simulation=False,native=False)
if __name__=='__main__':
    print(json.dumps(controls(),indent=2))
