#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud transport tests, including actual5106-column immutable-prefix fixtures.

The native fixture is a prefix extracted from one hash-verified archive part.
It is deliberately NOT represented as the complete native archive or waveform.
No simulation is started and no electrical acceptance is made by these tests.
"""
import ast,base64,copy,hashlib,io,json,os,random,re,shutil,subprocess,sys,tarfile,tempfile,traceback
from pathlib import Path
import numpy as np
import cloud_native_prefix_delta as delta
import cloud_native_sparse_prefix_store as sparse
import cloud_streamed_native_archive as archive
import read_pll845_all_native_transient as original
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-lossless-prefix-delta-controls'
REPO='repos/Melihakbulut221/nssoc/'
SOURCE_SPEC=dict(run=40001626503,attempt=1,stage='sparse',
    summary_sha256='1f990f8de03976caf21be8592e6584f9b4e6906306133f6b729a171e51534509',
    parts_sha256='ca9a995433ce65fba448e081a5b00e5a012ac3fd829869c553d90f83aad08974')
PARTS_ASSET=670728190
MEMBER='case/actual-acquisition.raw'

def sha(data):return hashlib.sha256(data).hexdigest()
def chunks(data,n=117031):
    for start in range(0,len(data),n):yield data[start:start+n]
def raw_contract(data):
    header=data.index(sparse.MARKER)+len(sparse.MARKER)
    return dict(bytes=len(data),sha256=sha(data),header_bytes=header,
        payload_bytes=len(data)-header,payload_sha256=sha(data[header:]))
def reject(fn):
    try:fn()
    except (AssertionError,FileNotFoundError,KeyError):return
    raise AssertionError('Corrupt transport was accepted')
def api(path):
    return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def hosted(aid):
    return subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])

def actual_native_fixture(destination):
    """Read only a prefix, with explicit part provenance and no full-archive claim."""
    raw=hosted(PARTS_ASSET);assert sha(raw)==SOURCE_SPEC['parts_sha256']
    manifest=json.loads(raw);archive.validate_manifest(manifest)
    first=manifest['parts'][0]
    release=api('releases/tags/cloud-results-40001626503-1-pll-rhi120-c8-native-sparse')
    matches=[x for x in release['assets']if x['name']==first['name']]
    assert len(matches)==1 and matches[0]['size']==first['bytes']
    packed=destination/'native-first-part.gz'
    with packed.open('xb')as f:
        subprocess.run(['gh','api',REPO+'releases/assets/'+str(matches[0]['id']),
            '-H','Accept: application/octet-stream'],stdout=f,check=True)
    assert packed.stat().st_size==first['bytes']and delta.sha(packed)==first['sha256']
    prefix=None;target=manifest['source_directory']+'/'+MEMBER
    with tarfile.open(packed,mode='r|gz')as tar:
        for entry in tar:
            if entry.name!=target:continue
            assert entry.isfile()
            with tar.extractfile(entry)as f:
                head=f.read(original.MAX_HEADER);table,meta=original.parse(head)
                required=meta['header_bytes']+512*len(table)*8
                prefix=head+f.read(required-len(head))
                assert len(prefix)==required
            break
    assert prefix is not None and meta['columns']==len(table)==5106
    values=np.frombuffer(prefix[meta['header_bytes']:],dtype='<f8').reshape(512,5106)
    assert np.isfinite(values).all()and np.all(np.diff(values[:,0])>0)
    original_hash=sha(prefix);old=prefix[:meta['header_bytes']+384*5106*8]
    # Header rewrite is a transport fixture only, and preserves the byte width.
    # Every native payload sample in both fixtures remains bit-identical.
    head=prefix[:meta['header_bytes']]
    m=re.search(rb'(?m)^(No. Points:)([^\n]*)$',head);assert m
    width=len(m[2]);updated=m[1]+b' '+b'512'.rjust(width-1,b'0')
    newhead=head[:m.start()]+updated+head[m.end():];assert len(newhead)==len(head)
    current=newhead+prefix[len(head):]
    return old,current,dict(source_descriptor=SOURCE_SPEC,manifest_asset=PARTS_ASSET,
        manifest_sha256=sha(raw),archive_part=first,archive_part_asset=matches[0]['id'],
        raw_member=target,raw_member_full_size=entry.size,prefix_bytes=len(prefix),
        prefix_sha256=original_hash,columns=5106,rows=512,all_prefix_payload_bits_native=True,
        header_rewrite_for_short_fixture_only=True,whole_archive_verified=False,
        full_capture_accepted=False,native_activation_performed=False)

def exercise(root,old,current):
    root.mkdir();source=raw_contract(old);logical=raw_contract(current)
    assert logical['header_bytes']==source['header_bytes']
    assert current[source['header_bytes']:len(old)]==old[source['header_bytes']:]
    native=root/'native';(native/'case').mkdir(parents=True)
    raw=native/MEMBER
    plan=sparse.materialize(raw,chunks(old),source,head_keep=2*sparse.BLOCK,tail_keep=2*sparse.BLOCK)
    with raw.open('r+b')as f:
        f.write(current[:source['header_bytes']]);f.seek(len(old));f.write(current[len(old):])
    (native/'result.json').write_text('{"fixture":true,"full_capture":false}\n')
    (native/'case/models.inc').write_bytes(b'Unchanged native fixture auxiliary bytes\x00\xff')
    (native/'case/models.inc').chmod(0o640)
    native_before=delta.snapshot(native,MEMBER)
    capsule=root/'capsule'
    record=delta.write_capsule(native,capsule,MEMBER,SOURCE_SPEC,source,plan,logical,lambda:True)
    proof={};rebuilt=b''.join(delta.capture_chunks(capsule,chunks(old),proof,SOURCE_SPEC))
    assert rebuilt==current and proof['complete']and proof['source_iterator_exhausted']
    assert proof['logical_sha256']==logical['sha256']
    assert not (capsule/MEMBER).exists()
    stored=sum(x['bytes']for x in record['extents'])
    assert stored==len(current)-(plan['hole_stop']-plan['hole_start'])<len(current)
    # Archive publication/extraction retains every non-raw file and both exact extents.
    destination=root/'packed';destination.mkdir();published={}
    def send(path):
        saved=root/('published-'+path.name);shutil.copyfile(path,saved);published[path.name]=saved
        return dict(name=path.name,bytes=saved.stat().st_size,sha256=delta.sha(saved))
    manifest=archive.stream_pack(capsule,'delta-fixture',destination,send,part_bytes=2*1024**2)
    def download(row,path):shutil.copyfile(published[row['name']],path)
    restored=root/'restored';archive.extract_verified(manifest,root/'staging',restored,download)
    roundproof={};assert b''.join(delta.capture_chunks(restored/'capsule',chunks(old),roundproof,SOURCE_SPEC))==current
    assert roundproof['complete']
    failures=[]
    def run_fault(name,fn):
        reject(fn);failures.append(name)
    def consume(data=old,expected=SOURCE_SPEC):
        p={};result=b''.join(delta.capture_chunks(capsule,chunks(data),p,expected))
        assert p['complete'];return result
    run_fault('missing-prefix',lambda:consume(b''))
    run_fault('truncated-prefix',lambda:consume(old[:-1]))
    run_fault('extra-prefix-byte',lambda:consume(old+b'x'))
    changed=bytearray(old);changed[source['header_bytes']+100]^=1
    run_fault('corrupt-prefix-byte',lambda:consume(bytes(changed)))
    seq=list(chunks(old));reordered=seq.copy();reordered[2],reordered[3]=reordered[3],reordered[2]
    run_fault('prefix-chunk-order',lambda:consume(b''.join(reordered)))
    run_fault('duplicated-prefix-chunk',lambda:consume(b''.join(seq[:4]+[seq[3]]+seq[4:])))
    wrong=copy.deepcopy(SOURCE_SPEC);wrong['summary_sha256']='0'*64
    run_fault('wrong-bound-source-descriptor',lambda:consume(expected=wrong))
    contract_path=capsule/delta.CONTRACT;original_record=contract_path.read_bytes()
    def record_fault(name,edit):
        bad=copy.deepcopy(record);edit(bad)
        contract_path.write_text(json.dumps(bad))
        try:run_fault(name,consume)
        finally:contract_path.write_bytes(original_record)
    record_fault('extent-order',lambda r:r['extents'].reverse())
    record_fault('missing-extent',lambda r:r['extents'].pop())
    record_fault('extent-overlap',lambda r:r['extents'][1].update(start=r['plan']['hole_start']))
    record_fault('extent-gap',lambda r:r['extents'][1].update(start=r['plan']['hole_stop']+1))
    record_fault('unbound-source-hash',lambda r:r['source'].update(sha256='1'*64))
    record_fault('wrong-full-logical-hash',lambda r:r['logical'].update(sha256='2'*64))
    record_fault('wrong-full-payload-hash',lambda r:r['logical'].update(payload_sha256='3'*64))
    record_fault('unqualified-format',lambda r:r.update(format='ordinary-full-raw-v1'))
    record_fault('native-acceptance-claim',lambda r:r.update(native_activation_qualified=True))
    record_fault('unsafe-extent-path',lambda r:r['extents'][0].update(name='../outside'))
    def content_fault(name,path,edit):
        data=path.read_bytes();path.write_bytes(edit(data))
        try:run_fault(name,consume)
        finally:path.write_bytes(data)
    content_fault('corrupt-head',capsule/record['extents'][0]['name'],lambda b:bytes([b[0]^1])+b[1:])
    content_fault('corrupt-tail',capsule/record['extents'][1]['name'],lambda b:b[:-1]+bytes([b[-1]^1]))
    content_fault('truncated-tail',capsule/record['extents'][1]['name'],lambda b:b[:-1])
    content_fault('changed-auxiliary-file',capsule/'case/models.inc',lambda b:b+b'changed')
    aux=capsule/'case/models.inc';aux.rename(aux.with_suffix('.missing'))
    try:run_fault('missing-auxiliary-file',consume)
    finally:aux.with_suffix('.missing').rename(aux)
    extra=capsule/'untracked.bin';extra.write_bytes(b'x')
    try:run_fault('untracked-file',consume)
    finally:extra.unlink()
    # Consistent malicious replacement hashes still cannot change a prior payload bit.
    head_path=capsule/record['extents'][0]['name'];head=head_path.read_bytes()
    badhead=bytearray(head);offset=source['header_bytes']+8;badhead[offset]^=1
    badall=bytearray(current);badall[offset]^=1
    head_path.write_bytes(badhead);bad=copy.deepcopy(record)
    bad['extents'][0]['sha256']=sha(badhead);bad['logical']=raw_contract(bytes(badall))
    bad['original_files'][MEMBER]['sha256']=bad['logical']['sha256']
    contract_path.write_text(json.dumps(bad))
    try:run_fault('changed-prior-payload-even-with-consistent-new-hashes',consume)
    finally:head_path.write_bytes(head);contract_path.write_bytes(original_record)
    p={};it=delta.capture_chunks(capsule,chunks(old),p,SOURCE_SPEC);next(it);it.close()
    assert p['complete']is False;failures.append('early-consumer-cannot-claim-complete')
    p={};it=delta.capture_chunks(capsule,chunks(old),p,SOURCE_SPEC);next(it)
    data=aux.read_bytes();aux.write_bytes(data+b'race')
    try:run_fault('capsule-mutated-during-reconstruction',lambda:list(it))
    finally:aux.write_bytes(data)
    assert not p['complete']
    run_fault('live-native-process',lambda:delta.write_capsule(native,root/'live-reject',MEMBER,
        SOURCE_SPEC,source,plan,logical,lambda:False))
    stopped=iter([True,False])
    run_fault('native-reactivated-during-copy',lambda:delta.write_capsule(native,root/'restart-reject',MEMBER,
        SOURCE_SPEC,source,plan,logical,lambda:next(stopped)))
    assert delta.snapshot(native,MEMBER)==native_before
    assert len(failures)==28,len(failures)
    return dict(status='PASS_TRANSPORT_ONLY',logical_bytes=len(current),source_bytes=len(old),
        stored_raw_extent_bytes=stored,prefix_bytes_not_retransmitted=plan['hole_stop']-plan['hole_start'],
        full_reconstructed_bytes_equal=True,full_reconstructed_sha256=sha(rebuilt),
        original_payload_preserved=True,original_auxiliary_files_preserved=True,
        archive_roundtrip=roundproof,negative_controls=failures,
        native_source_unchanged=True,native_activation_performed=False,full_capture_accepted=False)

def methods():
    record=json.loads((ROOT/'scripts/pll-lossless-prefix-delta-method.json').read_text())
    for path,digest in record['protected'].items():assert delta.sha(ROOT/path)==digest,path
    return record

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Run transport qualification in cloud only'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],
        native_activation_performed=False,full_capture_accepted=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        protected=methods();result['protected_methods']=protected
        scratch=Path(tempfile.mkdtemp(prefix='nssoc-prefix-delta-',dir=os.environ['RUNNER_TEMP']))
        randomizer=random.Random(20261024)
        header=b'Title: explicit synthetic transport fixture\nBinary:\n'
        payload=randomizer.randbytes(8*1024**2)
        old=header+payload;current=header+payload+randomizer.randbytes(1024**2)
        result['synthetic']=exercise(scratch/'synthetic',old,current)
        actual=scratch/'actual-source';actual.mkdir()
        old,current,provenance=actual_native_fixture(actual)
        result['actual_native_prefix_provenance']=provenance
        result['actual_native_prefix']=exercise(scratch/'actual',old,current)
        # These full-column binary64 matrices are transport oracles, not a
        # shortened electrical acceptance test or substitute for the full run.
        h=raw_contract(current)['header_bytes']
        capsule=scratch/'actual/capsule';proof={}
        rebuilt=b''.join(delta.capture_chunks(capsule,chunks(old),proof,SOURCE_SPEC))
        a=np.frombuffer(current[h:],dtype='<u8').reshape(512,5106)
        b=np.frombuffer(rebuilt[h:],dtype='<u8').reshape(512,5106)
        assert np.array_equal(a,b)
        result['all5106_native_prefix_columns']=dict(rows=512,columns=5106,
            compared_binary64_samples=int(a.size),bit_identical=True,columns_dropped=0,
            resampled=False,full_capture_accepted=False)
        assert methods()==protected
        result['sources_unchanged']=True
        result['status']='PASS_LOSSLESS_PREFIX_DELTA_ALL_BYTES_ACTUAL5106_COLUMN_FIXTURE_AND56_CORRUPTIONS_NOT_NATIVE_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_LOSSLESS_PREFIX_DELTA_CONTROLS',error=repr(error),traceback=traceback.format_exc());raise
    finally:save();print(json.dumps({k:result[k]for k in ('status','error')if k in result}),flush=True)

if __name__=='__main__':main()
