#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lossless stopped-native prefix/delta capsules; transport qualification only.

Every original file except the logical raw is copied unchanged. Its current
head/tail extents are retained explicitly; the middle remains in an immutable,
hash-bound source archive. The ordinary complete raw is reconstructed only after
every source byte, extent byte and resulting logical byte passes its hash.
Nothing here authorizes native activation or electrical/full-PHY acceptance.
A consumer must exhaust capture_chunks() and inspect its proof before using data.
"""
import copy,hashlib,json,os,re,shutil,stat
from pathlib import Path,PurePosixPath
import cloud_native_sparse_prefix_store as sparse

FORMAT='native-lossless-prefix-delta-v1'
META='.native-prefix-delta'
CONTRACT= META+'/contract.json'
CHUNK=1024*1024
FIELDS=('bytes','sha256','header_bytes','payload_bytes','payload_sha256')

def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def relative(name):
    assert isinstance(name,str)and name and str(PurePosixPath(name))==name
    p=PurePosixPath(name)
    assert not p.is_absolute()and not any(x in ('.','..')for x in p.parts)
    return name

def descriptor(spec):
    assert set(spec)=={'run','attempt','stage','summary_sha256','parts_sha256'}
    assert str(spec['run']).isdigit()and int(spec['run'])>0
    assert str(spec['attempt']).isdigit()and int(spec['attempt'])>0
    assert spec['stage']in ('initial','recovery','sparse')
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ('summary_sha256','parts_sha256'))
    return True

def files(root):
    root=Path(root);assert root.is_dir()and not root.is_symlink()
    result={}
    for p in sorted(root.rglob('*')):
        st=p.lstat()
        assert stat.S_ISREG(st.st_mode)or stat.S_ISDIR(st.st_mode),'Unsupported capsule file type'
        if p.is_file():result[p.relative_to(root).as_posix()]=p
    return result

def directories(root):
    root=Path(root);result={'.':stat.S_IMODE(root.stat().st_mode)}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),'Symlinks require separate native qualification'
        if p.is_dir():result[p.relative_to(root).as_posix()]=stat.S_IMODE(p.stat().st_mode)
    return result

def snapshot(root,member):
    result={}
    for name,p in files(root).items():
        row=dict(bytes=p.stat().st_size,identity=list(sparse.identity(p)),
            mode=stat.S_IMODE(p.stat().st_mode))
        if name!=member:row['sha256']=sha(p)
        result[name]=row
    assert member in result
    return result

def validate(record):
    assert set(record)=={'format','member','source_descriptor','source','plan','logical',
        'extents','original_files','original_directories','transport_only','native_activation_qualified','full_capture_accepted'}
    assert record['format']==FORMAT
    member=relative(record['member']);assert not member.startswith(META+'/')
    descriptor(record['source_descriptor'])
    source=record['source'];logical=record['logical']
    sparse.source_contract(source);sparse.source_contract(logical)
    sparse.validate_plan(record['plan'],source)
    assert logical['bytes']>=source['bytes']
    assert logical['header_bytes']==source['header_bytes']
    assert record['transport_only']is True
    assert record['native_activation_qualified']is False and record['full_capture_accepted']is False
    start=record['plan']['hole_start'];stop=record['plan']['hole_stop']
    expected=[dict(name=META+'/head.bin',start=0,stop=start),
              dict(name=META+'/tail.bin',start=stop,stop=logical['bytes'])]
    assert isinstance(record['extents'],list)and len(record['extents'])==2
    for actual,wanted in zip(record['extents'],expected,strict=True):
        assert set(actual)=={'name','start','stop','bytes','sha256'}
        assert {k:actual[k]for k in wanted}==wanted,'Extent order, gap or overlap'
        assert type(actual['bytes'])is int and actual['bytes']==wanted['stop']-wanted['start']>0
        assert re.fullmatch('[0-9a-f]{64}',actual['sha256'])
    assert isinstance(record['original_files'],dict)and member in record['original_files']
    for name,row in record['original_files'].items():
        relative(name);assert not name.startswith(META+'/')
        assert set(row)=={'bytes','sha256','mode'}
        assert type(row['bytes'])is int and row['bytes']>=0
        assert type(row['mode'])is int and 0<=row['mode']<=0o7777
        assert re.fullmatch('[0-9a-f]{64}',row['sha256'])
    assert isinstance(record['original_directories'],dict)and '.'in record['original_directories']
    for name,mode in record['original_directories'].items():
        if name!='.':relative(name);assert not name.startswith(META+'/')and name!=META
        assert type(mode)is int and 0<=mode<=0o7777
    assert record['original_files'][member]['bytes']==logical['bytes']
    assert record['original_files'][member]['sha256']==logical['sha256']
    return True

def copy_extent(source,destination,start,stop):
    with source.open('rb')as src,destination.open('xb')as dst:
        src.seek(start);left=stop-start
        while left:
            data=src.read(min(CHUNK,left));assert data,'Truncated stopped native extent'
            dst.write(data);left-=len(data)
    assert destination.stat().st_size==stop-start
    return dict(name=destination.name,bytes=stop-start,sha256=sha(destination),start=start,stop=stop)

def write_capsule(native_root,capsule_root,member,source_descriptor,source,plan,logical,stopped):
    """Copy real stored extents; never read sparse holes as original waveform."""
    native_root=Path(native_root).resolve();capsule_root=Path(capsule_root).resolve()
    relative(member);descriptor(source_descriptor)
    sparse.source_contract(source);sparse.source_contract(logical);sparse.validate_plan(plan,source)
    assert callable(stopped)and stopped()is True,'Native process must be stopped'
    assert not capsule_root.exists()and not capsule_root.is_relative_to(native_root)
    assert not (native_root/META).exists()
    original=native_root/member
    sparse.unchanged_hole(original,plan,source)
    assert original.stat().st_size==logical['bytes']
    before=snapshot(native_root,member);dirs=directories(native_root);capsule_root.mkdir()
    for name,mode in dirs.items():
        target=capsule_root if name=='.'else capsule_root/name
        target.mkdir(parents=True,exist_ok=True)
    for name,p in files(native_root).items():
        if name==member:continue
        target=capsule_root/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
        assert sha(target)==before[name]['sha256']
    meta=capsule_root/META;meta.mkdir()
    ranges=[('head.bin',0,plan['hole_start']),('tail.bin',plan['hole_stop'],logical['bytes'])]
    extents=[]
    for name,start,stop in ranges:
        row=copy_extent(original,meta/name,start,stop);row['name']=META+'/'+name;extents.append(row)
    inventory={}
    for name,row in before.items():
        inventory[name]=dict(bytes=row['bytes'],mode=row['mode'],
            sha256=logical['sha256']if name==member else row['sha256'])
    record=dict(format=FORMAT,member=member,source_descriptor=copy.deepcopy(source_descriptor),
        source=copy.deepcopy(source),plan=copy.deepcopy(plan),logical=copy.deepcopy(logical),
        extents=extents,original_files=inventory,original_directories=dirs,transport_only=True,
        native_activation_qualified=False,full_capture_accepted=False)
    validate(record)
    (capsule_root/CONTRACT).write_text(json.dumps(record,indent=2)+'\n')
    for name,mode in sorted(dirs.items(),key=lambda pair:len(pair[0]),reverse=True):
        (capsule_root if name=='.'else capsule_root/name).chmod(mode)
    assert stopped()is True and snapshot(native_root,member)==before and directories(native_root)==dirs,'Native source changed while copying'
    sparse.unchanged_hole(original,plan,source)
    verify_capsule(capsule_root)
    return record

def verify_capsule(root,expected=None):
    root=Path(root);record=json.loads((root/CONTRACT).read_text());validate(record)
    if expected is not None:assert record==expected,'Delta contract identity mismatch'
    current=files(root)
    actual_dirs=directories(root);assert actual_dirs.pop(META,None)is not None
    assert actual_dirs==record['original_directories'],'Missing or changed native directory'
    wanted=(set(record['original_files'])-{record['member']})|{CONTRACT}|{x['name']for x in record['extents']}
    assert set(current)==wanted,'Missing or untracked capsule file'
    for name,row in record['original_files'].items():
        if name==record['member']:continue
        p=current[name]
        assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'Original auxiliary file changed'
        assert stat.S_IMODE(p.stat().st_mode)==row['mode'],'Original auxiliary mode changed'
    for row in record['extents']:
        p=current[row['name']]
        assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'Stored extent changed'
    return record

def restore_capsule_modes(root,expected):
    """Restore archive-normalized modes only after trusted inventory/content proof.

    The caller must first verify the entire archive and bind the contract hash
    to its owning summary. No mode is changed until every named file's size and
    hash, the complete directory set, and both raw extents have been checked.
    """
    root=Path(root);record=json.loads((root/CONTRACT).read_text());validate(record)
    assert record==expected,'Unbound restoration contract'
    current=files(root)
    wanted=(set(record['original_files'])-{record['member']})|{CONTRACT}|{x['name']for x in record['extents']}
    assert set(current)==wanted,'Missing or untracked restored file'
    actual_dirs=directories(root);assert actual_dirs.pop(META,None)is not None
    assert set(actual_dirs)==set(record['original_directories']),'Missing or untracked restored directory'
    for name,row in record['original_files'].items():
        if name==record['member']:continue
        p=current[name]
        assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'Restored auxiliary content changed'
    for row in record['extents']:
        p=current[row['name']]
        assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'Restored raw extent changed'
    changed_files=[];changed_dirs=[]
    for name,row in record['original_files'].items():
        if name==record['member']:continue
        p=current[name]
        if stat.S_IMODE(p.stat().st_mode)!=row['mode']:
            p.chmod(row['mode']);changed_files.append(name)
    for name,mode in sorted(record['original_directories'].items(),key=lambda pair:len(pair[0]),reverse=True):
        p=root if name=='.'else root/name
        if stat.S_IMODE(p.stat().st_mode)!=mode:
            p.chmod(mode);changed_dirs.append(name)
    verify_capsule(root,record)
    return dict(all_contents_verified_before_mode_changes=True,
        restored_file_modes=changed_files,restored_directory_modes=changed_dirs,
        exact_native_modes_restored=True,full_capture_accepted=False)

def file_chunks(path):
    with Path(path).open('rb')as stream:
        while data:=stream.read(CHUNK):yield data

def capture_chunks(root,source_chunks,proof,expected_descriptor=None):
    """Exhaustion verifies complete source, full payload and all resulting bytes.

    Yielded bytes are provisional until proof['complete'] is true. No consumer
    may accept an early stopped iterator, including one that ended at a row edge.
    """
    assert isinstance(proof,dict)and not proof
    proof.update(complete=False,native_activation_qualified=False,full_capture_accepted=False)
    root=Path(root);record=verify_capsule(root)
    if expected_descriptor is not None:assert record['source_descriptor']==expected_descriptor,'Wrong immutable source descriptor'
    before={n:list(sparse.identity(p))for n,p in files(root).items()}
    expected=record['logical'];source=record['source'];plan=record['plan']
    total=0;whole=hashlib.sha256();payload=hashlib.sha256();old_payload=hashlib.sha256()
    header=bytearray()
    def account(data):
        nonlocal total
        assert isinstance(data,bytes)and data
        assert total+len(data)<=expected['bytes'],'Extra logical bytes'
        if len(header)<expected['header_bytes']:
            header.extend(data[:expected['header_bytes']-len(header)])
        whole.update(data)
        a=max(total,expected['header_bytes']);b=total+len(data)
        if a<b:payload.update(data[a-total:b-total])
        b=min(b,source['bytes'])
        if a<b:old_payload.update(data[a-total:b-total])
        total+=len(data)
        return data
    for data in file_chunks(root/record['extents'][0]['name']):yield account(data)
    source_exhausted=False
    for offset,data in sparse.checked_source(source_chunks,source):
        a=max(offset,plan['hole_start']);b=min(offset+len(data),plan['hole_stop'])
        if a<b:yield account(data[a-offset:b-offset])
    source_exhausted=True
    for data in file_chunks(root/record['extents'][1]['name']):yield account(data)
    assert source_exhausted and total==expected['bytes'],'Incomplete logical capture'
    assert whole.hexdigest()==expected['sha256'],'Reconstructed full logical SHA256 mismatch'
    assert payload.hexdigest()==expected['payload_sha256'],'Reconstructed full payload SHA256 mismatch'
    assert old_payload.hexdigest()==source['payload_sha256'],'Retained immutable payload changed'
    assert len(header)==expected['header_bytes']and header.endswith(sparse.MARKER)and header.count(sparse.MARKER)==1
    assert before=={n:list(sparse.identity(p))for n,p in files(root).items()},'Capsule changed during reconstruction'
    verify_capsule(root,record)
    proof.update(complete=True,source_iterator_exhausted=True,original_payload_preserved=True,
        source_bytes_verified=source['bytes'],logical_bytes_verified=total,
        logical_sha256=whole.hexdigest(),payload_sha256=payload.hexdigest(),
        samples_removed=0,resampled=False,all_original_auxiliary_files_preserved=True,
        all_original_directories_preserved=True)
