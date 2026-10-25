#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run one independently authorized v59 stage and preserve its complete evidence."""
import argparse,base64,copy,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
import cdr_v59_binding_rc_source as source
import ensure_cloud_tested_source_release as release
import migrate_outputs_to_cloud as publisher
from cloud_cdr500_resistor_v59_physical import precreated
from cloud_chunked_results import pack,verify_parts,controls as chunk_controls
ROOT=source.ROOT
PASS={
 'binding':'PASS_PD500_NATIVE_MODEL_BINDING_14_FAULTS_AND_NATIVE_CONTACT_ORACLE_REQUIRES_WIRE_COMPOSITION_AND_WAVES',
 'rc':'PASS_PD500_FRESH_NATIVE_WIRE_RC_AND13_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP'}
def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def only_reserved(group,env,read):
    tag,head=release.context(group,env)
    def lookup(requested):
        assert requested==tag
        info=read('releases/tags/'+tag,missing=True)
        assert info is not None,'Exact-source prerelease absent; never create'
        release.validate_release(info,read('git/ref/tags/'+tag),tag,head)
        return info
    return lookup
def copy_tree(root,destination):
    assert root.is_dir()and not root.is_symlink()and not destination.exists()
    destination.mkdir(parents=True);manifest={}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),'Symlink is not regular evidence'
        rel=p.relative_to(root);target=destination/rel
        if p.is_dir():target.mkdir(exist_ok=True);continue
        assert p.is_file(),'Nonregular evidence'
        target.parent.mkdir(parents=True,exist_ok=True)
        before=source.sha(p)
        with p.open('rb')as inp,target.open('xb')as out:shutil.copyfileobj(inp,out,4*1024**2)
        assert before==source.sha(p)==source.sha(target)
        manifest[str(rel)]=dict(bytes=p.stat().st_size,sha256=before)
    return manifest
def validate_stage(stage,report,returncode):
    assert stage in PASS and returncode==0 and report['status']==PASS[stage]
    assert report['source_head']==os.environ['GITHUB_SHA']and report['sources_unchanged']is True
    assert report['qualified_pex']is False and report['full_phy_accepted']is False and report['closed_loop']is False
    assert report['saved_capsule_integrity']==dict(files=706,all_hashes_unchanged=True)
    if stage=='binding':
        assert len(report['controls'])==14 and all(v['rejected']for v in report['controls'])
        assert len(report['target_length_controls']['rejected'])==6 and report['target_length_controls']['actual_fresh_binding']is True
        assert len(report['native_contact_comparisons'])==221
        assert len(report['contact_model_controls']['rejected_geometry'])==len(report['contact_model_controls']['rejected_compact_models'])==3
        source.validate_bound_targets(report['binding'])
    else:
        assert report['capture']['returncode']==0 and report['capture']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        assert report['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert report['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert len(report['controls']['cases'])==13
        assert report['geometry']['native_device_count']==500 and report['geometry']['native_terminal_count']==1446
        assert report['geometry']['wire_component_count']==113 and report['anchors']['logical_anchor_count']==978
    return True
def emit(path,marker):
    data=path.read_bytes()
    assert len(data)<=4*1024**2,'Full result remains durable; console bound exceeded'
    encoded=base64.b64encode(data).decode()
    print(marker+'_BEGIN '+json.dumps(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),chunks=(len(encoded)+4095)//4096)),flush=True)
    for index in range(0,len(encoded),4096):print(marker+'_CHUNK '+str(index//4096)+' '+encoded[index:index+4096],flush=True)
    print(marker+'_END',flush=True)
def publication_controls():
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=release.REPO,GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    group='fixture';tag,head=release.context(group,env)
    info=dict(id=1,tag_name=tag,target_commitish=head,prerelease=True,draft=False,assets=[])
    ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=head))
    calls=[]
    def read(path,missing=False):
        calls.append(path);return copy.deepcopy(info if path.startswith('releases/')else ref)
    lookup=only_reserved(group,env,read);assert lookup(tag)==info and len(calls)==2
    rejected=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,FileExistsError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    reject('different_requested_tag',lambda:lookup(tag+'-other'))
    reject('absent_never_create',lambda:only_reserved(group,env,lambda *a,**k:None)(tag))
    for field,value in [('target_commitish','b'*40),('prerelease',False),('draft',True)]:
        old=info[field];info[field]=value;reject('wrong_'+field,lambda:lookup(tag));info[field]=old
    old=ref['object']['sha'];ref['object']['sha']='b'*40;reject('wrong_tag_source',lambda:lookup(tag));ref['object']['sha']=old
    with tempfile.TemporaryDirectory()as folder:
        base=Path(folder);original=base/'original';original.mkdir()
        (original/'empty.log').write_bytes(b'');(original/'result.json').write_text('{"fixture":true}\n')
        manifest=copy_tree(original,base/'copied')
        assert manifest['empty.log']['bytes']==0 and manifest['result.json']['sha256']==source.sha(original/'result.json')
        reject('copy_destination_exists',lambda:copy_tree(original,base/'copied'))
        (original/'link').symlink_to(original/'result.json')
        reject('copy_symlink',lambda:copy_tree(original,base/'bad'))
    assert len(rejected)==8
    return dict(status='PASS_READ_ONLY_RELEASE_LOOKUP_AND_STREAM_COPY_8_FAULTS',rejected=rejected,
      existing_release_positive=True,stream_copy_positive=True,empty_file_preserved=True,
      release_creation_possible=False,chunk_controls=chunk_controls())
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=PASS);p.add_argument('--preflight',action='store_true')
    p.add_argument('--publication-controls',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.publication_controls:
        assert a.stage is None and not a.preflight
        source.methods();print(json.dumps(publication_controls(),indent=2));return
    assert a.stage in PASS
    source.authorize(a.stage);group='cdr-v59-'+a.stage
    reservation=precreated(group,wait=True)
    if a.preflight:print(json.dumps(reservation,indent=2));return
    stage=ROOT/'hw/soc/out'/('cloud-'+group)
    bundle=ROOT/'hw/soc/out'/('cloud-'+group+'-evidence')
    transport=ROOT/'hw/soc/out'/('cloud-'+group+'-publication')
    assert not stage.exists()and not bundle.exists()and not transport.exists()and not source.CAPSULE.exists()
    bundle.mkdir(parents=True);transport.mkdir(parents=True)
    r=dict(status='RUNNING',stage=a.stage,source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      run_attempt=1,release=reservation,input_run=source.RUN,input_source=source.HEAD,input_summary_sha256=source.SUMMARY_SHA,
      accepted=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,geometry_regenerated=False,
      physical_checks_rerun=False,future_mim_qualified=False,native_stage_passed=False,
      archive_restore_contract=dict(source_capsule='source-capsule',original_absolute_root=str(source.CAPSULE),
        stage_directory='stage',original_inputs=706))
    write(bundle/'result.json',r)
    try:
        command=[sys.executable,str(ROOT/'scripts'/('cloud_cdr_v59_'+a.stage+'.py'))]
        log=bundle/'controller.log'
        with log.open('wb')as stream:
            code=subprocess.call(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=stream,stderr=subprocess.STDOUT)
        r['command']=dict(argv=command,returncode=code,log_sha256=source.sha(log))
        if code:print(log.read_text(errors='replace')[-20000:],flush=True)
        report=json.loads((stage/'result.json').read_text())
        r['stage_status']=report['status'];r['stage_result_sha256']=source.sha(stage/'result.json')
        validate_stage(a.stage,report,code)
        r['saved_capsule_integrity']=source.verify_saved_inputs(json.loads(source.PIN.read_text()))
        source.methods()
        r.update(status='PASS_FRESH_V59_'+a.stage.upper()+'_REQUIRES_NEXT_REVIEWED_STAGE',native_stage_passed=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error))
    finally:
        try:
            if source.CAPSULE.exists():r['source_capsule_copy']=copy_tree(source.CAPSULE,bundle/'source-capsule')
            if stage.exists():r['stage_copy']=copy_tree(stage,bundle/'stage')
        except BaseException as error:r.update(status='FAIL_EVIDENCE_COPY',copy_error=repr(error),native_stage_passed=False)
        r['outputs']={str(q.relative_to(bundle)):source.sha(q)for q in bundle.rglob('*')if q.is_file()and q!=bundle/'result.json'}
        # Both full inventories are in the archived root result; no embedded stage report.
        write(bundle/'result.json',r)
    stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    summary=transport/(stem+'.summary.json');shutil.copyfile(bundle/'result.json',summary)
    assert source.sha(summary)==source.sha(bundle/'result.json')
    emit(summary,'CDR_V59_STAGE_RESULT')
    publication=dict(status='RUNNING',summary_sha256=source.sha(summary),assets=[])
    write(transport/'publication.json',publication)
    try:
        packed=pack(bundle,stem,transport,512*1024**2)
        archive_proof=verify_parts(packed,transport)
        manifest=transport/(stem+'.parts.json');write(manifest,packed)
        publication['archive']=archive_proof;write(transport/'publication.json',publication)
        files=[summary,manifest,*[transport[v['name']]for v in packed['parts']]]
        if(stage/'result.json').is_file():
            full=transport/(stem+'.stage-result.json');shutil.copyfile(stage/'result.json',full)
            assert source.sha(full)==source.sha(stage/'result.json');files.append(full)
        tag,_=release.context(group,os.environ)
        # The original digest/no-overwrite publisher is retained, but its legacy
        # release-creation seam is replaced by a strict read-only reservation lookup.
        old=publisher.release;publisher.release=only_reserved(group,os.environ,release.api)
        try:
            for path in files:
                assert path.stat().st_size>0
                publication['assets'].append(publisher.publish(path,tag));write(transport/'publication.json',publication)
        finally:publisher.release=old
        publication['status']='PASS_COMPLETE_SOURCE_AND_STAGE_EVIDENCE_PUBLISHED';write(transport/'publication.json',publication)
    except BaseException as error:
        publication.update(status='FAIL_PUBLICATION',error=repr(error));write(transport/'publication.json',publication);raise
    assert r['native_stage_passed']is True,r.get('error',r['status'])
if __name__=='__main__':main()
