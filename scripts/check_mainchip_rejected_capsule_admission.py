#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted admission controls only: tiny ZIP fixtures, never actual router restore."""
import ast, copy, hashlib, io, json, os, re, stat, tempfile, traceback, zipfile
from pathlib import Path
import mainchip_rejected_capsule_admission as a
def controls(pin):
    a.hosted();a.methods();raw=a.validate_pin(pin);rejected=[]
    def bad(name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,FileExistsError,zipfile.BadZipFile,EOFError):rejected.append(name)
        else:raise AssertionError('Accepted admission fault '+name)
    # Exercise each exact API identity independently on actual completed metadata.
    def identity(m):a.identities(m['run'],m['job'],m['publication_run'],m['publication_jobs'],m['release'],m['tag'])
    identity(pin['metadata'])
    for name,which,key,value in [
        ('original-live','run','status','in_progress'),('other-failure','run','id',1),
        ('original-accepted','run','conclusion','success'),('original-head','run','head_sha','0'*40),
        ('original-attempt','run','run_attempt',2),('original-job','job','id',1),
        ('publication-live','publication_run','status','in_progress'),
        ('publication-failed','publication_run','conclusion','failure'),
        ('publication-head','publication_run','head_sha','0'*40),
        ('release-target','release','target_commitish','0'*40),('release-draft','release','draft',True)]:
        m=copy.deepcopy(pin['metadata']);m[which][key]=value;bad(name,lambda:identity(m))
    m=copy.deepcopy(pin['metadata']);m['tag']['object']['sha']='0'*40;bad('tag-object',lambda:identity(m))
    m=copy.deepcopy(pin['metadata']);m['publication_jobs'][0]['conclusion']='failure';bad('publication-job-failure',lambda:identity(m))
    meta=next(v for v in pin['metadata']['release']['assets']if v['id']==a.ZIP_ID)
    for key,val in [('id',1),('name','other.zip'),('size',1),('digest','sha256:'+'0'*64)]:
        x=copy.deepcopy(meta);x[key]=val;bad('archive-meta-'+key,lambda:a.asset_valid(x,a.ZIP_ID))
    bad('actual-report-truncated',lambda:a.raw_valid(raw[str(a.REPORT_ID)][:-1],a.REPORT_ID))
    log=raw['672871178'];stripped=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',log)
    assert stripped!=log
    bad('actual-log-ansi-stripped',lambda:a.raw_valid(stripped,672871178))
    for key,val in [('status','SAVED'),('error',"AssertionError('other')"),('controller_sha256','0'*64),
                    ('checkpointed_elf_sha256','0'*64),('native_process_saved',False),
                    ('segment_elapsed_s',1),('previous_boot_id','0'*36),('checkpoint_images',{}),
                    ('native_log',{}),('restored_work_prefixes_verified',{}),('cpuset','0'),
                    ('route_script',{}),('runtime_source',{}),('global_source',{})]:
        r=copy.deepcopy(pin['report']);r[key]=val
        bad('actual-report-'+key,lambda:a.semantic_report(r,pin['inventory'],pin['parent']))
    for key in a.MISSING_HISTORICAL:
        r=copy.deepcopy(pin['report']);r[key]=False
        bad('invent-missing-'+key,lambda:a.semantic_report(r,pin['inventory'],pin['parent']))
    inv=copy.deepcopy(pin['inventory']);inv['checkpoints/state/core-2.img']=inv.pop('checkpoints/state/core-7.img')
    bad('wrong-image-topology',lambda:a.semantic_report(pin['report'],inv,pin['parent']))
    inv=copy.deepcopy(pin['inventory']);inv['checkpoints/state/pages-1.img']['sha256']='0'*64
    bad('changed-page-bytes',lambda:a.semantic_report(pin['report'],inv,pin['parent']))
    inv=copy.deepcopy(pin['inventory']);inv['work/native.log']['sha256']='0'*64
    bad('changed-work-prefix',lambda:a.semantic_report(pin['report'],inv,pin['parent']))
    pub=copy.deepcopy(pin['publication']);pub['continuation_accepted']=True
    bad('publication-acceptance-invented',lambda:a.publication_valid(pub))
    p=copy.deepcopy(pin);p['report']['status']='SAVED'
    bad('detached-report-object',lambda:a.validate_pin(p))
    names=sorted(n for n in pin['inventory']if n.startswith(('work/','checkpoints/')))
    assert len(a.selected_names(pin,names))==37
    bad('missing-selected-image',lambda:a.selected_names(pin,names[:-1]))
    bad('duplicate-selected-image',lambda:a.selected_names(pin,names[:-1]+names[:1]))
    bad('extra-selected-file',lambda:a.selected_names(pin,names+['criu-build.log']))
    # Run original unchanged normal-admission controls; actual rejected run must
    # remain rejected there even though this separate diagnostic can recover bytes.
    source=(a.ROOT/a.CONTROLLER).read_text()
    assert a.digest(source.encode())==a.CONTROLLER_SHA
    nodes=[]
    for n in ast.parse(source).body:
        if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='GLOBAL_INPUTS'for t in n.targets):nodes.append(n)
        if isinstance(n,ast.FunctionDef)and n.name in('validate_saved_source','source_controls'):nodes.append(n)
    assert len(nodes)==3
    ns=dict(re=re);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<original-pure-admission>','exec'),ns)
    original=ns['source_controls']();assert len(original['faults'])==20
    spec=dict(run=a.RUN,attempt=1,group='mainchip-route12-drt-cross',source_head=a.HEAD,
        controller_sha256=a.CONTROLLER_SHA,summary_sha256=a.ASSETS[str(a.REPORT_ID)]['sha256'],parts_sha256='0'*64)
    bad('original-validator-still-rejects-actual-failure',lambda:ns['validate_saved_source'](
        spec,pin['metadata']['run'],pin['report'],spec['summary_sha256'],spec['parts_sha256'],{a.CONTROLLER_SHA}))
    with tempfile.TemporaryDirectory(prefix='rejected-capsule-controls-')as td:
        root=Path(td);payload=b'opaque\x00bytes\xff\x1b[31m'
        a.consume(io.BytesIO(payload),root/'good',len(payload),a.digest(payload))
        for name,b in [('truncated',payload[:-1]),('overlong',payload+b'x'),('changed',b'X'+payload[1:])]:
            bad('stream-'+name,lambda:a.consume(io.BytesIO(b),root/name,len(payload),a.digest(payload)))
        entries=[('result.json',b'{}',stat.S_IFREG),('work/native.log',b'original-native',stat.S_IFREG),
                 ('checkpoints/state/pages-1.img',b'opaque-image',stat.S_IFREG),('empty.log',b'',stat.S_IFREG)]
        def archive(items):
            f=io.BytesIO()
            with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED)as z:
                for name,body,kind in items:
                    i=zipfile.ZipInfo(name);i.create_system=3;i.external_attr=(kind|0o600)<<16;z.writestr(i,body)
            return f.getvalue()
        good=archive(entries)
        with zipfile.ZipFile(io.BytesIO(good))as z:
            expected={i.filename:dict(bytes=i.file_size,compressed_bytes=i.compress_size,crc32=i.CRC,
                sha256=a.digest(z.read(i)))for i in z.infolist()}
        def scan(blob,exp=expected,target=None):
            target=target or root/('scan-'+str(len(rejected)))
            with zipfile.ZipFile(io.BytesIO(blob))as z:return a.scan_extract(z,exp,['work/native.log','checkpoints/state/pages-1.img'],target)
        actual=scan(good,target=root/'positive')
        assert len(actual)==4 and not(root/'positive/empty.log').exists()
        assert (root/'positive/work/native.log').read_bytes()==b'original-native'
        for name,path,kind in [('absolute','/escape',stat.S_IFREG),('traversal','../escape',stat.S_IFREG),
                ('alias','./result.json',stat.S_IFREG),('backslash','work\\escape',stat.S_IFREG),
                ('drive','C:/escape',stat.S_IFREG),('symlink','result.json',stat.S_IFLNK),
                ('special','result.json',stat.S_IFIFO),('file-parent','work',stat.S_IFREG)]:
            blob=archive([(path,b'{}',kind)]+entries[1:]);bad('zip-'+name,lambda:scan(blob))
        bad('zip-missing',lambda:scan(archive(entries[:-1])))
        bad('zip-extra',lambda:scan(archive(entries+[('extra',b'x',stat.S_IFREG)])))
        bad('zip-duplicate',lambda:scan(archive([entries[0]]+entries)))
        corrupt=good.replace(b'original-native',b'Xriginal-native',1);assert corrupt!=good
        bad('zip-crc',lambda:scan(corrupt))
        exp=copy.deepcopy(expected);exp['work/native.log']['sha256']='0'*64
        bad('zip-member-sha',lambda:scan(good,exp))
        exp=copy.deepcopy(expected);exp['work/native.log']['bytes']+=1
        bad('zip-member-size',lambda:scan(good,exp))
        bad('zip-existing-destination',lambda:scan(good,target=root/'positive'))
        f=root/'input';f.write_bytes(b'authenticated-input');h=a.file_sha(f)
        row={'input':dict(path=str(f),expected_sha256=h,actual_sha256=h)}
        before=a.validate_current_rows(row,'before_restore',required={})
        a.validate_current_rows(row,'after_restore',before,required={})
        q=copy.deepcopy(row);q['input']['actual_sha256']='0'*64
        bad('current-claimed-hash',lambda:a.validate_current_rows(q,'before_restore',required={}))
        q=copy.deepcopy(row);q['other']=copy.deepcopy(q['input'])
        bad('current-duplicate-path',lambda:a.validate_current_rows(q,'before_restore',required={}))
        q=copy.deepcopy(row);q['input']['path']='relative'
        bad('current-relative-path',lambda:a.validate_current_rows(q,'before_restore',required={}))
        bad('current-required-missing',lambda:a.validate_current_rows(row,'before_restore',required={'missing':h}))
        q=copy.deepcopy(row);q['renamed']=q.pop('input')
        bad('current-before-after-inventory',lambda:a.validate_current_rows(q,'after_restore',before,required={}))
        f.write_bytes(b'changed');bad('current-real-file-mutated',lambda:a.validate_current_rows(row,'after_restore',before,required={}))
        link=root/'link';link.symlink_to(f);q=copy.deepcopy(row);q['input']['path']=str(link)
        bad('current-symlink',lambda:a.validate_current_rows(q,'before_restore',required={}))
    assert len(set(rejected))==len(rejected)
    assert len(rejected)==71,len(rejected)
    return dict(status='PASS_REJECTED_CAPSULE_ADMISSION_CONTROLS_ONLY',faults=rejected,
        original20_controls=original,actual_receipt_bound=True,tiny_fixture_stream_and_crc_verified=True,
        original_failed_source_still_rejected=True,actual65_archive_restored=False,
        native_process_restored=False,saved_process_validated=False,normal_continuation_allowed=False)
def main():
    out=dict(status='RUNNING',native_process_restored=False,normal_continuation_allowed=False)
    try:
        out.update(controls(a.rejected_receipt()))
    except BaseException as e:
        out.update(status='FAIL_ADMISSION_CONTROLS',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        print(json.dumps(out,sort_keys=True),flush=True)
if __name__=='__main__':main()
