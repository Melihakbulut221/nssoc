#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted exact metadata/log and real ZIP/tar/publication-file controls; no CAD."""
import copy,hashlib,io,json,os,stat,struct,tarfile,tempfile,zipfile
from pathlib import Path
import cloud_cdr_v59_publication_recovery as core
import cloud_cdr_v59_binding_rc as wrapper
def controls():
    methods=core.methods();receipt=json.loads((core.ROOT/core.RECEIPT).read_text());rejected=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,TypeError,ValueError,FileNotFoundError,zipfile.BadZipFile,tarfile.TarError,EOFError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    run=dict(id=core.RUN,run_attempt=1,head_sha=core.HEAD,path=core.WORKFLOW,event='workflow_dispatch',status='completed',conclusion='failure')
    jobs=dict(total_count=3,jobs=[dict(id=121168387181,run_id=core.RUN,head_sha=core.HEAD,name='controls',status='completed',conclusion='success')]+[
      dict(id=core.PIN[stage]['job'],run_id=core.RUN,head_sha=core.HEAD,name='native ('+stage+')',status='completed',conclusion='failure',
        steps=receipt['stages'][stage]['steps'])for stage in ['binding','rc']])
    artifact=copy.deepcopy(receipt['stages']['binding']['artifact'])
    for stage in ['binding','rc']:
        assert core.validate_metadata(stage,run,jobs,receipt['stages'][stage]['artifact'])
        core.exact_summary(stage,core.evidence(stage,'-summary.json').read_bytes())
        core.exact_log(stage,core.evidence(stage,'.log').read_bytes())
    for field,value in [('id',1),('run_attempt',2),('head_sha','0'*40),('path','other.yml'),('event','push'),('status','in_progress'),('conclusion','success')]:
        bad=copy.deepcopy(run);bad[field]=value;reject('run_'+field,lambda:core.validate_metadata('binding',bad,jobs,artifact))
    for field,value in [('id',1),('run_id',1),('head_sha','0'*40),('status','in_progress'),('conclusion','success')]:
        bad=copy.deepcopy(jobs);bad['jobs'][1][field]=value;reject('job_'+field,lambda:core.validate_metadata('binding',run,bad,artifact))
    for field,value in [('id',1),('name','other'),('size_in_bytes',1),('digest','sha256:'+'0'*64),('expired',True)]:
        bad=copy.deepcopy(artifact);bad[field]=value;reject('artifact_'+field,lambda:core.validate_metadata('binding',run,jobs,bad))
    bad=copy.deepcopy(artifact);bad['workflow_run']['head_sha']='0'*40
    reject('artifact_source',lambda:core.validate_metadata('binding',run,jobs,bad))
    summary=core.evidence('binding','-summary.json').read_bytes();log=core.evidence('binding','.log').read_bytes()
    reject('summary_truncated',lambda:core.exact_summary('binding',summary[:-1]))
    reject('summary_changed',lambda:core.exact_summary('binding',bytes([summary[0]^1])+summary[1:]))
    reject('log_truncated',lambda:core.exact_log('binding',log[:-1]))
    reject('log_changed',lambda:core.exact_log('binding',bytes([log[0]^1])+log[1:]))
    endpoint='actions/jobs/'+str(core.PIN['binding']['job'])+'/logs'
    command=['gh','api','--allow-escape-sequences','repos/'+core.release.REPO+'/'+endpoint]
    assert core.validate_raw_command(endpoint,command)
    reject('raw_transport_strips_escapes',lambda:core.validate_raw_command(endpoint,[command[0],command[1],command[3]]))
    reject('raw_transport_wrong_endpoint',lambda:core.validate_raw_command('actions/jobs/1/logs',command))
    metadata_count=len(rejected);assert metadata_count==24
    with tempfile.TemporaryDirectory()as folder:
        base=Path(folder)
        def make_zip(label,entries):
            path=base/(label+'.zip')
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED)as archive:
                for item,data in entries:archive.writestr(item,data)
            return path
        good=[('a.txt',b'original'),('empty.log',b'')]
        path=make_zip('good',good)
        inventory=core.zip_inventory(path,2)
        assert inventory['a.txt']['sha256']==hashlib.sha256(b'original').hexdigest()and inventory['empty.log']['bytes']==0
        digest=core.sha(path);size=path.stat().st_size;assert core.file_identity(path,size,digest)
        reject('zip_size_mismatch',lambda:core.file_identity(path,size-1,digest))
        reject('zip_digest_mismatch',lambda:core.file_identity(path,size,'0'*64))
        reject('zip_member_count',lambda:core.zip_inventory(path,1))
        for label,name in [('zip_traversal','../escape'),('zip_absolute','/escape'),('zip_backslash','a'+chr(92)+'b'),('zip_alias','a//b'),('zip_dot','a/./b')]:
            bad=make_zip(label,[(name,b'x')]);reject(label,lambda:core.zip_inventory(bad,1))
        bad=make_zip('zip_duplicate',[('a',b'a'),('a',b'b')]);reject('zip_duplicate',lambda:core.zip_inventory(bad,2))
        item=zipfile.ZipInfo('link');item.create_system=3;item.external_attr=(stat.S_IFLNK|0o777)<<16
        bad=make_zip('zip_symlink',[(item,b'target')]);reject('zip_symlink',lambda:core.zip_inventory(bad,1))
        bad=make_zip('zip_directory',[('folder/',b'')]);reject('zip_directory',lambda:core.zip_inventory(bad,1))
        bad=make_zip('zip_trailing',good)
        with bad.open('ab')as out:out.write(b'junk')
        reject('zip_trailing',lambda:core.zip_inventory(bad,2))
        bad=make_zip('zip_crc',good)
        with bad.open('r+b')as out:
            header=out.read(30);name_size,extra_size=struct.unpack('<HH',header[26:30]);offset=30+name_size+extra_size
            out.seek(offset);value=out.read(1);out.seek(offset);out.write(bytes([value[0]^1]))
        reject('zip_crc',lambda:core.zip_inventory(bad,2))
        zip_count=len(rejected)-metadata_count;assert zip_count==13
        bundle=base/'bundle';bundle.mkdir();(bundle/'a').write_bytes(b'original');(bundle/'empty').write_bytes(b'')
        transport=base/'packed';transport.mkdir()
        packed=wrapper.pack(bundle,'roundtrip',transport,127)
        expected={'a':hashlib.sha256(b'original').hexdigest(),'empty':hashlib.sha256(b'').hexdigest()}
        proof=core.scan_tar(packed,transport,expected);assert proof['regular_files']==2 and len(packed['parts'])>1
        def tar_case(label,entries):
            dest=base/label;dest.mkdir();filename=label+'.tar.gz.part0000';path=dest/filename
            with tarfile.open(path,'w:gz')as archive:
                for name,data,kind in entries:
                    item=tarfile.TarInfo(name);item.type=kind;item.size=len(data)if kind==tarfile.REGTYPE else 0
                    if kind in(tarfile.SYMTYPE,tarfile.LNKTYPE):item.linkname='bundle/a'
                    archive.addfile(item,io.BytesIO(data)if kind==tarfile.REGTYPE else None)
            h=core.sha(path);size=path.stat().st_size
            m=dict(format='ordered-tar-gzip-parts-v1',stem=label,source_directory='bundle',bytes=size,sha256=h,
              parts=[dict(index=0,name=filename,bytes=size,sha256=h)])
            return m,dest
        originals=[('bundle/a',b'original',tarfile.REGTYPE),('bundle/empty',b'',tarfile.REGTYPE)]
        cases=[
          ('tar_missing',originals[:-1]),('tar_extra',originals+[('bundle/extra',b'x',tarfile.REGTYPE)]),
          ('tar_duplicate',originals+[originals[0]]),
          ('tar_changed',[('bundle/a',b'changed',tarfile.REGTYPE),originals[1]]),
          ('tar_symlink',originals+[('bundle/link',b'',tarfile.SYMTYPE)]),
          ('tar_hardlink',originals+[('bundle/link',b'',tarfile.LNKTYPE)]),
          ('tar_traversal',originals+[('bundle/../escape',b'x',tarfile.REGTYPE)]),
          ('tar_wrong_root',[('other/a',b'original',tarfile.REGTYPE),originals[1]])]
        for label,entries in cases:
            m,dest=tar_case(label,entries);reject(label,lambda:core.scan_tar(m,dest,expected))
        assert len(rejected)-metadata_count-zip_count==8
    assert len(rejected)==45 and len(set(rejected))==45
    publication=wrapper.publication_controls()
    assert len(publication['rejected'])==8 and publication['chunk_controls']['negative_controls']==6
    assert len(publication['file_list_controls']['rejected'])==14
    return dict(status='PASS_V59_ARTIFACT_PUBLICATION_RECOVERY_45_CONTROLS',rejected=rejected,
      metadata_and_log_controls=24,zip_controls=13,complete_tar_controls=8,publication=publication,
      actual_committed_full_summaries_and_logs_verified=True,actual_archive_downloaded=False,
      fixture_archive_roundtrip=True,protected_files=len(methods['protected']),native_executed=False,
      original_native_stages_rerun=False,recovery_authorized=methods['recovery_authorized'])
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    print(json.dumps(controls(),indent=2))
