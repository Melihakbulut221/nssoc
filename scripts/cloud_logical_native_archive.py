#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lossless ordinary tar publication from stopped sparse native working files.

Storage qualification only. A caller must separately establish native process
quiescence and full electrical/physical acceptance. No sparse zero-filled file
is presented as an original waveform.
"""
import hashlib,io,json,os,stat,tarfile
from pathlib import Path,PurePosixPath
import cloud_streamed_native_archive as archive
import cloud_native_sparse_prefix_store as sparse

def relative_name(name):
    assert isinstance(name,str)and name and str(PurePosixPath(name))==name
    p=PurePosixPath(name)
    assert not p.is_absolute()and not any(x in ('..','.')for x in p.parts)
    return name

def inventory(root):
    root=Path(root)
    result={}
    for p in [root,*sorted(root.rglob('*'))]:
        st=p.lstat();kind=stat.S_IFMT(st.st_mode)
        assert kind in (stat.S_IFREG,stat.S_IFDIR,stat.S_IFLNK),'Unsupported native archive file type'
        key='.'if p==root else p.relative_to(root).as_posix()
        target=os.readlink(p)if p.is_symlink()else None
        if target is not None:
            assert not Path(target).is_absolute()and p.resolve().is_relative_to(root),'Unsafe native symlink'
        result[key]=(st.st_dev,st.st_ino,st.st_size,st.st_mode,st.st_uid,st.st_gid,st.st_mtime_ns,st.st_ctime_ns,target)
    return result

class VerifiedReader(io.RawIOBase):
    def __init__(self,chunks,size,original=None):
        self.chunks=iter(chunks);self.size=size;self.original=original
        self.pending=b'';self.offset=0;self.total=0;self.done=False
        self.whole=hashlib.sha256();self.payload=hashlib.sha256();self.old_payload=hashlib.sha256()
    def readable(self):return True
    def readinto(self,buffer):
        view=memoryview(buffer);used=0
        while used<len(view):
            if self.offset==len(self.pending):
                try:self.pending=next(self.chunks)
                except StopIteration:self.done=True;break
                assert isinstance(self.pending,bytes)and self.pending,'Invalid logical archive chunk'
                self.offset=0
            n=min(len(view)-used,len(self.pending)-self.offset)
            data=self.pending[self.offset:self.offset+n]
            assert self.total+n<=self.size,'Archive input grew beyond the declared member size'
            view[used:used+n]=data;self.whole.update(data)
            if self.original is not None:
                a=max(0,self.original['header_bytes']-self.total)
                if a<n:self.payload.update(data[a:])
                b=min(n,self.original['bytes']-self.total)
                if a<b:self.old_payload.update(data[a:b])
            used+=n;self.offset+=n;self.total+=n
        return used
    def finish(self):
        # tar.addfile reads exactly member.size and need not request EOF.
        # This extra read must exhaust the source verifier, including its final
        # immutable SHA and stopped-file identity checks, before any manifest.
        assert self.read(1)==b''and self.done and self.total==self.size,'Incomplete archive member'
        proof=dict(bytes=self.total,sha256=self.whole.hexdigest(),source_iterator_exhausted=True)
        if self.original is not None:
            assert self.old_payload.hexdigest()==self.original['payload_sha256'],'Original retained native payload changed'
            proof.update(header_bytes=self.original['header_bytes'],payload_bytes=self.total-self.original['header_bytes'],
                payload_sha256=self.payload.hexdigest(),original_payload_preserved=True,original=self.original)
        return proof
    def close(self):
        close=getattr(self.chunks,'close',None)
        if close is not None:close()
        super().close()

def file_chunks(path):
    with Path(path).open('rb')as f:
        while data:=f.read(archive.CHUNK):yield data

class PartSink:
    """At most one unverified compressed part on disk; never remove failed data."""
    def __init__(self,stem,destination,send,limit):
        self.stem=stem;self.destination=Path(destination);self.send=send;self.limit=limit
        self.parts=[];self.receipts=[];self.stream=None;self.path=None;self.used=0
        self.total=0;self.digest=hashlib.sha256()
    def finish_part(self):
        self.stream.close();self.stream=None
        p=dict(index=len(self.parts),name=self.path.name,bytes=self.used,sha256=archive.sha(self.path))
        assert 0<self.used<=self.limit and self.path.stat().st_size==self.used
        receipt=self.send(self.path);archive.verify_receipt(p,receipt)
        assert self.path.parent==self.destination and self.path.name==self.stem+'.tar.gz.part'+str(len(self.parts)).zfill(4)
        assert self.path.stat().st_size==self.used and archive.sha(self.path)==p['sha256'],'Published part changed'
        self.path.unlink();self.parts.append(p);self.receipts.append(receipt);self.path=None
    def write(self,data):
        self.digest.update(data);self.total+=len(data);offset=0
        while offset<len(data):
            if self.stream is None:
                self.path=self.destination/(self.stem+'.tar.gz.part'+str(len(self.parts)).zfill(4))
                self.stream=self.path.open('xb');self.used=0
            n=min(self.limit-self.used,len(data)-offset)
            self.stream.write(data[offset:offset+n]);self.used+=n;offset+=n
            if self.used==self.limit:self.finish_part()
        return len(data)
    def finish(self):
        if self.stream is not None:self.finish_part()
    def abort(self):
        if self.stream is not None:self.stream.close();self.stream=None

def stream_pack(directory,stem,destination,send,logical_members,stop_check,part_bytes=archive.PART_BYTES):
    directory=Path(directory).resolve();destination=Path(destination).resolve()
    assert directory.is_dir()and destination.is_dir()and not destination.is_relative_to(directory)
    assert relative_name(stem)==Path(stem).name and type(part_bytes)is int and part_bytes>0
    assert callable(stop_check)and stop_check()is True,'Stopped native process must be established by caller'
    assert logical_members
    for key,spec in logical_members.items():
        relative_name(key);assert set(spec)=={'source','plan','open_source'}and callable(spec['open_source'])
        p=directory/key
        assert p.is_file()and not p.is_symlink()and p.stat().st_nlink==1
        sparse.validate_plan(spec['plan'],spec['source'])
        sparse.unchanged_hole(p,spec['plan'],spec['source'])
    manifest_path=destination/(stem+'.parts.json')
    assert not manifest_path.exists()and not list(destination.glob(stem+'.tar.gz.part*')),'Never overwrite an archive attempt'
    before=inventory(directory);proofs={};seen=set()
    sink=PartSink(stem,destination,send,part_bytes)
    try:
        with tarfile.open(fileobj=sink,mode='w|gz',format=tarfile.PAX_FORMAT,compresslevel=6)as tar:
            for key in before:
                path=directory if key=='.'else directory/key
                arc=directory.name if key=='.'else directory.name+'/'+key
                info=tar.gettarinfo(str(path),arcname=arc)
                if key in logical_members:assert info.isfile(),'Logical raw cannot be a hardlink or symlink'
                if not info.isfile():
                    tar.addfile(info);continue
                spec=logical_members.get(key)
                if spec is None:chunks=file_chunks(path)
                else:
                    seen.add(key)
                    chunks=sparse.logical_chunks(path,spec['open_source'](),spec['plan'],spec['source'])
                with VerifiedReader(chunks,info.size,None if spec is None else spec['source'])as reader:
                    tar.addfile(info,reader);proofs[key]=reader.finish()
        assert seen==set(logical_members),'Missing logical member'
        assert stop_check()is True,'Native process resumed during archival'
        assert inventory(directory)==before,'Source tree changed during archival'
        for key,spec in logical_members.items():sparse.unchanged_hole(directory/key,spec['plan'],spec['source'])
        sink.finish()
        m=dict(format='ordered-tar-gzip-parts-v1',stem=stem,source_directory=directory.name,
            bytes=sink.total,sha256=sink.digest.hexdigest(),parts=sink.parts,part_limit_bytes=part_bytes,
            meaning='Ordinary complete native files. Sparse old prefix was reconstructed from verified immutable source; all original payload preserved.',
            hosted_receipts=sink.receipts,
            verification=dict(parts=len(sink.parts),bytes=sink.total,sha256=sink.digest.hexdigest(),
                all_parts_and_combined_bytes_verified=True,hosted_part_size_and_digest_verified=True,
                compressed_staging_part_limit_bytes=part_bytes,source_tree_unchanged=True,
                all_source_iterators_exhausted=True,original_source_deleted=False,
                logical_members={k:proofs[k]for k in logical_members},regular_files=proofs,
                native_activation_qualified=False,full_capture_accepted=False))
        archive.validate_manifest(m)
        for p,r in zip(m['parts'],m['hosted_receipts'],strict=True):archive.verify_receipt(p,r)
        with manifest_path.open('x')as f:f.write(json.dumps(m,indent=2)+'\n')
        return m
    finally:sink.abort()

def extract_sparse(manifest,staging,destination,download,members):
    """Restore ordinary archive into new sparse working files; never activate here."""
    archive.validate_manifest(manifest)
    destination=Path(destination);staging=Path(staging)
    destination.mkdir(parents=True,exist_ok=True);staging.mkdir(parents=True,exist_ok=True)
    root=destination/manifest['source_directory'];assert not root.exists()
    for key,spec in members.items():
        relative_name(key)
        assert set(spec)=={'source','head_keep','tail_keep'}
        sparse.plan_for(spec['source'],spec['head_keep'],spec['tail_keep'])
    assert members
    seen=set();plans={}
    with archive.verified_remote_parts(manifest,staging,download)as stream:
        with tarfile.open(fileobj=stream,mode='r|gz')as tar:
            for member in tar:
                p=PurePosixPath(member.name)
                assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==manifest['source_directory']
                assert member.name not in seen,'Duplicate native archive member'
                seen.add(member.name)
                assert not(member.isdev()or member.isfifo())
                filtered=tarfile.data_filter(member,str(destination))
                key='/'.join(p.parts[1:])
                if key not in members:
                    tar.extract(member,destination,filter='data');continue
                spec=members[key];assert member.isfile()and member.size==spec['source']['bytes']
                target=destination/member.name;target.parent.mkdir(parents=True,exist_ok=True)
                assert target.resolve().is_relative_to(root.resolve())and not target.exists()
                with tar.extractfile(member)as f:
                    def chunks():
                        while data:=f.read(archive.CHUNK):yield data
                    plans[key]=sparse.materialize(target,chunks(),spec['source'],spec['head_keep'],spec['tail_keep'])
                if filtered.mode is not None:target.chmod(filtered.mode)
    assert set(plans)==set(members),'Archive missing expected native raw'
    return dict(all_parts_verified_before_delivery=True,whole_ordered_archive_verified_before_native_activation=True,
        bytes=manifest['bytes'],sha256=manifest['sha256'],plans=plans,
        native_activation_qualified=False,sparse_working_file_not_valid_waveform=True)
