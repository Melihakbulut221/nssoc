#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only source, exact current-input and real archive/filesystem controls."""
import ast,copy,hashlib,io,json,os,tarfile,tempfile
from pathlib import Path
import cdr_v59_mim_admission as a
from cloud_chunked_results import pack
from cdr_v59_mim_composition_derivation import controls as count_controls
import tx_native_cap_order
ROOT=a.ROOT
DERIVATION='scripts/cdr-v59-mim-source-derivation.json'
def derivations(overrides=None):
    overrides=overrides or {}
    record=json.loads((ROOT/DERIVATION).read_text());proof={}
    for path,row in record['generated'].items():
        old=overrides.get(row['original'],(ROOT/row['original']).read_text())
        assert hashlib.sha256(old.encode()).hexdigest()==row['original_sha256']
        generated=old
        for edit in row['edits']:
            assert generated.count(edit['before'])==edit['count']
            generated=generated.replace(edit['before'],edit['after'])
        actual=overrides.get(path,(ROOT/path).read_text())
        assert generated==actual and hashlib.sha256(actual.encode()).hexdigest()==row['generated_sha256']
        restored=generated
        for edit in reversed(row['edits']):
            assert restored.count(edit['after'])==edit['count']
            restored=restored.replace(edit['after'],edit['before'])
        assert restored==old
        old_ast=ast.parse(old);new_ast=ast.parse(actual)
        old_functions={n.name:ast.dump(n,include_attributes=False)for n in old_ast.body if isinstance(n,ast.FunctionDef)}
        new_functions={n.name:ast.dump(n,include_attributes=False)for n in new_ast.body if isinstance(n,ast.FunctionDef)}
        assert set(old_functions)==set(new_functions)
        changed=sorted(k for k in old_functions if old_functions[k]!=new_functions[k])
        assert changed==row['changed_functions']
        proof[path]=dict(original_sha256=row['original_sha256'],generated_sha256=row['generated_sha256'],
          edits=len(row['edits']),reverse_exact=True,changed_functions=changed)
    assert len(proof)==5
    return proof
def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=a.methods();rejected=[];positive={}
    def reject(name,call,types=(AssertionError,ValueError,FileExistsError,FileNotFoundError,KeyError)):
        try:call()
        except types:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    positive['derivations']=derivations()
    record=json.loads((ROOT/DERIVATION).read_text())
    for path,row in record['generated'].items():
        reject('changed_original_'+Path(path).stem,lambda p=row['original']:derivations({p:(ROOT/p).read_text()+'\n'}))
        reject('changed_generated_'+Path(path).stem,lambda p=path:derivations({p:(ROOT/p).read_text()+'\n'}))
    reports={s:a.stage_report(s)for s in ('binding','rc')}
    positive['actual_current_stage_reports']={s:dict(sha256=a.sha(a.stage_path(s)),status=r['status'])for s,r in reports.items()}
    def mutate(stage,name,fn):
        bad=copy.deepcopy(reports[stage]);fn(bad)
        reject(stage+'_'+name,lambda:a.validate_stage(stage,bad))
    for stage in reports:
        for key,value in [('source_head','0'*40),('sources_unchanged',False),('status','PASS_OTHER'),
          ('qualified_pex',True),('full_phy_accepted',True),('closed_loop',True)]:
            mutate(stage,key,lambda r,k=key,v=value:r.__setitem__(k,v))
        mutate(stage,'missing_original_integrity',lambda r:r['saved_capsule_integrity'].__setitem__('files',705))
    mutate('binding','missing_device',lambda r:r['binding']['devices'].pop())
    mutate('binding','missing_electrical_node',lambda r:r['binding']['node_map'].pop(next(iter(r['binding']['node_map']))))
    mutate('binding','missing_port',lambda r:r['binding']['native_ports'].pop())
    mutate('binding','old_target_L7_4',lambda r:next(d for d in r['binding']['devices']if d['native_id']==184)['native_parameters'].__setitem__('l','7.4'))
    for key,value in [('l','3.7'),('w','3.7')]:
        mutate('binding','MIM_'+key,lambda r,k=key,v=value:next(d for d in r['binding']['devices']if d['native_id']==273)['native_parameters'].__setitem__(k,v))
    mutate('binding','MIM_plate',lambda r:next(d for d in r['binding']['devices']if d['native_id']==273)['native_nodes'].__setitem__('mim_btm','vip'))
    mutate('binding','missing_native_fault',lambda r:r['controls'].pop())
    mutate('binding','accepted_native_fault',lambda r:r['controls'][0].__setitem__('rejected',False))
    mutate('binding','missing_target_fault',lambda r:r['target_length_controls']['rejected'].pop())
    mutate('binding','missing_contact',lambda r:r['native_contact_comparisons'].pop())
    mutate('binding','missing_contact_fault',lambda r:r['contact_model_controls']['rejected_geometry'].pop())
    for key,value in [('native_device_count',499),('native_terminal_count',1445),('wire_component_count',112),
      ('native_net_count',237),('native_electrical_net_count',113)]:
        mutate('rc',key,lambda r,k=key,v=value:r['geometry'].__setitem__(k,v))
    for key,value in [('logical_anchor_count',977),('physical_anchor_count',977),('public_ports',24)]:
        mutate('rc',key,lambda r,k=key,v=value:r['anchors'].__setitem__(k,v))
    mutate('rc','changed_absolute_anchor_input',lambda r:r['anchors']['inputs'].__setitem__(next(iter(r['anchors']['inputs'])),'0'*64))
    mutate('rc','failed_native_return',lambda r:r['capture'].__setitem__('returncode',1))
    mutate('rc','missing_raw_fault',lambda r:r['controls']['cases'].pop())
    mutate('rc','missing_raw_file',lambda r:r['new_capsule_outputs'].pop(next(iter(r['new_capsule_outputs']))))
    for stage in reports:
        raw=a.recovery.evidence(stage,'-summary.json').read_bytes()
        positive[stage+'_original_summary']=a.recovery.exact_summary(stage,raw)['status']
        reject(stage+'_changed_original_summary',lambda s=stage,b=raw:a.recovery.exact_summary(s,b+b' '))
        positive[stage+'_original_publication_failure']=a.recovery.exact_log(stage,a.recovery.evidence(stage,'.log').read_bytes())
    p=a.descriptor()
    old=dict(id=a.RUN,run_attempt=1,head_sha=a.HEAD,path=a.recovery.WORKFLOW,event='workflow_dispatch',status='completed',conclusion='failure')
    oldjobs=dict(total_count=3,jobs=[dict(id=i,run_id=a.RUN,head_sha=a.HEAD,status='completed',name=n,conclusion=c)for i,n,c in
      [(121168387181,'controls','success'),(121168500687,'native (binding)','failure'),(121168500631,'native (rc)','failure')]])
    new={**p['recovery_run'],'path':'.github/workflows/cdr-v59-publication-recovery-cloud.yml'}
    newjobs=dict(total_count=3,jobs=[{**j,'run_id':new['id'],'head_sha':new['head_sha']}for j in p['recovery_jobs']])
    assert a.validate_runs(old,oldjobs,new,newjobs)
    positive['metadata_fixture_bound_to_actual_ids']=True
    for which,key,value in [('old','conclusion','success'),('old','head_sha','0'*40),('old','run_attempt',2),
      ('old','event','push'),('old','path','wrong.yml'),('new','conclusion','failure'),('new','head_sha','0'*40)]:
        args=copy.deepcopy([old,oldjobs,new,newjobs]);args[0 if which=='old'else 2][key]=value
        reject(which+'_'+key,lambda args=args:a.validate_runs(*args))
    for stage in reports:
        info=copy.deepcopy(p['publications'][stage]);ref=dict(ref='refs/tags/'+info['tag_name'],object=dict(type='commit',sha=a.HEAD))
        assert a.validate_release(stage,info,ref)
        for key,value in [('prerelease',False),('draft',True),('target_commitish','0'*40),('id',1)]:
            bad=copy.deepcopy(info);bad[key]=value
            reject(stage+'_release_'+key,lambda s=stage,v=bad,r=ref:a.validate_release(s,v,r))
        bad=copy.deepcopy(info);bad['assets'][0]['digest']='sha256:'+'0'*64
        reject(stage+'_asset_hash',lambda s=stage,v=bad,r=ref:a.validate_release(s,v,r))
    # Real small archive positive, including an empty file, hidden runtime and
    # distinct outer/inner result. No recovered native archive is opened here.
    with tempfile.TemporaryDirectory()as folder:
        base=Path(folder);bundle=base/'fixture';bundle.mkdir();(bundle/'sys').mkdir()
        for n,b in {'result.json':b'{"original":true}\n','sys/.magicrc':b'fixture-runtime\n','empty.log':b''}.items():(bundle/n).write_bytes(b)
        expected={str(q.relative_to(bundle)):a.sha(q)for q in bundle.rglob('*')if q.is_file()}
        parts=base/'parts';parts.mkdir();packed=pack(bundle,'fixture',parts,113)
        proof=a.saved.exact_extract(packed,parts,base/'positive',expected)
        assert proof['regular_members']==3 and (base/'positive/empty.log').stat().st_size==0
        positive['real_small_full_archive']=dict(members=3,hidden_and_empty_preserved=True,parts=len(packed['parts']))
        reject('occupied_restore_root',lambda:a.saved.exact_extract(packed,parts,base/'positive',expected))
        for name,change in [('missing_member',lambda d:d.pop('empty.log')),('unexpected_expected_member',lambda d:d.__setitem__('extra','0'*64)),
          ('changed_member_hash',lambda d:d.__setitem__('sys/.magicrc','0'*64))]:
            bad=dict(expected);change(bad)
            reject(name,lambda b=bad,n=name:a.saved.exact_extract(packed,parts,base/n,b))
        for label,names in [('duplicate',[('result.json',b'{"original":true}\n'),('result.json',b'{"original":true}\n')]),
          ('traversal',[('../escape',b'x')]),('extra',[('alien',b'x')]),('symlink',[('link',None)])]:
            td=base/label;td.mkdir();path=td/'bad.tar.gz.part0000'
            with tarfile.open(path,'w:gz')as tar:
                for name,data in names:
                    item=tarfile.TarInfo('fixture/'+name)
                    if data is None:item.type=tarfile.SYMTYPE;item.linkname='result.json';tar.addfile(item)
                    else:item.size=len(data);tar.addfile(item,io.BytesIO(data))
            size=path.stat().st_size;digest=a.sha(path)
            bad=dict(format='ordered-tar-gzip-parts-v1',stem='bad',source_directory='fixture',part_limit_bytes=512*1024**2,
              bytes=size,sha256=digest,parts=[dict(index=0,name=path.name,bytes=size,sha256=digest)])
            reject('archive_'+label,lambda b=bad,d=td,n=label:a.saved.exact_extract(b,d,base/(n+'-output'),expected))
        bad=copy.deepcopy(packed);bad['sha256']='0'*64
        reject('combined_archive_hash',lambda:a.saved.exact_extract(bad,parts,base/'wrong-combined',expected))
        first=parts/packed['parts'][0]['name'];data=first.read_bytes();first.write_bytes(data+b'x')
        reject('part_extent',lambda:a.saved.exact_extract(packed,parts,base/'wrong-part',expected));first.write_bytes(data)
        copied=a.saved.copy_selected(bundle,base/'projection',list(expected),expected);assert copied==expected
        reject('projection_collision',lambda:a.saved.copy_selected(bundle,base/'projection',list(expected),expected))
        target=bundle/'sys/.magicrc';data=target.read_bytes();target.unlink();target.symlink_to(bundle/'result.json')
        reject('projection_symlink',lambda:a.saved.copy_selected(bundle,base/'bad-projection',list(expected),expected))
    positive['noncascading_counts']=count_controls((ROOT/'scripts/cloud_cdr_retimed_composition.py').read_text())
    positive['native_cap_order']=tx_native_cap_order.controls()
    assert len(rejected)==m['source_controls']['faults'],(len(rejected),rejected)
    return dict(status='PASS_CURRENT_V59_MIM_SOURCE_CONTROLS_NO_NATIVE',protected_files=len(m['protected']),
      positive=positive,rejected=rejected,source_controls_only=True,archives_downloaded=False,
      native_extraction_executed=False,simulation_executed=False,geometry_regenerated=False,
      original_failed_publication_preserved=True)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
