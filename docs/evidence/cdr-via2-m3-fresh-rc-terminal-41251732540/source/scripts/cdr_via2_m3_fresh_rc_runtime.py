#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound cloud runtime acquisition; historical inputs confer no authority."""
import hashlib,json,os,shutil,tarfile,tempfile
from pathlib import Path
import cdr_via2_m3_fresh_rc_admission as a
import cdr_via2_m3_fresh_rc_producer as producer
from run_cloud_tx_layout_repair import fetch
q=a.q;require=a.require;encode=a.encode;write=q.write_new;pin=q.file_pin
CONFIG='scripts/cdr-via2-m3-fresh-rc-runtime-inputs.json'

def records(root=a.ROOT):
    c=q.decode(q.regular(root,CONFIG).read_bytes());require(c['schema']=='cdr-via2-m3-fresh-rc-runtime-inputs-v1','runtime schema')
    require(c['native_authorization_asserted_by_this_record']is c['local_native_payload_acquired']is False,'historical runtime grants no authority')
    data={}
    for name,p in c['records'].items():
        raw=q.regular(root,name).read_bytes();require(q.fingerprint(raw)==p,'exact historical runtime record '+name);data[Path(name).name]=q.decode(raw)
    summary=data['precise-summary.json'];parts=data['precise-parts.json'];p=c['precise']
    require(summary['source_head']==p['source']and summary['status']=='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE','actual precise producer qualification')
    for key in ('sources_unchanged','baseline_reproduced_original_rc_and_failure','no_rc_records_changed','no_geometry_technology_or_threshold_change','both_native_input_orders_verified'):require(summary[key]is True,'original runtime gate '+key)
    require(summary['source_changes']['changed_only']=='resis/resis.h'and len(summary['controls']['cases'])==len(summary['historical_controls']['cases'])==13,'unchanged precise runtime qualification')
    require(summary['rebuilt_runtimes']['precise']['sha256']==summary['outputs']['precise-source/magic/tclmagic.so']==p['library_sha256'],'exact frozen precise library')
    require(p['historical_difference_preserved']is True and p['tag_source_equal']is False and p['source']!=p['actual_tag_commit'],'honest historical tag/source distinction')
    require(len(parts['parts'])==1 and parts['parts'][0]['index']==0 and parts['parts'][0]['bytes']==parts['bytes']and parts['parts'][0]['sha256']==parts['sha256'],'single authentic precise archive')
    require(parts['verification']==dict(parts=1,bytes=parts['bytes'],sha256=parts['sha256'],all_parts_and_combined_bytes_verified=True),'original complete archive verification')
    return c,data

def validate_precise_live(c,d,run,jobs,release,tag):
    p=c['precise'];old=d['precise-run.json']
    for field in ('id','head_sha','head_branch','run_attempt','event','workflow_id','path','status','conclusion'):require(run[field]==old[field],'precise producer run '+field)
    require(run['id']==p['run_id']and run['head_sha']==p['source']and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='success','actual successful historical runtime producer')
    oldjobs=d['precise-jobs.json'];require(jobs['total_count']==len(jobs['jobs'])==oldjobs['total_count']==1,'complete historical runtime jobs')
    for field in ('id','run_id','run_attempt','head_sha','name','status','conclusion','steps'):require(jobs['jobs'][0][field]==oldjobs['jobs'][0][field],'historical runtime job '+field)
    require(release['id']==p['release_id']and release['tag_name']==p['tag']and release['target_commitish']==p['actual_target_commitish'],'actual historical release target preserved')
    for field in ('draft','prerelease'):require(release[field]==d['precise-release.json'][field],'historical release visibility')
    require(tag['object']['type']=='commit'and tag['object']['sha']==p['actual_tag_commit']and tag['ref']=='refs/tags/'+p['tag'],'actual historical tag preserved separately from source')
    assets=release['assets'];require(len(assets)==len({x['name']for x in assets})==3,'all historical runtime assets')
    actual={x['name']:x for x in assets};oldassets={x['name']:x for x in d['precise-release.json']['assets']}
    for asset in p['assets']:
        row=actual[asset['name']];require(row['id']==asset['id']and row['size']==asset['bytes']and row['digest']=='sha256:'+asset['sha256']and row['state']=='uploaded','historical runtime asset bytes')
        for field in ('created_at','updated_at','content_type'):require(row[field]==oldassets[asset['name']][field],'historical runtime asset identity')
    return dict(run_id=p['run_id'],source=p['source'],tag_commit=p['actual_tag_commit'],target_commitish=p['actual_target_commitish'],tag_source_equal=False,library_sha256=p['library_sha256'],new_execution_authority=False)

def safe_unpack(archive,destination):
    require(not destination.exists()and not destination.is_symlink(),'new runtime extraction root');destination.mkdir(parents=True)
    observed={};seen=set();total=0
    with tarfile.open(archive,'r|gz')as tar:
        for member in tar:
            name=member.name.rstrip('/')if member.isdir()else member.name
            if name in ('','.'):require(member.isdir(),'runtime archive root');continue
            if name.startswith('./'):name=name[2:]
            producer.relative(name);require(name not in seen,'duplicate runtime archive path');seen.add(name)
            path=destination/name
            require(member.isdir()or(member.isfile()and not member.issparse()),'runtime link/special/sparse refused')
            if member.isdir():path.mkdir(parents=True,exist_ok=True);continue
            require(0<=member.size<=2*1024**3,'runtime member bound');total+=member.size;require(total<=8*1024**3,'runtime expansion bound')
            path.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
            with tar.extractfile(member)as src,path.open('xb')as dst:
                while block:=src.read(1024*1024):dst.write(block);digest.update(block);size+=len(block)
            require(size==member.size,'runtime complete member bytes');os.chmod(path,member.mode&0o777);observed[name]=dict(bytes=size,sha256=digest.hexdigest())
    require(observed,'nonempty runtime archive');return observed

def verify_manifest(destination,observed):
    manifest=q.decode(q.regular(destination,'manifest.json').read_bytes());require(type(manifest['files'])is dict and manifest['files'],'runtime manifest')
    for name,p in manifest['files'].items():
        require(name in observed and pin(q.regular(destination,name))==p==observed[name],'every original runtime manifest byte '+name)
    return dict(manifest=manifest,manifest_pin=pin(destination/'manifest.json'),complete_extracted_members=observed,manifest_listed_members_verified=True,whole_authenticated_archive_members_hashed=True)

def copy_owned(source,destination,members):
    require(not destination.exists()and not destination.is_symlink(),'new runtime copy');destination.mkdir(parents=True)
    for name,p in members.items():
        raw=q.regular(source,name);require(pin(raw)==p,'runtime source unchanged');target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        with raw.open('rb')as src,target.open('xb')as dst:shutil.copyfileobj(src,dst)
        shutil.copymode(raw,target,follow_symlinks=False)
        require(pin(target)==p and(target.stat().st_mode&0o777)==(raw.stat().st_mode&0o777),'runtime copy byte and mode equality')
    return dict(files=len(members),all_actual_bytes_preserved=True)

def acquire(out,preflight,ctx,config,producer_config,api_call=q.api,download=q.download,fetch_call=fetch):
    require(out==a.OUT,'exact fresh RC root');a.source_guard(ctx);a.native_preflight(preflight,ctx,config,producer_config)
    c,d=records();owned=out/'runtime-inputs';require(not owned.exists()and not owned.is_symlink(),'new owned runtime cache');owned.mkdir()
    primary=None;result=dict(status='RUNNING_RUNTIME_ACQUISITION',native_extraction_executed=False,new_execution_authority=False)
    def live(suffix):
        p=c['precise'];values=[]
        for name,path in (('run','actions/runs/'+str(p['run_id'])),('jobs','actions/runs/'+str(p['run_id'])+'/attempts/1/jobs?per_page=100'),('release','releases/'+str(p['release_id'])),('tag-ref','git/ref/tags/'+p['tag'])):
            value=api_call(path);values.append(value);write(owned/('precise-'+name+suffix+'.json'),encode(value))
        return validate_precise_live(c,d,*values)
    temp=tempfile.TemporaryDirectory(prefix='fresh-rc-runtime-',dir=out.parent)
    try:
        result['historical_precise_binding']=live('')
        for name in ('frozen_layout','models','magic'):
            spec=c[name];receipt=spec['receipt'];source=q.decode(q.regular(a.ROOT,spec['source_path']).read_bytes());require(source['receipt']==receipt,'original receipt source equality')
            packed=Path(temp.name)/(name+'.tar.gz');fetch_call(receipt['url'],receipt['sha256'],packed);require(pin(packed)==dict(bytes=receipt['bytes'],sha256=receipt['sha256']),'exact complete runtime archive')
            destination=owned/name;observed=safe_unpack(packed,destination);proof=verify_manifest(destination,observed);result[name]=proof;write(owned/(name+'-inventory.json'),encode(proof));packed.unlink()
        frozen=result['frozen_layout']['manifest'];require(frozen==d['frozen-layout-runtime-manifest.json']and len(frozen['files'])==197,'same complete original frozen197 runtime')
        for name,p in frozen['files'].items():
            source=q.regular(owned/'frozen_layout',name);target=a.ROOT/name
            require(not target.is_symlink()and not any(x.is_symlink()for x in target.parents),'runtime target ownership')
            if target.exists():require(pin(target)==p,'existing source/native runtime cannot be overwritten')
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with source.open('rb')as src,target.open('xb')as dst:shutil.copyfileobj(src,dst)
            require(pin(target)==p,'original runtime file equality')
        models=owned/'models/models';model_files=publisher_inventory(models);copy_owned(models,a.ROOT/'pdk/libs.tech/ngspice/models',model_files)
        from build_cdr500_cleaned_native_models import MODEL_PINS
        for name,digest in MODEL_PINS.items():require(pin(q.regular(a.ROOT/'pdk',name))['sha256']==digest,'all original frozen model pins '+name)
        write(owned/'model-pins.json',encode(MODEL_PINS))
        magiclib=q.regular(owned/'magic','runtime/lib/magic/tcl/tclmagic.so');require(pin(magiclib)['sha256']==c['magic']['library_sha256'],'frozen baseline Magic')
        parts=d['precise-parts.json'];part=parts['parts'][0];asset=next(x for x in c['precise']['assets']if x['name']==part['name']);archive=Path(temp.name)/part['name'];download(asset,archive)
        require(pin(archive)==dict(bytes=parts['bytes'],sha256=parts['sha256']),'entire historical precise archive bytes')
        expected=dict(d['precise-summary.json']['outputs']);expected['result.json']=c['records'][next(n for n in c['records']if n.endswith('/precise-summary.json'))]['sha256']
        require(len(expected)==c['precise']['declared_archive_members'],'declared exact original member census')
        restored=q.select_archive(archive,expected,c['precise']['selected'],parts['source_directory'],owned/'precise')
        require(q.decode(q.regular(owned/'precise','result.json').read_bytes())==d['precise-summary.json'],'original runtime result retained exactly')
        require(pin(q.regular(owned/'precise','precise-source/magic/tclmagic.so'))['sha256']==c['precise']['library_sha256'],'selected immutable precise library')
        result['precise_full_archive']=restored;write(owned/'precise-complete-census.json',encode(restored));result['historical_precise_binding_after']=live('-after')
        a.source_guard(ctx);a.native_preflight(preflight,ctx,config,producer_config)
        result.update(status='PASS_AUTHENTICATED_RUNTIME_INPUTS_ONLY_NO_EXTRACTION',all_original_model_pins_verified=True)
    except BaseException as error:primary=error;result.update(status='FAIL_RUNTIME_ACQUISITION',error=repr(error))
    finally:
        try:temp.cleanup()
        except BaseException as error:
            result['cleanup_error']=repr(error)
            if primary is None:primary=error
        try:write(owned/'result.json',encode(result))
        except BaseException as error:
            print('UNSAVED_FRESH_RC_RUNTIME '+encode(dict(result,save_error=repr(error))).decode(),flush=True)
            if primary is None:primary=error
    if primary is not None:raise primary
    return result

def publisher_inventory(root):
    from publish_cdr_via2_m3_fresh_rc import inventory
    return inventory(root)

if __name__=='__main__':raise SystemExit('Runtime library only; no standalone acquisition authority')
