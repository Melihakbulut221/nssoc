#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source, tiny archive and filesystem controls; never execute CAD."""
import ast,copy,hashlib,io,json,os,tarfile,tempfile
from pathlib import Path
import cdr_v59_binding_rc_source as source
from cloud_chunked_results import pack
ROOT=source.ROOT
PROJECTION=ROOT/'docs/evidence/cdr-v59-font-native-device-projection-20261025.json'
def derive(text,record):
    assert hashlib.sha256(text.encode()).hexdigest()==record['original_sha256']
    generated=text
    for edit in record['edits']:
        assert generated.count(edit['before'])==1
        generated=generated.replace(edit['before'],edit['after'])
    assert hashlib.sha256(generated.encode()).hexdigest()==record['generated_sha256']
    restored=generated
    for edit in reversed(record['edits']):
        assert restored.count(edit['after'])==1
        restored=restored.replace(edit['after'],edit['before'])
    assert restored==text
    ast.parse(generated)
    return generated
def function_map(text):
    return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
def source_derivations(m):
    proof=[];bad=[]
    for stage,record in m['derivations'].items():
        before=(ROOT/record['original']).read_text();generated=derive(before,record)
        assert generated==(ROOT/record['generated']).read_text()
        old=function_map(before);new=function_map(generated)
        assert set(old)==set(new)
        unchanged=sorted(n for n in old if n!='main')
        assert all(old[n]==new[n]for n in unchanged)
        assert unchanged==record['unchanged_functions']
        proof.append(dict(stage=stage,edits=len(record['edits']),unchanged_functions=unchanged,
          original_sha256=record['original_sha256'],generated_sha256=record['generated_sha256'],reverse_exact=True))
        for label,mutated,changed in [('source',before+'\n',record),('edits',before,copy.deepcopy(record))]:
            if label=='edits':changed['edits'][0]['after']+='\n'
            try:derive(mutated,changed)
            except AssertionError:bad.append(stage+'_'+label)
            else:raise AssertionError('Accepted changed derivation')
    assert len(proof)==2 and len(bad)==4
    return dict(proof=proof,rejected=bad)
def archive_controls():
    rejected=[]
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);payload=root/'evidence';payload.mkdir();(payload/'result.json').write_text('{"status":"fixture"}\n')
        (payload/'empty.log').write_bytes(b'');expected={n.name:source.sha(n)for n in payload.iterdir()}
        manifest=pack(payload,'fixture',root,127)
        proof=source.exact_extract(manifest,root,root/'positive',expected)
        assert proof['regular_members']==2 and source.verify_files(root/'positive',expected)['files']==2
        def reject(name,fn):
            try:fn()
            except(AssertionError,FileNotFoundError,FileExistsError):rejected.append(name)
            else:raise AssertionError('Accepted '+name)
        for label,edit in [('part_order',lambda x:x['parts'].reverse()),('whole_digest',lambda x:x.update(sha256='0'*64)),('extent',lambda x:x.update(bytes=x['bytes']+1))]:
            m=copy.deepcopy(manifest);edit(m);reject(label,lambda:source.exact_extract(m,root,root/label,expected))
        bad=dict(expected);bad['result.json']='0'*64;reject('member_hash',lambda:source.exact_extract(manifest,root,root/'member_hash',bad))
        bad=dict(expected);bad['missing']='0'*64;reject('missing',lambda:source.exact_extract(manifest,root,root/'missing',bad))
        reject('occupied',lambda:source.exact_extract(manifest,root,root/'positive',expected))
        # Rehash malformed fixture transport so member/path checks, not outer hashes, reject it.
        for label,name,kind in [('extra','evidence/extra',tarfile.REGTYPE),('traversal','evidence/../x',tarfile.REGTYPE),
          ('alias','evidence/./result.json',tarfile.REGTYPE),('backslash','evidence/a'+chr(92)+'b',tarfile.REGTYPE),
          ('symlink','evidence/link',tarfile.SYMTYPE),('hardlink','evidence/link',tarfile.LNKTYPE),
          ('duplicate','evidence/result.json',tarfile.REGTYPE)]:
            archive=root/(label+'.tar.gz.part0000')
            with tarfile.open(archive,'w:gz')as out:
                for n in expected:out.add(payload/n,arcname='evidence/'+n,recursive=False)
                entry=tarfile.TarInfo(name);entry.type=kind;entry.linkname='result.json'if kind!=tarfile.REGTYPE else ''
                out.addfile(entry,io.BytesIO(b'')if kind==tarfile.REGTYPE else None)
            h=source.sha(archive);size=archive.stat().st_size
            m=dict(format='ordered-tar-gzip-parts-v1',stem=label,source_directory='evidence',bytes=size,sha256=h,
              parts=[dict(index=0,name=archive.name,bytes=size,sha256=h)])
            reject(label,lambda:source.exact_extract(m,root,root/(label+'-out'),expected))
        copied=source.copy_selected(payload,root/'copy',list(expected),expected);assert copied==expected
        reject('copy_occupied',lambda:source.copy_selected(payload,root/'copy',list(expected),expected))
        reject('copy_missing',lambda:source.copy_selected(payload,root/'copy_missing',['missing'],expected))
        bad=dict(expected);bad['result.json']='0'*64
        reject('copy_changed',lambda:source.copy_selected(payload,root/'copy_changed',list(expected),bad))
        (root/'positive/result.json').write_text('changed')
        reject('preserved_result_changed',lambda:source.verify_files(root/'positive',expected))
    assert len(rejected)==17
    return dict(actual_tiny_archive_roundtrip=True,zero_byte_log_retained=True,copy_roundtrip=True,
      source_result_not_overwritten=True,rejected=rejected)
def check():
    m=source.methods();inherited=source.font.controls()
    assert len(inherited['rejected'])==18 and len(inherited['font']['rejected'])==16
    derivation=source_derivations(m);r=json.loads(source.PIN.read_text());source.validate_summary(r)
    rejected=[]
    def reject(label,data,change,validator):
        bad=copy.deepcopy(data);change(bad)
        try:validator(bad)
        except(AssertionError,KeyError,ValueError,TypeError):rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    for k,v in [('status','PASS'),('source_head','0'*40),('run_id',0),('accepted',True),
      ('geometry_regenerated',True),('wire_rc_extracted',True),('original_physical_and_planes_rerun',True),
      ('annotation_binding_accepted',False),('strict_wires_executed',False),('original_font_rejection_preserved',False),
      ('all339_analysis_originals_unchanged',False),('all345_restored_files_unchanged',False),('runtime_unchanged',False)]:
        reject('summary_'+k,r,lambda q,k=k,v=v:q.__setitem__(k,v),source.validate_summary)
    for name,edit in [
      ('wrong_graph',lambda q:q['strict_wire_graph'].update(wire_component_count=112)),
      ('body_anchor',lambda q:q['anchors']['dispositions'].update(RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=492)),
      ('missing_output',lambda q:q['outputs'].pop(next(iter(q['outputs'])))),
      ('candidate_gds',lambda q:q['outputs'].update({'analysis-capsule/parent/layout/nssoc_cdr_pd500_resistor_v59.gds':'0'*64})),
      ('missing_font_mutation',lambda q:q['font_roundtrip']['native_controls']['rejected'].pop()),
      ('missing_positive_font',lambda q:q['font_roundtrip']['native_controls'].update(positive_exact_saved_copies=27)),
      ('wrong_font',lambda q:q['font_roundtrip']['serialized'][0]['actual_font_fields'].update(serialized_font=0)),
      ('original_recover_changed',lambda q:q['annotation_materialization'].update(original_recovery_source_unchanged=False)),
      ('missing_materialization_fault',lambda q:q['annotation_materialization']['native_controls']['rejected'].pop()),
      ('missing_wire_command',lambda q:q['commands'].pop())]:
        reject(name,r,edit,source.validate_summary)
    run=dict(id=source.RUN,head_sha=source.HEAD,run_attempt=1,path='.github/workflows/cdr-v59-font-recovery-cloud.yml',
      event='workflow_dispatch',status='completed',conclusion='success')
    jobs=dict(total_count=2,jobs=[dict(id=i,run_id=source.RUN,head_sha=source.HEAD,name=n,status='completed',conclusion='success')
      for i,n in[(121154246625,'controls'),(121154331539,'saved-font-and-strict-wires')]])
    source.validate_run(run,jobs)
    for k,v in [('id',1),('head_sha','0'*40),('run_attempt',2),('conclusion','failure'),('event','push')]:
        reject('run_'+k,run,lambda q,k=k,v=v:q.__setitem__(k,v),lambda q:source.validate_run(q,jobs))
    for k,v in [('id',1),('run_id',1),('head_sha','0'*40),('conclusion','failure')]:
        reject('job_'+k,jobs,lambda q,k=k,v=v:q['jobs'][1].__setitem__(k,v),lambda q:source.validate_run(run,q))
    source.validate_assets(source.ASSETS)
    for k,v in [('id',1),('size',1),('digest','sha256:'+'0'*64),('name','wrong')]:
        reject('asset_'+k,source.ASSETS,lambda q,k=k,v=v:q[0].__setitem__(k,v),source.validate_assets)
    manifest=json.loads(source.PARTS.read_text());source.validate_manifest(manifest)
    for k,v in [('bytes',1),('sha256','0'*64),('source_directory','old-v58')]:
        reject('manifest_'+k,manifest,lambda q,k=k,v=v:q.__setitem__(k,v),source.validate_manifest)
    fixture=json.loads(PROJECTION.read_text())
    assert fixture['source_asset']==674854213 and fixture['source_sha256']=='79ebadf8a36a2be02be680e6d276abbd67c9ddf0bd784a069fa27b96d034e066'
    devices=fixture['devices'];source.validate_targets(devices)
    for ident in source.TARGETS:
        reject('old_length_'+str(ident),devices,lambda q,i=ident:next(d for d in q if d['native_id']==i)['parameters'].update(l=7.4),source.validate_targets)
    reject('target_width',devices,lambda q:next(d for d in q if d['native_id']==184)['parameters'].update(w=5),source.validate_targets)
    reject('target_id',devices,lambda q:next(d for d in q if d['native_id']==184).update(native_id=999),source.validate_targets)
    assert len(rejected)==45
    filesystem=archive_controls()
    return dict(status='PASS_V59_COMPOSED_ADMISSION_DERIVATION_AND_FILESYSTEM_SOURCE_CONTROLS',
      inherited=inherited,rejected=rejected,derivation=derivation,filesystem=filesystem,
      protected_files=len(m['protected']),native_executed=False,geometry_changed=False,new_rc_qualified=False)
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    print(json.dumps(check(),indent=2))
