#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish two already completed native stages from exact Actions fallback artifacts."""
import argparse,base64,copy,hashlib,io,json,os,re,shutil,stat,struct,subprocess,tarfile,tempfile,traceback,zipfile
from pathlib import Path,PurePosixPath
import cdr_v59_binding_rc_source as original
import cloud_cdr_v59_binding_rc as wrapper
import ensure_cloud_tested_source_release as release
import migrate_outputs_to_cloud as publisher
from cloud_chunked_results import verify_parts
from cloud_verified_parts import JoinedParts
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-publication-recovery-methods.json'
RUN=40193186762
HEAD='572269f839f34435127a053bdea6a779c2b452fd'
WORKFLOW='.github/workflows/cdr-v59-binding-rc-cloud.yml'
RECEIPT='docs/evidence/cdr-v59-binding-rc-native-publication-failure-20261025.json'
RECEIPT_SHA='4a93457c6042241fc618160cbe18d55218fa87de8392e1096fab286dff44738a'
PIN={
 'binding':dict(job=121168500687,artifact=12599485176,zip_bytes=73824799,zip_sha256='8ebc698234462aba26e8b3853bffa6fb3314ae3eff65224321feaa3e55f5cb00',members=1528,
   summary_bytes=253582,summary_sha256='21625f9833ca9efe500f9eab932a4b032a0f2f74f261663dccc06775b2966f23',chunks=83,
   log_bytes=377105,log_sha256='3b5f3bb7caf35934919f50638604737c58a999f6196f28818efce02b535bc3ef',
   stage_sha256='b5389f23f31f9058d0f894c8ca14008c038469ac8811a093be6beb11b0c2e1c4',
   release=423388618,source_files=706,stage_files=55,bundle_files=763),
 'rc':dict(job=121168500631,artifact=12599130920,zip_bytes=95034331,zip_sha256='2e427b2b529c7dde6b982a5370bd9e153cc8f1cd02c87c2db91eff0c6cfdaa8b',members=2270,
   summary_bytes=383941,summary_sha256='c91b2695adf5d93b5b497b9aeb8537dbb331d023b9ad1ecab87a06261adcfcaf',chunks=125,
   log_bytes=552810,log_sha256='49ab4c67db12fbe0921721212d818fe1a0204f8296779408141f46a4a7f73ff2',
   stage_sha256='bec9b8c416a62efe9cfe9aa5bca0b6dce53dfe6661c7fbef4423dc48a086a303',
   release=423388657,source_files=1127,stage_files=7,bundle_files=1136)}
HIDDEN_RC=['analysis-capsule/magic-cloud/runtime/lib/magic/sys/.initrc','analysis-capsule/magic-cloud/runtime/lib/magic/sys/.magicrc']
ERROR="TypeError(\"'PosixPath' object is not subscriptable\")"
def sha(path):return original.sha(path)
def write(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def names(stage):
    assert stage in PIN
    group='cdr-v59-'+stage;stem=group+'-'+str(RUN)+'-1'
    return dict(group=group,stem=stem,tag='cloud-results-'+str(RUN)+'-1-'+group,
      bundle='cloud-'+group+'-evidence',stage='cloud-'+group,transport='cloud-'+group+'-publication')
def evidence(stage,suffix):
    return ROOT/('docs/evidence/cdr-v59-'+stage+'-native-publication-failure-20261025'+suffix)
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='EXACT_EXISTING_ACTIONS_ARTIFACT_PUBLICATION_ONLY_NO_NATIVE_OR_NEW_EXTRACTION'
    assert m['original_run']==RUN and m['original_head']==HEAD and m['original_attempt']==1
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    assert sha(ROOT/RECEIPT)==RECEIPT_SHA
    assert original.methods()['binding_authorized']is False and original.methods()['rc_authorized']is False
    return m
def safe_name(name):
    assert isinstance(name,str)and name and chr(92)not in name and '\0'not in name
    p=PurePosixPath(name)
    assert not p.is_absolute()and p.as_posix()==name and all(v not in ('','.','..')for v in name.split('/'))
    return name
def hidden(name):return any(v.startswith('.')for v in name.split('/'))
def exact_summary(stage,data):
    pin=PIN[stage]
    assert len(data)==pin['summary_bytes']and hashlib.sha256(data).hexdigest()==pin['summary_sha256']
    r=json.loads(data)
    assert r['source_head']==HEAD and r['run_id']==RUN and r['run_attempt']==1 and r['stage']==stage
    assert r['status']=='PASS_FRESH_V59_'+stage.upper()+'_REQUIRES_NEXT_REVIEWED_STAGE'
    assert r['native_stage_passed']is True and r['command']['returncode']==0 and r['stage_status']==wrapper.PASS[stage]
    assert r['stage_result_sha256']==pin['stage_sha256']
    assert r['saved_capsule_integrity']==dict(files=706,all_hashes_unchanged=True)
    for field in ['accepted','qualified_pex','electrical_accepted','full_phy_accepted','geometry_regenerated','physical_checks_rerun','future_mim_qualified']:
        assert r[field]is False
    assert r['archive_restore_contract']==dict(source_capsule='source-capsule',original_absolute_root=str(original.CAPSULE),stage_directory='stage',original_inputs=706)
    assert len(r['source_capsule_copy'])==pin['source_files']and len(r['stage_copy'])==pin['stage_files']and len(r['outputs'])+1==pin['bundle_files']
    expected={'controller.log':r['command']['log_sha256']}
    for prefix,key in [('source-capsule','source_capsule_copy'),('stage','stage_copy')]:
        for n,v in r[key].items():
            safe_name(n);assert isinstance(v['bytes'],int)and v['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',v['sha256'])
            expected[prefix+'/'+n]=v['sha256']
    assert r['outputs']==expected
    prior=json.loads(original.PIN.read_text())
    originals={**prior['outputs'],'result.json':original.SUMMARY_SHA}
    assert len(originals)==706
    for n,h in originals.items():assert r['source_capsule_copy'][n]['sha256']==h
    assert sorted(n for n in r['source_capsule_copy']if hidden(n))==(HIDDEN_RC if stage=='rc'else[])
    assert not any(hidden(n)for n in r['stage_copy'])
    return r
def exact_log(stage,data):
    pin=PIN[stage]
    assert len(data)==pin['log_bytes']and hashlib.sha256(data).hexdigest()==pin['log_sha256']
    lines=[re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ','',v)for v in data.decode().splitlines()]
    begin=[json.loads(v.split(' ',1)[1])for v in lines if v.startswith('CDR_V59_STAGE_RESULT_BEGIN ')]
    chunks=[v.split(' ',2)for v in lines if v.startswith('CDR_V59_STAGE_RESULT_CHUNK ')]
    assert begin==[dict(bytes=pin['summary_bytes'],sha256=pin['summary_sha256'],chunks=pin['chunks'])]
    assert [int(v[1])for v in chunks]==list(range(pin['chunks']))and lines.count('CDR_V59_STAGE_RESULT_END')==1
    decoded=base64.b64decode(''.join(v[2]for v in chunks),validate=True)
    assert decoded==evidence(stage,'-summary.json').read_bytes();exact_summary(stage,decoded)
    index=lines.index('Traceback (most recent call last):')
    expected=json.loads((ROOT/RECEIPT).read_text())['stages'][stage]['traceback']
    assert lines[index:index+8]==expected
    assert "files=[summary,manifest,*[transport[v['name']]for v in packed['parts']]]"in lines[index+5]
    return dict(bytes=len(data),sha256=pin['log_sha256'],full_summary_chunks_verified=True,original_failure_reproduced=True)
def validate_metadata(stage,run,jobs,artifact):
    pin=PIN[stage]
    assert run['id']==RUN and run['run_attempt']==1 and run['head_sha']==HEAD and run['path']==WORKFLOW
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='failure'
    assert jobs['total_count']==len(jobs['jobs'])==3
    wanted={121168387181:('controls','success'),121168500687:('native (binding)','failure'),121168500631:('native (rc)','failure')}
    assert {j['id']for j in jobs['jobs']}==set(wanted)
    for j in jobs['jobs']:
        assert j['run_id']==RUN and j['head_sha']==HEAD and j['status']=='completed'
        assert(j['name'],j['conclusion'])==wanted[j['id']]
        if j['id']==pin['job']:
            steps={v['name']:v['conclusion']for v in j['steps']}
            assert steps['Require authorization and precreated exact-source prerelease before dependencies']=='success'
            assert steps['Restore the original pinned native CAD runtime']=='success'
            assert steps['Fresh binding or raw RC with complete immutable publication']=='failure'
            assert steps['Preserve original capsule and every complete or partial output']=='success'
    assert artifact['id']==pin['artifact']and artifact['name']==names(stage)['stem']
    assert artifact['size_in_bytes']==pin['zip_bytes']and artifact['digest']=='sha256:'+pin['zip_sha256']and artifact['expired']is False
    assert artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==HEAD
    assert artifact['workflow_run']['head_branch']=='codex/cdr-v59-headroom-hypotheses'
    return True
def original_release(stage):
    n=names(stage);info=release.api('releases/tags/'+n['tag'])
    assert info['id']==PIN[stage]['release']
    release.validate_release(info,release.api('git/ref/tags/'+n['tag']),n['tag'],HEAD)
    return info
def original_lookup(stage):
    def lookup(tag):
        assert tag==names(stage)['tag']
        return original_release(stage)
    return lookup
def file_identity(path,size,digest):
    assert path.is_file()and not path.is_symlink()and path.stat().st_size==size and sha(path)==digest
    return True
def validate_raw_command(endpoint,command):
    allowed={value for p in PIN.values()for value in ['actions/jobs/'+str(p['job'])+'/logs','actions/artifacts/'+str(p['artifact'])+'/zip']}
    assert endpoint in allowed
    assert command==['gh','api','--allow-escape-sequences','repos/'+release.REPO+'/'+endpoint]
    return True
def download_raw(endpoint,path,size,digest):
    command=['gh','api','--allow-escape-sequences','repos/'+release.REPO+'/'+endpoint]
    validate_raw_command(endpoint,command)
    with path.open('xb')as out:subprocess.run(command,stdout=out,check=True)
    file_identity(path,size,digest)
def zip_inventory(path,expected_count):
    # The complete ZIP hash is checked before parsing. Also reject trailing/comment junk,
    # duplicate/aliased names, encryption and nonregular members; support ZIP64 extents.
    size=path.stat().st_size
    with path.open('rb')as f:
        tail_size=min(size,65557);f.seek(size-tail_size);tail=f.read()
        index=tail.rfind(b'PK\x05\x06');assert index>=0
        values=struct.unpack('<4s4H2LH',tail[index:index+22]);eo=size-tail_size+index
        assert values[1]==values[2]==0 and values[3]==values[4]and values[7]==0 and eo+22==size
        count=values[4];cd_size=values[5];cd_offset=values[6]
        f.seek(eo-20);locator=f.read(20)
        if locator[:4]==b'PK\x06\x07'or count==65535 or cd_size==0xffffffff or cd_offset==0xffffffff:
            sig,disk,offset,disks=struct.unpack('<4sLQL',locator)
            assert sig==b'PK\x06\x07'and disk==0 and disks==1
            f.seek(offset);record=f.read(56)
            sig,length,made,need,disk,cd_disk,entries_disk,count,cd_size,cd_offset=struct.unpack('<4sQ2H2L4Q',record)
            assert sig==b'PK\x06\x06'and length==44 and disk==cd_disk==0 and entries_disk==count
            assert offset+56==eo-20 and cd_offset+cd_size==offset
        else:assert cd_offset+cd_size==eo
        assert count==expected_count
    with zipfile.ZipFile(path)as archive:
        members=archive.infolist();assert len(members)==expected_count and archive.start_dir==cd_offset
        seen=set();headers=set();inventory={}
        for item in members:
            name=safe_name(item.filename)
            assert name not in seen and item.header_offset not in headers;seen.add(name);headers.add(item.header_offset)
            assert not item.is_dir()and not item.flag_bits&1 and item.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
            mode=item.external_attr>>16;assert stat.S_IFMT(mode)in(0,stat.S_IFREG)
            assert item.header_offset>=0 and item.header_offset+30<cd_offset and item.file_size>=0
            digest=hashlib.sha256();total=0
            with archive.open(item)as source:
                while data:=source.read(4*1024**2):digest.update(data);total+=len(data)
            assert total==item.file_size
            inventory[name]=dict(bytes=total,sha256=digest.hexdigest(),crc32=item.CRC)
        assert min(headers)==0
    return inventory
def read_member(archive,name,limit):
    info=archive.getinfo(name);assert 0<=info.file_size<=limit
    return archive.read(info)
def scan_tar(manifest,directory,expected):
    proof=verify_parts(manifest,directory)
    prefix=manifest['source_directory'];safe_name(prefix);assert '/'not in prefix
    wanted=dict(expected);seen=set();found={}
    with JoinedParts([directory/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as archive:
            for item in archive:
                name=item.name[:-1]if item.isdir()and item.name.endswith('/')else item.name
                safe_name(name);assert name==prefix or name.startswith(prefix+'/')
                assert name not in seen and(item.isfile()or item.isdir());seen.add(name)
                relative=name[len(prefix)+1:]if name!=prefix else ''
                if item.isdir():
                    assert relative==''or any(n.startswith(relative+'/')for n in wanted)
                    continue
                assert relative in wanted
                digest=hashlib.sha256();total=0
                with archive.extractfile(item)as stream:
                    while data:=stream.read(4*1024**2):digest.update(data);total+=len(data)
                assert total==item.size and digest.hexdigest()==wanted[relative]
                found[relative]=dict(bytes=total,sha256=digest.hexdigest())
    assert set(found)==set(wanted)
    return dict(archive=proof,regular_files=len(found),all_member_hashes_verified=True,files=found)
def recover_files(stage,path,work):
    pin=PIN[stage];n=names(stage);summary_bytes=evidence(stage,'-summary.json').read_bytes()
    report=exact_summary(stage,summary_bytes)
    file_identity(path,pin['zip_bytes'],pin['zip_sha256'])
    inventory=zip_inventory(path,pin['members'])
    transport=work/'publication';transport.mkdir()
    prefix=n['transport']+'/'
    with zipfile.ZipFile(path)as archive:
        raw_manifest=read_member(archive,prefix+n['stem']+'.parts.json',65536)
        manifest=json.loads(raw_manifest)
        assert manifest['format']=='ordered-tar-gzip-parts-v1'and manifest['stem']==n['stem']
        assert manifest['source_directory']==n['bundle']and manifest['part_limit_bytes']==512*1024**2
        assert len(manifest['parts'])==1 and manifest['parts'][0]['index']==0
        assert manifest['parts'][0]['name']==n['stem']+'.tar.gz.part0000'
        assert 0<manifest['bytes']<=512*1024**2
        assert manifest['parts'][0]['bytes']==manifest['bytes']and manifest['parts'][0]['sha256']==manifest['sha256']
        expected={}
        for name,row in report['source_capsule_copy'].items():
            if not hidden(name):expected['cloud-cdr-v59-font-recovery/'+name]=row['sha256']
        for name,row in report['stage_copy'].items():expected[n['stage']+'/'+name]=row['sha256']
        for name,digest in report['outputs'].items():
            if not hidden(name):expected[n['bundle']+'/'+name]=digest
        expected[n['bundle']+'/result.json']=pin['summary_sha256']
        summary_name=prefix+n['stem']+'.summary.json';manifest_name=prefix+n['stem']+'.parts.json'
        assert read_member(archive,summary_name,1024**2)==summary_bytes
        expected[summary_name]=pin['summary_sha256'];expected[manifest_name]=hashlib.sha256(raw_manifest).hexdigest()
        publication_name=prefix+'publication.json';publication_bytes=read_member(archive,publication_name,65536)
        publication=json.loads(publication_bytes)
        assert publication==dict(status='FAIL_PUBLICATION',summary_sha256=pin['summary_sha256'],assets=[],
          archive=dict(parts=1,bytes=manifest['bytes'],sha256=manifest['sha256'],all_parts_and_combined_bytes_verified=True),error=ERROR)
        expected[publication_name]=hashlib.sha256(publication_bytes).hexdigest()
        for row in manifest['parts']:expected[prefix+row['name']]=row['sha256']
        assert set(inventory)==set(expected)and len(expected)==pin['members']
        for name,digest in expected.items():assert inventory[name]['sha256']==digest,name
        # Select only already-created publication payloads and the full stage JSON.
        # Every other outer ZIP member was streamed/CRC/SHA checked above.
        for filename in [n['stem']+'.summary.json',n['stem']+'.parts.json',*[r['name']for r in manifest['parts']]]:
            with archive.open(prefix+filename)as inp,(transport/filename).open('xb')as out:shutil.copyfileobj(inp,out,4*1024**2)
            assert sha(transport/filename)==expected[prefix+filename]
        stage_bytes=read_member(archive,n['stage']+'/result.json',16*1024**2)
        assert hashlib.sha256(stage_bytes).hexdigest()==pin['stage_sha256']
        assert stage_bytes==read_member(archive,n['bundle']+'/stage/result.json',16*1024**2)
        stage_report=json.loads(stage_bytes)
        assert stage_report['source_head']==HEAD and stage_report['status']==wrapper.PASS[stage]
        assert stage_report['sources_unchanged']is True and stage_report['saved_capsule_integrity']==dict(files=706,all_hashes_unchanged=True)
        assert all(stage_report[k]is False for k in ['qualified_pex','full_phy_accepted','closed_loop'])
        (transport/(n['stem']+'.stage-result.json')).write_bytes(stage_bytes)
        (work/'original-publication-failure.json').write_bytes(publication_bytes)
    full_expected={**report['outputs'],'result.json':pin['summary_sha256']}
    tar_proof=scan_tar(manifest,transport,full_expected)
    assert tar_proof['regular_files']==pin['bundle_files']
    for prefix,key in [('source-capsule','source_capsule_copy'),('stage','stage_copy')]:
        for name,row in report[key].items():assert tar_proof['files'][prefix+'/'+name]==row
    assert tar_proof['files']['result.json']['bytes']==pin['summary_bytes']
    files=wrapper.publication_files(transport,transport/(n['stem']+'.summary.json'),transport/(n['stem']+'.parts.json'),manifest)
    full=transport/(n['stem']+'.stage-result.json');assert sha(full)==pin['stage_sha256']and full.stat().st_size>0;files.append(full)
    return files,dict(zip=dict(artifact=pin['artifact'],bytes=pin['zip_bytes'],sha256=pin['zip_sha256'],members=pin['members'],all_crc_and_hashes_verified=True),
      full_bundle=tar_proof,outer_omitted_hidden_files=[p+'/'+v for p in ['cloud-cdr-v59-font-recovery',n['bundle']+'/source-capsule']for v in(HIDDEN_RC if stage=='rc'else[])],
      hidden_bytes_preserved_in_complete_inner_archive=True,stage_sha256=pin['stage_sha256'],summary_sha256=pin['summary_sha256'],
      native_stage_status=stage_report['status'],native_stage_rerun=False,original_actions_failure_retained=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--stage',choices=PIN);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    m=methods()
    if a.controls:
        assert a.stage is None
        from check_cdr_v59_publication_recovery import controls
        print(json.dumps(controls(),indent=2));return
    assert a.stage in PIN and m['recovery_authorized']is True
    stage=a.stage;pin=PIN[stage];n=names(stage)
    out=ROOT/'hw/soc/out'/('cloud-cdr-v59-'+stage+'-publication-recovery');out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,stage=stage,
      original_run=RUN,original_head=HEAD,original_attempt=1,original_job_conclusion='failure',
      native_rerun=False,geometry_regenerated=False,extraction_repeated=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,
      future_mim_qualified=False,original_publication_failure_retained=True)
    write(out/'result.json',result)
    try:
        result['original_release']=original_release(stage)
        run=release.api('actions/runs/'+str(RUN));jobs=release.api('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100')
        artifact=release.api('actions/artifacts/'+str(pin['artifact']));validate_metadata(stage,run,jobs,artifact)
        log=out/'original-job.log';download_raw('actions/jobs/'+str(pin['job'])+'/logs',log,pin['log_bytes'],pin['log_sha256'])
        result['log_proof']=exact_log(stage,log.read_bytes());write(out/'result.json',result)
        archive=out/'original-artifact.zip'
        download_raw('actions/artifacts/'+str(pin['artifact'])+'/zip',archive,pin['zip_bytes'],pin['zip_sha256'])
        files,proof=recover_files(stage,archive,out);result['recovery']=proof
        result['assets']=[];write(out/'result.json',result)
        old=publisher.release;publisher.release=original_lookup(stage)
        try:
            for path in files:
                before=sha(path);size=path.stat().st_size;assert size>0
                result['assets'].append(publisher.publish(path,n['tag']))
                assert sha(path)==before and path.stat().st_size==size
                write(out/'result.json',result)
        finally:publisher.release=old
        methods()
        result['status']='PASS_EXISTING_NATIVE_STAGE_EVIDENCE_RECOVERED_ORIGINAL_JOB_FAILURE_RETAINED'
    except BaseException as error:
        result.update(status='FAIL_PUBLICATION_RECOVERY',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(v.relative_to(out)):dict(bytes=v.stat().st_size,sha256=sha(v))for v in out.rglob('*')if v.is_file()and v!=out/'result.json'}
        write(out/'result.json',result)
        wrapper.emit(out/'result.json','CDR_V59_PUBLICATION_RECOVERY_RESULT')
if __name__=='__main__':main()
