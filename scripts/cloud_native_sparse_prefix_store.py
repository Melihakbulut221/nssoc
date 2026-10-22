#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lossless sparse-prefix storage primitive; NOT qualified for native activation.

The authoritative prior raw bytes remain immutable outside the sparse working
file. A stopped-process logical reader must reconstruct and verify those bytes.
This module alone does not restore CRIU or provide an accepted waveform reader.
"""
import copy,errno,hashlib,json,os,re
from pathlib import Path
FORMAT='native-raw-sparse-prefix-v1'
BLOCK=128*1024
CHUNK=1024*1024
MARKER=b'Binary:\n'

def source_contract(source):
    assert set(source)=={'bytes','sha256','header_bytes','payload_bytes','payload_sha256'}
    assert all(type(source[k])is int and source[k]>0 for k in ('bytes','header_bytes','payload_bytes'))
    assert source['bytes']==source['header_bytes']+source['payload_bytes']
    assert all(isinstance(source[k],str)and re.fullmatch('[0-9a-f]{64}',source[k])for k in ('sha256','payload_sha256'))
    assert source['header_bytes']<=4*1024*1024

def plan_for(source,head_keep=1024*1024,tail_keep=4*1024*1024):
    source_contract(source)
    assert type(head_keep)is int and type(tail_keep)is int
    assert head_keep>=source['header_bytes']and head_keep>=BLOCK and tail_keep>=BLOCK
    first=((head_keep+BLOCK-1)//BLOCK)*BLOCK
    last=((source['bytes']-tail_keep)//BLOCK)*BLOCK
    assert last-first>=2*BLOCK,'No meaningful sparse prefix interval'
    return dict(format=FORMAT,source=copy.deepcopy(source),block_bytes=BLOCK,
        head_keep_bytes=head_keep,tail_keep_bytes=tail_keep,
        hole_start=first,hole_stop=last)

def validate_plan(plan,expected):
    source_contract(expected)
    assert plan==plan_for(expected,plan['head_keep_bytes'],plan['tail_keep_bytes'])
    return True

def identity(path):
    st=Path(path).stat()
    return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)

def unchanged_hole(path,plan,expected):
    validate_plan(plan,expected)
    path=Path(path);assert path.is_file()and not path.is_symlink()
    assert path.stat().st_size>=expected['bytes'],'Truncated live raw file'
    with path.open('rb')as f:
        try:found=os.lseek(f.fileno(),plan['hole_start'],os.SEEK_DATA)
        except OSError as e:
            assert e.errno==errno.ENXIO,(e.errno,str(e));found=path.stat().st_size
        assert found>=plan['hole_stop'],'Native write into archived-only prefix; reconstruction is forbidden'
        f.seek(0);header=f.read(expected['header_bytes'])
        assert header.endswith(MARKER)and header.count(MARKER)==1,'Changed raw header boundary'
    return True

def checked_source(chunks,expected):
    source_contract(expected);total=0;whole=hashlib.sha256();payload=hashlib.sha256();header=bytearray()
    for data in chunks:
        assert isinstance(data,bytes)and data,'Invalid source byte chunk'
        assert total+len(data)<=expected['bytes'],'Long or duplicated source'
        if len(header)<expected['header_bytes']:
            header.extend(data[:expected['header_bytes']-len(header)])
        whole.update(data)
        start=max(0,expected['header_bytes']-total)
        payload.update(data[start:])
        yield total,data
        total+=len(data)
    assert total==expected['bytes'],'Truncated immutable source'
    assert whole.hexdigest()==expected['sha256'],'Immutable raw SHA256 mismatch'
    assert payload.hexdigest()==expected['payload_sha256'],'Immutable payload SHA256 mismatch'
    assert len(header)==expected['header_bytes']and header.endswith(MARKER)and header.count(MARKER)==1

def materialize(path,chunks,expected,head_keep=1024*1024,tail_keep=4*1024*1024):
    """Create only a new owned sparse file. Never modify the immutable source."""
    path=Path(path);plan=plan_for(expected,head_keep,tail_keep)
    with path.open('xb')as f:
        f.truncate(expected['bytes'])
        for offset,data in checked_source(chunks,expected):
            end=offset+len(data)
            if offset<plan['hole_start']:
                n=min(len(data),plan['hole_start']-offset)
                f.seek(offset);f.write(data[:n])
            if end>plan['hole_stop']:
                start=max(offset,plan['hole_stop'])
                f.seek(start);f.write(data[start-offset:])
        f.flush();os.fsync(f.fileno())
    unchanged_hole(path,plan,expected)
    return plan

def logical_chunks(path,source_chunks,plan,expected):
    """Only consume while native process is stopped; detect concurrent mutation."""
    validate_plan(plan,expected);path=Path(path)
    before=identity(path);unchanged_hole(path,plan,expected)
    with path.open('rb')as f:
        left=plan['hole_start']
        while left:
            data=f.read(min(CHUNK,left));assert data
            yield data;left-=len(data)
        # Consume and validate the ENTIRE immutable source, including retained
        # head/tail. No partial archive read is evidence of full source identity.
        for offset,data in checked_source(source_chunks,expected):
            a=max(offset,plan['hole_start']);b=min(offset+len(data),plan['hole_stop'])
            if a<b:yield data[a-offset:b-offset]
        f.seek(plan['hole_stop'])
        while data:=f.read(CHUNK):yield data
    assert identity(path)==before,'Native file changed during stopped-process verification'
    unchanged_hole(path,plan,expected)

def inspect_logical(path,source_chunks,plan,expected):
    """Verify old payload and hash every current byte without allocating the full file."""
    total=0;whole=hashlib.sha256();payload=hashlib.sha256();old_payload=hashlib.sha256()
    for data in logical_chunks(path,source_chunks,plan,expected):
        whole.update(data)
        a=max(total,expected['header_bytes']);b=total+len(data)
        if a<b:payload.update(data[a-total:b-total])
        b=min(b,expected['bytes'])
        if a<b:old_payload.update(data[a-total:b-total])
        total+=len(data)
    assert total==Path(path).stat().st_size
    assert old_payload.hexdigest()==expected['payload_sha256'],'Original native payload was altered'
    return dict(bytes=total,sha256=whole.hexdigest(),header_bytes=expected['header_bytes'],
        payload_bytes=total-expected['header_bytes'],payload_sha256=payload.hexdigest(),
        original_payload_preserved=True,physical_allocated_bytes=Path(path).stat().st_blocks*512,
        native_activation_qualified=False,waveform_reader_qualified=False)

def controls(root):
    """Owned cloud fixture only; not an electrical simulation or native restart."""
    root=Path(root);root.mkdir(exist_ok=False)
    header=b'Title: storage fixture only\nNo. Points: 0000000000\nBinary:\n'
    payload=os.urandom(16*1024*1024+123)
    original=header+payload
    source=dict(bytes=len(original),sha256=hashlib.sha256(original).hexdigest(),
        header_bytes=len(header),payload_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest())
    immutable=root/'immutable-original.raw';immutable.write_bytes(original)
    def chunks(data=original,n=131071):
        for offset in range(0,len(data),n):yield data[offset:offset+n]
    live=root/'live.raw';plan=materialize(live,chunks(),source)
    proof=inspect_logical(live,chunks(),plan,source)
    assert proof['sha256']==source['sha256']
    assert b''.join(logical_chunks(live,chunks(),plan,source))==original
    assert proof['physical_allocated_bytes']<source['bytes']//2
    append=os.urandom(2*1024*1024+77)
    patched=header.replace(b'0000000000',b'0000000123')
    with live.open('r+b')as f:
        f.seek(0);f.write(patched);f.seek(0,os.SEEK_END);f.write(append)
    expected=patched+payload+append
    proof_after=inspect_logical(live,chunks(),plan,source)
    assert proof_after['sha256']==hashlib.sha256(expected).hexdigest()
    assert proof_after['payload_sha256']==hashlib.sha256(payload+append).hexdigest()
    assert b''.join(logical_chunks(live,chunks(),plan,source))==expected
    rejected=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,FileExistsError):rejected.append(name)
        else:raise AssertionError('Accepted storage corruption: '+name)
    for name,key,value in [('wrong-format','format','other'),('changed-source-digest','source',dict(source,sha256='0'*64)),
            ('moved-hole-start','hole_start',plan['hole_start']+BLOCK),
            ('moved-hole-stop','hole_stop',plan['hole_stop']-BLOCK),
            ('changed-block-size','block_bytes',4096)]:
        bad=copy.deepcopy(plan);bad[key]=value
        reject(name,lambda bad=bad:validate_plan(bad,source))
    reject('overwrite-existing',lambda:materialize(live,chunks(),source))
    reject('truncated-source',lambda:materialize(root/'truncated.raw',chunks(original[:-1]),source))
    corrupt=original[:len(header)]+bytes([original[len(header)]^1])+original[len(header)+1:]
    reject('corrupted-source',lambda:materialize(root/'corrupted.raw',chunks(corrupt),source))
    reject('duplicated-source',lambda:materialize(root/'duplicated.raw',chunks(original+original[:1]),source))
    reject('corrupted-restore-source',lambda:inspect_logical(live,chunks(corrupt),plan,source))
    for name,offset in [('changed-retained-head',len(header)+3),('changed-retained-tail',source['bytes']-3),('write-inside-hole',plan['hole_start']+BLOCK)]:
        target=root/(name+'.raw');p=materialize(target,chunks(),source)
        with target.open('r+b')as f:
            f.seek(offset);old=f.read(1);f.seek(offset);f.write(bytes([old[0]^1]))
        reject(name,lambda:inspect_logical(target,chunks(),p,source))
    target=root/'truncated-live.raw';p=materialize(target,chunks(),source)
    with target.open('r+b')as f:f.truncate(source['bytes']-1)
    reject('truncated-live',lambda:inspect_logical(target,chunks(),p,source))
    target=root/'bad-marker.raw';p=materialize(target,chunks(),source)
    with target.open('r+b')as f:f.seek(len(header)-len(MARKER));f.write(b'Broken:\n')
    reject('changed-header-boundary',lambda:inspect_logical(target,chunks(),p,source))
    # Mutate during logical reading: neither even unchanged-size append/read
    # races nor a source that finishes late may silently pass verification.
    target=root/'concurrent-write.raw';p=materialize(target,chunks(),source)
    def racing():
        for i,data in enumerate(chunks()):
            if i==3:
                with target.open('ab')as f:f.write(b'race')
            yield data
    reject('concurrent-live-mutation',lambda:inspect_logical(target,racing(),p,source))
    assert len(rejected)==16
    assert hashlib.sha256(immutable.read_bytes()).hexdigest()==source['sha256']
    return dict(status='PASS_LOSSLESS_SPARSE_PREFIX_FIXTURE_AND16_CORRUPTIONS_NOT_NATIVE_QUALIFICATION',
        before=proof,after=proof_after,plan=plan,negative_controls=rejected,
        immutable_source_unchanged=True,complete_logical_bytes_equal_oracle=True,
        header_backpatch_and_partial_tail_retained=True,
        native_process_resumed=False,native_activation_qualified=False,
        waveform_reader_qualified=False,full_capture_accepted=False,full_phy_accepted=False)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    root=Path(__file__).resolve().parents[1]
    base=Path(os.environ.get('SPARSE_PROOF_BASE',str(root))).resolve()
    assert base==root or base.is_relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
    assert base.is_dir()
    out=base/'cloud-native-sparse-prefix-controls';out.mkdir(exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
    try:report.update(controls(out/'fixtures'))
    except BaseException as e:report.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        report['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report['filesystem']=__import__('subprocess').check_output(['findmnt','--json','-T',str(out)],text=True)
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
