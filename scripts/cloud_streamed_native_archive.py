#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lossless hosted archive streaming; never trim native evidence or replace its capture."""
import argparse,contextlib,copy,hashlib,io,json,os,re,subprocess,tarfile,tempfile
from pathlib import Path
CHUNK=4*1024**2
PART_BYTES=256*1024**2
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate_manifest(m):
    assert m['format']=='ordered-tar-gzip-parts-v1' and m['parts']
    assert Path(m['stem']).name==m['stem']and m['stem']not in ('','.','..')
    assert Path(m['source_directory']).name==m['source_directory']and m['source_directory']not in ('','.','..')
    total=0;names=set()
    for i,p in enumerate(m['parts']):
        assert p['index']==i and p['name']==m['stem']+'.tar.gz.part'+str(i).zfill(4)
        assert p['name']not in names and isinstance(p['bytes'],int)and 0<p['bytes']<=m['part_limit_bytes']
        assert re.fullmatch('[0-9a-f]{64}',p['sha256'])
        names.add(p['name']);total+=p['bytes']
    assert total==m['bytes']and re.fullmatch('[0-9a-f]{64}',m['sha256'])
def verify_receipt(p,r):
    assert r['name']==p['name']and r['bytes']==p['bytes']and r['sha256']==p['sha256'],'Hosted asset identity/size/digest mismatch'
def stream_pack(directory,stem,destination,send,part_bytes=PART_BYTES):
    directory=Path(directory).resolve();destination=Path(destination).resolve()
    assert directory.is_dir()and destination.is_dir()and not destination.is_relative_to(directory)
    assert Path(stem).name==stem and stem not in ('','.','..')and part_bytes>0
    process=subprocess.Popen(['tar','-czf','-','--',directory.name],cwd=directory.parent,stdout=subprocess.PIPE)
    parts=[];receipts=[];whole=hashlib.sha256();total=0;stream=None;path=None;used=0
    def finish():
        nonlocal stream,path,used
        stream.close();stream=None
        p=dict(index=len(parts),name=path.name,bytes=used,sha256=sha(path))
        assert 0<used<=part_bytes and path.stat().st_size==used
        r=send(path);verify_receipt(p,r)
        # Delete only this exact temporary compressed part after hosted verification.
        # Original native files and every unfinished/failed part remain untouched.
        assert path.parent==destination and path.name==stem+'.tar.gz.part'+str(len(parts)).zfill(4)
        assert path.stat().st_size==used and sha(path)==p['sha256'],'Part changed during publication'
        path.unlink();parts.append(p);receipts.append(r);path=None
    try:
        while data:=process.stdout.read(CHUNK):
            whole.update(data);total+=len(data);offset=0
            while offset<len(data):
                if stream is None:
                    path=destination/(stem+'.tar.gz.part'+str(len(parts)).zfill(4));stream=path.open('xb');used=0
                n=min(part_bytes-used,len(data)-offset);stream.write(data[offset:offset+n]);used+=n;offset+=n
                if used==part_bytes:finish()
        if stream is not None:finish()
        assert process.wait()==0 and total>0,'Native tar failed; no complete manifest'
    finally:
        if stream is not None:stream.close()
        process.stdout.close()
        if process.poll() is None:process.kill();process.wait()
    m=dict(format='ordered-tar-gzip-parts-v1',stem=stem,source_directory=directory.name,
        bytes=total,sha256=whole.hexdigest(),parts=parts,part_limit_bytes=part_bytes,
        meaning='All original native evidence retained. Verify ordered parts and total SHA256 before native activation.',
        verification=dict(parts=len(parts),bytes=total,sha256=whole.hexdigest(),
            all_parts_and_combined_bytes_verified=True,hosted_part_size_and_digest_verified=True,
            compressed_staging_part_limit_bytes=part_bytes,original_source_deleted=False),
        hosted_receipts=receipts)
    validate_manifest(m)
    assert len(receipts)==len(parts)
    for p,r in zip(parts,receipts,strict=True):verify_receipt(p,r)
    (destination/(stem+'.parts.json')).write_text(json.dumps(m,indent=2)+'\n')
    return m

class VerifiedRemoteParts(io.RawIOBase):
    """Verify each downloaded part before delivery, then verify the complete ordered stream."""
    def __init__(self,manifest,staging,download):
        validate_manifest(manifest);self.m=manifest;self.staging=Path(staging);self.download=download
        self.index=0;self.stream=None;self.path=None;self.total=0;self.digest=hashlib.sha256();self.complete=False
    def readable(self):return True
    def readinto(self,buffer):
        view=memoryview(buffer);used=0
        while used<len(view):
            if self.stream is None:
                if self.index==len(self.m['parts']):
                    assert self.total==self.m['bytes']and self.digest.hexdigest()==self.m['sha256'],'Ordered archive digest mismatch'
                    self.complete=True;break
                row=self.m['parts'][self.index];self.path=self.staging/row['name']
                assert not self.path.exists()
                self.download(row,self.path)
                assert self.path.is_file()and not self.path.is_symlink()
                assert self.path.stat().st_size==row['bytes']and sha(self.path)==row['sha256'],'Downloaded part corrupt/truncated'
                self.stream=self.path.open('rb')
            n=self.stream.readinto(view[used:])
            if n:
                self.digest.update(view[used:used+n]);self.total+=n;used+=n
            else:
                self.stream.close();self.stream=None
                assert self.path.parent==self.staging
                self.path.unlink();self.path=None;self.index+=1
        return used
    def close(self):
        if self.stream is not None:self.stream.close();self.stream=None
        super().close()
@contextlib.contextmanager
def verified_remote_parts(manifest,staging,download):
    raw=VerifiedRemoteParts(manifest,staging,download)
    with io.BufferedReader(raw,buffer_size=CHUNK)as stream:
        yield stream
        # tar may stop at end-of-archive before consuming the gzip footer.
        while stream.read(CHUNK):pass
        assert raw.complete,'Incomplete archive; native restore is forbidden'
def extract_verified(manifest,staging,destination,download):
    destination=Path(destination);staging=Path(staging)
    destination.mkdir(parents=True,exist_ok=True);staging.mkdir(parents=True,exist_ok=True)
    assert not(destination/manifest['source_directory']).exists()
    with verified_remote_parts(manifest,staging,download)as stream:
        with tarfile.open(fileobj=stream,mode='r|gz')as tar:
            for member in tar:
                p=Path(member.name)
                assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==manifest['source_directory']
                assert not(member.isdev()or member.isfifo())
                tar.extract(member,destination,filter='data')
    return dict(all_parts_verified_before_delivery=True,whole_ordered_archive_verified_before_native_activation=True,
        bytes=manifest['bytes'],sha256=manifest['sha256'],local_compressed_copy_limit_bytes=manifest['part_limit_bytes'])
def controls():
    rejected=[]
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp);source=root/'source';stage=root/'stage';source.mkdir();stage.mkdir()
        payload=bytes(range(256))*257
        (source/'native.raw').write_bytes(payload);(source/'sub').mkdir();(source/'sub/circuit.cir').write_text('native circuit fixture\n')
        original={str(p.relative_to(source)):sha(p)for p in source.rglob('*')if p.is_file()}
        remote={};maximum=0
        def send(path):
            nonlocal maximum
            size=sum(p.stat().st_size for p in stage.glob('*.part*'))
            maximum=max(maximum,size);assert len(list(stage.glob('*.part*')))==1 and size<=127
            remote[path.name]=path.read_bytes()
            return dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path))
        m=stream_pack(source,'fixture',stage,send,127)
        assert len(m['parts'])>1 and maximum<=127 and not list(stage.glob('*.part*'))
        joined=b''.join(remote[p['name']]for p in m['parts'])
        assert hashlib.sha256(joined).hexdigest()==m['sha256']
        with tarfile.open(fileobj=io.BytesIO(joined),mode='r:gz')as t:assert t.extractfile('source/native.raw').read()==payload
        def download(row,path):path.write_bytes(remote[row['name']])
        proof=extract_verified(m,root/'input',root/'restored',download)
        assert proof['whole_ordered_archive_verified_before_native_activation']
        assert (root/'restored/source/native.raw').read_bytes()==payload
        assert not list((root/'input').glob('*.part*'))
        for label in ('wrong-hosted-name','wrong-hosted-size','wrong-hosted-digest','failed-upload'):
            def badsend(path):
                if label=='failed-upload':raise OSError('injected upload failure')
                r=dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path))
                r[{'wrong-hosted-name':'name','wrong-hosted-size':'bytes','wrong-hosted-digest':'sha256'}[label]]='bad'if label!='wrong-hosted-size'else 1
                return r
            bad=root/label;bad.mkdir()
            try:stream_pack(source,label,bad,badsend,127)
            except (AssertionError,OSError):rejected.append(label)
            else:raise AssertionError(label+' accepted')
            assert not(bad/(label+'.parts.json')).exists()and list(bad.glob('*.part*')),'Failed part lost'
        for label in ('wrong-order','missing-part','wrong-size','wrong-part-digest','wrong-whole-digest','unsafe-part','corrupt-download','truncated-download'):
            broken=copy.deepcopy(m)
            if label=='wrong-order':broken['parts']=broken['parts'][::-1]
            elif label=='missing-part':broken['parts'].pop()
            elif label=='wrong-size':broken['parts'][0]['bytes']+=1
            elif label=='wrong-part-digest':broken['parts'][0]['sha256']='0'*64
            elif label=='wrong-whole-digest':broken['sha256']='0'*64
            elif label=='unsafe-part':broken['parts'][0]['name']='../escape'
            def badget(row,path):
                raw=remote[row['name']]
                if label=='corrupt-download':raw=bytes([raw[0]^1])+raw[1:]
                if label=='truncated-download':raw=raw[:-1]
                path.write_bytes(raw)
            try:extract_verified(broken,root/(label+'-staging'),root/(label+'-destination'),badget)
            except (AssertionError,OSError,tarfile.TarError,EOFError):rejected.append(label)
            else:raise AssertionError(label+' accepted')
        assert {str(p.relative_to(source)):sha(p)for p in source.rglob('*')if p.is_file()}==original
        assert len(rejected)==12
    return dict(exact_tar_and_payload_roundtrip=True,max_local_compressed_bytes=maximum,part_limit_bytes=127,
        original_source_unchanged=True,partial_publications_not_accepted=True,
        negative_controls=rejected,native_or_phy_acceptance=False)

def hosted_smoke():
    from publish_cloud_results import result_tag
    from migrate_outputs_to_cloud import publish
    from route_cloud_newer_postcts import fetch
    root=Path(os.environ['RUNNER_TEMP'])/'streamed-evidence-smoke';root.mkdir(exist_ok=False)
    source=root/'source';source.mkdir();stage=root/'staging';stage.mkdir()
    payload=os.urandom(1024**2);(source/'fixture.bin').write_bytes(payload)
    tag=result_tag('pll-stream-archive-controls',os.environ)
    m=stream_pack(source,'pll-stream-smoke-'+os.environ['GITHUB_RUN_ID'],stage,lambda p:publish(p,tag),512*1024)
    # Publication of the manifest follows verified remote completion of every part.
    manifest_path=stage/(m['stem']+'.parts.json');record=publish(manifest_path,tag)
    receipt={r['name']:r for r in m['hosted_receipts']}
    def get(row,path):fetch(receipt[row['name']]['url'],row['sha256'],path)
    proof=extract_verified(m,root/'download',root/'restore',get)
    assert (root/'restore/source/fixture.bin').read_bytes()==payload
    assert (source/'fixture.bin').read_bytes()==payload
    report=dict(status='PASS_REAL_GITHUB_PART_PUBLICATION_AND_VERIFIED_RESTORE_FIXTURE_ONLY',
        parts=len(m['parts']),bytes=m['bytes'],source_sha256=sha(source/'fixture.bin'),
        manifest=record,restore=proof,original_source_retained=True,native_or_phy_acceptance=False)
    p=stage/'hosted-roundtrip.json';p.write_text(json.dumps(report,indent=2)+'\n');publish(p,tag);return report
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true','Run storage tests only on hosted runners'
    p=argparse.ArgumentParser();p.add_argument('--hosted-smoke',action='store_true');a=p.parse_args()
    print(json.dumps(hosted_smoke()if a.hosted_smoke else controls()))
