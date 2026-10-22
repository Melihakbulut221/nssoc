#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only production integration controls; no short capture can accept full1us."""
import copy,hashlib,io,json,os,tarfile,traceback
from pathlib import Path
import cloud_pll845_sparse_io as storage
import cloud_native_sparse_prefix_store as sparse
import cloud_streamed_native_archive as archive
import cloud_logical_native_archive_controls as previous
import cloud_pll845_sparse_disk as disk
import cloud_pll845_sparse_acquisition as native
import publish_pll845_sparse_checkpoint as publisher
import read_pll845_sparse_completed as reader
def digest(b):return hashlib.sha256(b).hexdigest()
def source_controls(root):
    root.mkdir(exist_ok=False)
    header=b'Title: storage integration fixture only\nNo. Points: 0000000000\nBinary:\n'
    raw=header+os.urandom(8*1024**2+127)
    source=dict(bytes=len(raw),sha256=digest(raw),header_bytes=len(header),
        payload_bytes=len(raw)-len(header),payload_sha256=digest(raw[len(header):]))
    def make(duplicate=False,link=False):
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w:gz')as tar:
            for name,data in [('cloud-pll845-native-acquisition/'+storage.RAW,raw),
                ('cloud-pll845-native-acquisition/after-raw',os.urandom(1024**2))]:
                item=tarfile.TarInfo(name);item.size=len(data);tar.addfile(item,io.BytesIO(data))
            if duplicate:
                item=tarfile.TarInfo('cloud-pll845-native-acquisition/'+storage.RAW);item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
            if link:
                item=tarfile.TarInfo('cloud-pll845-native-acquisition/link');item.type=tarfile.SYMTYPE;item.linkname='/outside';tar.addfile(item)
        packed=buffer.getvalue();stem='pll845-native-acquisition-initial-123-1';rows=[];remote={};limit=256*1024
        for i,offset in enumerate(range(0,len(packed),limit)):
            data=packed[offset:offset+limit];name=stem+'.tar.gz.part'+str(i).zfill(4)
            rows.append(dict(index=i,name=name,bytes=len(data),sha256=digest(data)));remote[name]=data
        m=dict(format='ordered-tar-gzip-parts-v1',stem=stem,source_directory='cloud-pll845-native-acquisition',
            bytes=len(packed),sha256=digest(packed),part_limit_bytes=limit,parts=rows)
        return m,remote
    m,remote=make()
    def get(row,path):path.write_bytes(remote[row['name']])
    def chunks(manifest=m,getter=get,member=storage.RAW,size=len(raw),label='read'):
        return storage.source_member_chunks(manifest,root/label,getter,member,size)
    assert b''.join(chunks())==raw
    target=root/'sparse.raw';plan=sparse.materialize(target,chunks(label='materialize'),source,1024**2,1024**2)
    with target.open('r+b')as f:
        f.seek(0);f.write(header.replace(b'0000000000',b'0000000042'));f.seek(0,2);f.write(b'new actual bytes')
    snapshot=sparse.inspect_logical(target,chunks(label='inspect'),plan,source)
    assert snapshot['sha256']==digest(header.replace(b'0000000000',b'0000000042')+raw[len(header):]+b'new actual bytes')
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (AssertionError,OSError,tarfile.TarError,EOFError):rejected.append(label)
        else:raise AssertionError('Invalid production archive accepted: '+label)
    reject('missing-member',lambda:b''.join(chunks(member='absent.raw',label='missing')))
    reject('wrong-member-size',lambda:b''.join(chunks(size=len(raw)+1,label='size')))
    bad=copy.deepcopy(m);bad['sha256']='0'*64
    reject('wrong-full-archive-after-yield',lambda:sparse.materialize(root/'bad-full.raw',chunks(manifest=bad,label='whole'),source,1024**2,1024**2))
    assert (root/'bad-full.raw').exists(),'Failed raw evidence must remain'
    def corrupt(row,path):
        data=remote[row['name']]
        if row['index']==len(m['parts'])-1:data=data[:-1]+bytes([data[-1]^1])
        path.write_bytes(data)
    reject('late-part-corruption-after-raw',lambda:sparse.materialize(root/'bad-late.raw',chunks(getter=corrupt,label='late'),source,1024**2,1024**2))
    for label,dup,link in [('duplicate-raw',True,False),('unsafe-link',False,True)]:
        broken,bytes_by_name=make(dup,link)
        def other_get(row,path):path.write_bytes(bytes_by_name[row['name']])
        reject(label,lambda broken=broken,label=label:b''.join(chunks(manifest=broken,getter=other_get,label=label)))
    reject('live-native-inspection',lambda:storage.snapshot(root,lambda:False))
    assert len(rejected)==7
    return dict(all_source_and_late_archive_bytes_verified=True,stopped_append_and_header_backpatch_exact=True,
        rejected=rejected,source_bytes=len(raw),native_or_full_capture_acceptance=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    root=Path.cwd();out=root/'cloud-pll845-sparse-production-controls';out.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
    try:
        r['native_methods']=disk.controls()
        assert native.method_hashes()==disk.source_contract(root)[1]
        r['original_native']=native.controls()
        r['original_logical_archive']=previous.controls(out/'logical')
        r['source_iterator']=source_controls(out/'source')
        r['metadata_reconciliation']=metadata_controls(out/'metadata')
        r['publication']=publisher.controls();r['complete_reader']=reader.controls()
        disk.source_contract(root)
        r['status']='PASS_SPARSE_PRODUCTION_METHOD_MIGRATION_SOURCE_ARCHIVE_AND_ORIGINAL_GATES_REQUIRES_REAL_CONTINUATION'
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps({k:r[k]for k in ('status','error')if k in r}),flush=True)

def metadata_controls(root):
    root.mkdir(exist_ok=False)
    actual=json.loads((Path(__file__).resolve().parents[1]/storage.RECONCILIATION).read_text())
    assert storage.validate_reconciliation_record(actual)
    policy_faults=[]
    for name in ['source','audit','target','old_peer','new_peer','old_digest','new_digest','raw','native_inventory']:
        bad=copy.deepcopy(actual)
        if name=='source':bad['source']['summary_sha256']='0'*64
        elif name=='audit':bad['audit']['summary_sha256']='0'*64
        elif name=='target':bad['replacement']['target']='case/circuit.cir'
        elif name=='old_peer':bad['replacement']['original_peer']='runtime/patched-ngspice'
        elif name=='new_peer':bad['replacement']['published_peer']='checkpoints/state'
        elif name=='old_digest':bad['replacement']['recorded_sha256']='0'*64
        elif name=='new_digest':bad['replacement']['archived_sha256']='0'*64
        elif name=='raw':bad['original_raw']['payload_sha256']='0'*64
        else:bad['actual']['runtime/patched-ngspice']['sha256']='0'*64
        try:storage.validate_reconciliation_record(bad)
        except AssertionError:policy_faults.append(name)
        else:raise AssertionError('Invalid metadata policy accepted: '+name)
    original=b'original initialization';published=b'published initialization'
    raw=b'header\n'+b'native-payload'*100
    source=dict(bytes=len(raw),sha256=digest(raw),header_bytes=7,payload_bytes=len(raw)-7,payload_sha256=digest(raw[7:]))
    target='storage-initialization-state.json';peer='preallocated-storage-proof/state.json'
    newer='storage-evidence/run-39674830790-attempt-1/preallocated-storage-proof/state.json'
    def fixture(label):
        out=root/label;out.mkdir()
        data={storage.RAW:raw,target:published,peer:original,newer:published,
            'runtime/patched-ngspice':b'native engine','checkpoints/state/pages.img':b'checkpoint pages','result.json':b'original report'}
        for n,b in data.items():p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        recorded={n:digest(b)for n,b in data.items()if n!='result.json'};recorded[target]=digest(original)
        report=dict(outputs=recorded,checkpoint_prefix=source)
        record=dict(source=storage.AUDITED_SOURCE,audit=actual['audit'],recorded_outputs=recorded,original_raw=source,
            actual={n:dict(bytes=len(b),sha256=digest(b))for n,b in data.items()},
            replacement=dict(target=target,original_peer=peer,published_peer=newer,recorded_sha256=digest(original),archived_sha256=digest(published)))
        return out,report,record
    out,report,record=fixture('good')
    proof=storage.reconcile_inventory(out,report,record,source)
    assert (out/target).read_bytes()==original
    assert (out/proof['retained_published_metadata']).read_bytes()==published
    assert (out/newer).read_bytes()==published and (out/peer).read_bytes()==original
    assert (out/storage.RAW).read_bytes()==raw
    rejected=[]
    for name in ['changed-native','changed-checkpoint','changed-old-peer','changed-published-peer','missing-member','extra-member','unsafe-link','wrong-source-proof']:
        out,report,record=fixture(name);verified=source
        if name=='changed-native':(out/'runtime/patched-ngspice').write_bytes(b'changed engine')
        elif name=='changed-checkpoint':(out/'checkpoints/state/pages.img').write_bytes(b'changed pages')
        elif name=='changed-old-peer':(out/peer).write_bytes(b'changed old')
        elif name=='changed-published-peer':(out/newer).write_bytes(b'changed new')
        elif name=='missing-member':(out/peer).unlink()
        elif name=='extra-member':(out/'unexpected').write_bytes(b'extra')
        elif name=='unsafe-link':
            (out/peer).unlink();(out/peer).symlink_to(out/newer)
        else:verified=dict(source,sha256='0'*64)
        try:storage.reconcile_inventory(out,report,record,verified)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Invalid source reconciliation accepted: '+name)
        assert (out/target).read_bytes()==published,'Rejected source was mutated'
    host=root/'host';host.mkdir();(host/'state.json').write_bytes(b'new host state');(host/'logs').mkdir();(host/'logs/x.log').write_bytes(b'new log')
    hr=root/'headroom';hr.mkdir();(hr/'result.json').write_bytes(b'new headroom')
    out=root/'publication';out.mkdir();(out/target).write_bytes(original)
    before=archive.sha(out/target)
    publication=storage.publication_evidence(out,'123','1',host,hr)
    assert archive.sha(out/target)==before
    assert all(archive.sha(out/n)==h for n,h in publication['outputs'].items())
    try:storage.publication_evidence(out,'123','1',host,hr)
    except AssertionError:rejected.append('overwrite-owned-publication')
    else:raise AssertionError('Publication overwrite accepted')
    assert archive.sha(out/target)==before
    return dict(actual_audit_policy_bound=True,rejected_policy=policy_faults,rejected_storage=rejected,
        original_metadata_restored_published_metadata_retained=True,all_native_fixture_bytes_unchanged=True,
        publication_namespace_preserved_original=True,native_activation_performed=False)

if __name__=='__main__':main()
