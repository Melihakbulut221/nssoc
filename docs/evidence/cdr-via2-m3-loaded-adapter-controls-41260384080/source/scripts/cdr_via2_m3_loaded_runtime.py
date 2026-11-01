#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Frozen original loaded runtime acquisition on an authorized GitHub runner only."""
import json,os,shutil,tempfile,traceback
from pathlib import Path
import cdr_via2_m3_loaded_admission as a
q=a.q;require=a.require
def write(path,value):return q.write_new(path,q.encode(value))
CONFIG='scripts/cdr-via2-m3-loaded-runtime-inputs.json'

def records(root=a.ROOT):
    c=q.decode(q.regular(root,CONFIG).read_bytes())
    require(c['schema']=='cdr-via2-m3-loaded-runtime-inputs-v1'and c['native_authorization_asserted_by_this_record']is c['local_native_payload_acquired']is False,'runtime input scope')
    d={}
    for name,pin in c['records'].items():
        raw=q.regular(root,name).read_bytes();require(q.fingerprint(raw)==pin,'historical runtime record '+name);d[Path(name).name]=q.decode(raw)
    p=c['producer'];summary=d['pump-summary.json'];parts=d['pump-parts.json']
    require(p['run_id']==39029337682 and p['source']==summary['source_head']=='e29107296dc3abe0bcb15c57de0a7cbac67dc0e7','original loaded runtime producer')
    require(p['conclusion']=='failure'and p['historical_failed_measurement_preserved']is True and summary['status']=='FAIL_OR_ERROR','historical pump rejection is preserved')
    for flag in('accepted','full_phy_accepted','qualified_pex','acquisition_accepted'):require(summary[flag]is False,'no inherited runtime acceptance')
    require(len(summary['outputs'])==119 and 'result.json'not in summary['outputs'],'complete original output hash inventory')
    require(parts['source_directory']==p['archive_root']and parts['bytes']==p['archive_bytes']and parts['sha256']==p['archive_sha256'],'original runtime archive identity')
    require(len(parts['parts'])==1 and parts['parts'][0]['index']==0 and parts['parts'][0]['bytes']==parts['bytes']and parts['parts'][0]['sha256']==parts['sha256'],'single exact original runtime part')
    require(parts['verification']==dict(parts=1,bytes=parts['bytes'],sha256=parts['sha256'],all_parts_and_combined_bytes_verified=True),'original combined archive verification')
    require(summary['outputs']['source/runtime/patched-ngspice']==p['engine_sha256']=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509','frozen original loaded engine')
    require(summary['outputs']['source-pin.json']==p['model_pin_sha256']=='436914ae3ef1e1727b31e799317cfd92354cf00a00839527f49fcb079b9da1a6','original model pin')
    return c,d

def validate_live(c,d,run,jobs,release,tag):
    p=c['producer'];old=d['pump-run.json']
    for field in('id','head_sha','head_branch','run_attempt','event','workflow_id','path','status','conclusion'):require(run[field]==old[field],'historical runtime run '+field)
    require(run['id']==p['run_id']and run['head_sha']==p['source']and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure','exact failed historical producer retained')
    oldjobs=d['pump-jobs.json'];require(jobs['total_count']==len(jobs['jobs'])==oldjobs['total_count']==1,'complete historical runtime job')
    for field in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps'):require(jobs['jobs'][0][field]==oldjobs['jobs'][0][field],'historical runtime job '+field)
    require(release['id']==p['release_id']and release['tag_name']==p['tag']and release['target_commitish']==p['actual_target_commitish'],'historical release target')
    for field in('draft','prerelease'):require(release[field]==d['pump-release.json'][field],'historical release visibility')
    require(tag['object']['type']=='commit'and tag['object']['sha']==p['actual_tag_commit']==p['source']and tag['ref']=='refs/tags/'+p['tag'],'exact historical tag')
    assets={x['name']:x for x in release['assets']};require(len(assets)==len(release['assets'])==len(p['assets'])==3,'complete historical assets')
    for pin in p['assets']:
        row=assets[pin['name']]
        require(row['id']==pin['id']and row['size']==pin['bytes']and row['digest']=='sha256:'+pin['sha256'],'historical runtime asset bytes')
        for field in('state','content_type','created_at','updated_at'):require(row[field]==pin[field],'historical runtime asset identity')
    return dict(run_id=p['run_id'],source=p['source'],conclusion='failure',historical_failed_measurement_preserved=True,release_id=p['release_id'],engine_sha256=p['engine_sha256'],new_execution_authority=False)

def archive_contract(c,d):
    summary=d['pump-summary.json'];prefix='source/model-sources/'
    expected=dict(summary['outputs']);expected['result.json']=next(pin['sha256']for name,pin in c['records'].items()if name.endswith('/pump-summary.json'))
    selected={name:expected[name]for name in expected if name.startswith(prefix)or name in('source-pin.json','source/runtime/patched-ngspice','result.json')}
    require(len(expected)==c['producer']['declared_members']==120 and len(selected)==c['producer']['selected_members']==40,'complete runtime and exact selected census')
    return expected,selected

def verify_restored(c,d,restored,proof):
    expected,selected=archive_contract(c,d)
    require(proof['every_member_authenticated']is True and proof['full_member_count']==len(expected)and set(proof['full_members'])==set(expected),'all original runtime members authenticated')
    require(all(proof['full_members'][name]['sha256']==digest for name,digest in expected.items()),'every original runtime byte hash')
    require(set(proof['selected'])==set(selected)and all(proof['selected'][n]==proof['full_members'][n]for n in selected),'exact complete selected runtime')
    observed={}
    for path in restored.rglob('*'):
        require(not path.is_symlink(),'no restored runtime links')
        if path.is_file():observed[path.relative_to(restored).as_posix()]=q.file_pin(path)
        else:require(path.is_dir(),'no restored runtime special files')
    require(observed==proof['selected'],'exact restored runtime set and bytes')
    original=q.decode(q.regular(restored,'source-pin.json').read_bytes());models=original['preparation']['model_sources']
    require(len(models)==37 and set('source/model-sources/'+n for n in models)==set(n for n in selected if n.startswith('source/model-sources/')),'complete original model library')
    require(all(observed['source/model-sources/'+n]['sha256']==digest for n,digest in models.items()),'all original model source hashes')
    require(q.decode(q.regular(restored,'result.json').read_bytes())==d['pump-summary.json'],'unchanged original rejected runtime summary')
    engine=q.regular(restored,'source/runtime/patched-ngspice');require(q.file_pin(engine)['sha256']==c['producer']['engine_sha256'],'frozen executable bytes')
    engine.chmod(0o755);require(os.access(engine,os.X_OK),'frozen engine executable permission')
    return dict(lib=str(restored/'source/model-sources'),engine=str(engine),source_pin=str(restored/'source-pin.json'),models_summary=str(restored/'result.json'))

def acquire(root,out,ctx,config,producer,budget):
    """Admission before acquisition; every archived member is hashed on the runner."""
    a.source_guard(ctx,root,budget);a.native_preflight(out/'preflight.json',ctx,config,producer,root)
    c,d=records(root);p=c['producer'];cache=out/'runtime';require(not cache.exists(),'new runtime cache');cache.mkdir()
    report=dict(status='RUNNING',context=ctx,native_execution=False,historical_failed_measurement_preserved=True)
    temp=None;primary=None
    try:
        for suffix in('',):
            live=[a.api('actions/runs/'+str(p['run_id']),budget),a.api('actions/runs/'+str(p['run_id'])+'/attempts/1/jobs?per_page=100',budget),a.api('releases/'+str(p['release_id']),budget),a.api('git/ref/tags/'+p['tag'],budget)]
            for name,value in zip(('run','jobs','release','ref'),live,strict=True):write(cache/('producer-'+name+suffix+'.json'),value)
            report['producer_binding']=validate_live(c,d,*live)
        free=shutil.disk_usage(out).free;needed=max(256*1024**2,p['archive_bytes']*4)
        write(cache/'storage-before.json',dict(free_bytes=free,required_bytes=needed))
        require(free>=needed,'insufficient runtime acquisition disk')
        temp=Path(tempfile.mkdtemp(prefix='loaded-runtime-',dir=out))
        asset=next(x for x in p['assets']if x['name']==d['pump-parts.json']['parts'][0]['name'])
        archive=temp/asset['name'];a.download(asset,archive,budget)
        expected,selected=archive_contract(c,d)
        full=q.select_archive(archive,expected,selected,p['archive_root'],cache/'restored')
        write(cache/'complete-input-census.json',full)
        paths=verify_restored(c,d,cache/'restored',full)
        report.update(status='PASS_FROZEN_ORIGINAL_LOADED_RUNTIME_BYTES_NO_TRANSIENT',runtime_paths=paths,full_member_count=full['full_member_count'],selected_count=len(full['selected']))
        a.source_guard(ctx,root,budget);a.native_preflight(out/'preflight.json',ctx,config,producer,root)
        live=[a.api('actions/runs/'+str(p['run_id']),budget),a.api('actions/runs/'+str(p['run_id'])+'/attempts/1/jobs?per_page=100',budget),a.api('releases/'+str(p['release_id']),budget),a.api('git/ref/tags/'+p['tag'],budget)]
        for name,value in zip(('run','jobs','release','ref'),live,strict=True):write(cache/('producer-'+name+'-after.json'),value)
        require(validate_live(c,d,*live)==report['producer_binding'],'unchanged historical runtime publication')
        return paths
    except BaseException as error:
        primary=error;report.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        cleanup=[]
        if temp is not None:
            if primary is None:
                try:shutil.rmtree(temp)
                except BaseException as error:cleanup.append(repr(error))
            else:report['retained_failed_acquisition']=dict(path=str(temp),native_bytes_remain_cloud_only=True,complete_or_partial=True)
        report['cleanup_errors']=cleanup
        try:write(cache/'result.json',report)
        except BaseException as error:
            try:print(json.dumps(dict(unsaved_runtime_result=report,secondary_save_error=repr(error)),sort_keys=True),flush=True)
            except BaseException:pass
            if primary is None:raise
        if cleanup and primary is None:raise RuntimeError('runtime cleanup failed: '+repr(cleanup))

if __name__=='__main__':raise SystemExit('Library only; no standalone runtime acquisition authority')
