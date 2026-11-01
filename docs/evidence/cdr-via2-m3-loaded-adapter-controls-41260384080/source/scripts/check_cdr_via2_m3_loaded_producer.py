#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Meaningful hosted source-only current producer and full archive handoff controls."""
import copy,io,json,tarfile,types
from pathlib import Path
import cdr_via2_m3_loaded_producer as p
import cloud_cdr_current_eight_drain_wave_replay as q

def reject(fn,label,records):
    try:fn()
    except (ValueError,RuntimeError,AssertionError,KeyError,TypeError,OSError):records.append(label);return
    raise AssertionError('expected refusal: '+label)

def fixture_archive(path,files,root,mode='normal'):
    with tarfile.open(path,'w:gz')as out:
        items=list(files.items())
        if mode=='missing':items=items[:-1]
        if mode=='extra':items+=[('undeclared.json',b'{}')]
        if mode=='traversal':items+=[('../escaped.json',b'{}')]
        if mode=='duplicate':items+=[items[0]]
        for i,(name,raw)in enumerate(items):
            info=tarfile.TarInfo(root+'/'+name)
            if mode=='symlink'and i==0:info.type=tarfile.SYMTYPE;info.linkname='/tmp/not-owned';out.addfile(info);continue
            if mode=='changed'and i==0:raw+=b'changed'
            info.size=len(raw);out.addfile(info,io.BytesIO(raw))

def controls(root,out):
    """All real metadata is derived JSON; all archived fixture payloads are synthetic."""
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    config=p.decode(p.regular(root,'scripts/cdr-via2-m3-loaded-producer-inputs.json').read_bytes())
    actual=p.metadata(root,config)
    positives=['actual_complete_454_file_metadata']
    refusals=[]
    proof=p.validate_live(config,actual,actual['run'],actual['jobs'],actual['release'],actual['tag'])
    assert proof['members']==3091 and proof['accepted']is False
    positives.append('actual_terminal_run_jobs_release_tag')
    for field,value in [('schema','wrong'),('producer_run_id',1),('producer_source','0'*40),('producer_attempt',2),('loaded_case_scope','nominal_early'),('native_authorization_asserted_by_this_record',True),('qualified_pex',True),('electrical_accepted',True),('full_phy_accepted',True)]:
        c=copy.deepcopy(config);c[field]=value;reject(lambda:p.metadata(root,c),'input_'+field,refusals)
    def live_change(group,key,value,label):
        values={n:copy.deepcopy(actual[n])for n in('run','jobs','release','tag')}
        target=values[group]
        for step in key[:-1]:target=target[step]
        target[key[-1]]=value
        reject(lambda:p.validate_live(config,actual,values['run'],values['jobs'],values['release'],values['tag']),label,refusals)
    for key,value in [('id',1),('head_sha','0'*40),('head_branch','other'),('run_attempt',2),('event','push'),('workflow_id',1),('path','other'),('status','in_progress'),('conclusion','failure')]:live_change('run',[key],value,'run_'+key)
    for key,value in [('total_count',2)]:live_change('jobs',[key],value,'jobs_'+key)
    for key,value in [('run_id',1),('head_sha','0'*40),('name','other'),('conclusion','failure'),('steps',[])]:live_change('jobs',['jobs',0,key],value,'job_'+key)
    for key,value in [('id',1),('target_commitish','main'),('tag_name','other'),('draft',True),('prerelease',False),('assets',[])]:live_change('release',[key],value,'release_'+key)
    for key,value in [('id',1),('size',1),('digest','sha256:'+'0'*64),('state','new'),('content_type','other'),('created_at','changed'),('updated_at','changed')]:live_change('release',['assets',0,key],value,'asset_'+key)
    live_change('tag',['object','type'],'tag','tag_type')
    live_change('tag',['object','sha'],'0'*40,'tag_commit')
    live_change('tag',['ref'],'refs/tags/other','tag_ref')
    for raw in [b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":-Infinity}',b'\xff']:
        reject(lambda:p.decode(raw),'invalid_json_'+str(len(refusals)),refusals)
    files={name:('SYNTHETIC SOURCE CONTROL ONLY '+name+'\n').encode()for name in config['complete_members']}
    synthetic_reports={}
    for name in config['required_reports']:
        synthetic_reports[name]=dict(explicitly_synthetic=True,path=name)
        files[name]=(json.dumps(synthetic_reports[name],sort_keys=True)+'\n').encode()
    fixture=copy.deepcopy(config)
    fixture['complete_members']={n:p.fingerprint(raw)for n,raw in files.items()}
    fixture['required_reports']={n:dict(pin,**p.fingerprint(files[n]))for n,pin in fixture['required_reports'].items()}
    for key in('model','composition','planes'):fixture[key].update(p.fingerprint(files[fixture[key]['path']]))
    expected={n:pin['sha256']for n,pin in fixture['complete_members'].items()}
    archive=out/'synthetic.tar.gz';fixture_archive(archive,files,config['archive_root'])
    restored=out/'restored'
    full=q.select_archive(archive,expected,expected,config['archive_root'],restored)
    fixture['original_output_root']=str(restored)
    g=dict(p.validate_restored.__globals__,CURRENT_ROOT=str(restored))
    restored_validator=types.FunctionType(p.validate_restored.__code__,g,p.validate_restored.__name__,p.validate_restored.__defaults__)
    original=dict(reports=synthetic_reports)
    result=restored_validator(restored,fixture,full,original)
    assert result['complete_members']==3091 and result['original_bytes_unchanged']is True
    positives.append('real_streaming_reader_to_identical_restore_validator_3091_synthetic_members')
    reject(lambda:p.validate_restored(restored,fixture,full,original),'production_absolute_namespace_not_spoofed',refusals)
    for key,value in [('every_member_authenticated',False),('full_member_count',3090),('full_members',{}),('selected',{})]:
        changed=copy.deepcopy(full);changed[key]=value
        reject(lambda:restored_validator(restored,fixture,changed,original),'reader_proof_'+key,refusals)
    member=next(iter(files));path=restored/member;old=path.read_bytes();path.write_bytes(old+b'x')
    reject(lambda:restored_validator(restored,fixture,full,original),'changed_restored_member',refusals);path.write_bytes(old)
    path.unlink();reject(lambda:restored_validator(restored,fixture,full,original),'missing_restored_member',refusals);path.write_bytes(old)
    path.unlink();path.symlink_to(out/'never-read');reject(lambda:restored_validator(restored,fixture,full,original),'linked_restored_member',refusals);path.unlink();path.write_bytes(old)
    extra=restored/'undeclared.json';extra.write_text('{}');reject(lambda:restored_validator(restored,fixture,full,original),'extra_restored_member',refusals);extra.unlink()
    for mode in('missing','extra','traversal','duplicate','symlink','changed'):
        bad=out/(mode+'.tar.gz');fixture_archive(bad,files,config['archive_root'],mode)
        reject(lambda:q.select_archive(bad,expected,expected,config['archive_root'],out/('bad-'+mode)),mode+'_archive',refusals)
    subset=q.select_archive(archive,expected,{member:expected[member]},config['archive_root'],out/'subset')
    reject(lambda:restored_validator(out/'subset',fixture,subset,original),'authenticated_subset_is_not_complete_restore',refusals)
    positives.append('same_complete_source_fixture_retained_after_refusals')
    assert restored_validator(restored,fixture,full,original)['complete_members']==3091
    return dict(positive=len(positives),refusals=len(refusals),positive_cases=positives,refusal_cases=refusals,actual_metadata_proof=dict(files=config['proof']['files'],bytes=config['proof']['bytes'],source=config['proof']['source']),synthetic_archive_members=3091,native_payload_acquired=False,native_execution=False)

if __name__=='__main__':raise SystemExit('Invoke controls under separately reviewed exact-source GitHub workflow only')
