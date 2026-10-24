#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted lossless archive qualification, including original native 5106-column bytes."""
import argparse,copy,hashlib,io,json,os,shutil,tarfile
from pathlib import Path
import cloud_logical_native_archive as logical
import cloud_streamed_native_archive as archive
import cloud_native_sparse_prefix_store as sparse
ROOT=Path(__file__).resolve().parents[1]

def digest(data):return hashlib.sha256(data).hexdigest()
def chunks(raw):
    for i in range(0,len(raw),131071):yield raw[i:i+131071]
def identity(raw,header):
    return dict(bytes=len(raw),sha256=digest(raw),header_bytes=header,
        payload_bytes=len(raw)-header,payload_sha256=digest(raw[header:]))
def host_memory(remote,stage,limit):
    def send(path):
        assert len(list(stage.glob('*.tar.gz.part*')))==1
        assert path.stat().st_size<=limit
        data=path.read_bytes();remote[path.name]=data
        return dict(name=path.name,bytes=len(data),sha256=digest(data))
    return send
def controls(out):
    out.mkdir(exist_ok=False)
    old=archive.controls();assert len(old['negative_controls'])==12
    prefix=sparse.controls(out/'original-sparse-controls');assert len(prefix['negative_controls'])==16
    header=b'Title: complete storage fixture\nNo. Points: 0000000000\nBinary:\n'
    raw=header+os.urandom(5*1024*1024+123);expected=identity(raw,len(header))
    immutable=out/'immutable.raw';immutable.write_bytes(raw)
    source=out/'source';source.mkdir();(source/'raw.bin').write_bytes(raw)
    (source/'native-engine').write_bytes(b'owned executable bytes\n');(source/'native-engine').chmod(0o755)
    (source/'sub').mkdir();(source/'sub/circuit.cir').write_text('unchanged native circuit fixture\n')
    (source/'engine-link').symlink_to('native-engine')
    remote={};stage=out/'initial-stage';stage.mkdir();limit=256*1024
    original=archive.stream_pack(source,'original',stage,host_memory(remote,stage,limit),limit)
    def get(row,path):path.write_bytes(remote[row['name']])
    restored=out/'sparse-restore'
    request={'raw.bin':dict(source=expected,head_keep=sparse.BLOCK,tail_keep=sparse.BLOCK)}
    proof=logical.extract_sparse(original,out/'original-download',restored,get,request)
    work=restored/'source';plan=proof['plans']['raw.bin']
    assert (work/'raw.bin').stat().st_blocks*512<len(raw)//2
    append=os.urandom(512*1024+47);new_header=header.replace(b'0000000000',b'0000000234')
    with(work/'raw.bin').open('r+b')as f:
        f.write(new_header);f.seek(0,os.SEEK_END);f.write(append)
    full=new_header+raw[len(header):]+append
    stage=out/'logical-stage';stage.mkdir()
    members={'raw.bin':dict(source=expected,plan=plan,open_source=lambda:chunks(raw))}
    before=logical.inventory(work)
    packed=logical.stream_pack(work,'logical',stage,host_memory(remote,stage,limit),members,lambda:True,limit)
    assert logical.inventory(work)==before
    assert packed['verification']['logical_members']['raw.bin']['sha256']==digest(full)
    joined=b''.join(remote[p['name']]for p in packed['parts'])
    with tarfile.open(fileobj=io.BytesIO(joined),mode='r:gz')as tar:
        member=tar.getmember('source/raw.bin')
        assert member.isfile()and member.sparse is None and not any(k.startswith('GNU.sparse')for k in member.pax_headers)
        assert tar.extractfile(member).read()==full
    restore=archive.extract_verified(packed,out/'logical-download',out/'ordinary-restored',get)
    normal=out/'ordinary-restored/source'
    assert (normal/'raw.bin').read_bytes()==full
    assert (normal/'sub/circuit.cir').read_bytes()==(work/'sub/circuit.cir').read_bytes()
    assert (normal/'native-engine').stat().st_mode&0o111==0o111
    assert (normal/'engine-link').is_symlink()and os.readlink(normal/'engine-link')=='native-engine'
    current=identity(full,len(header))
    sparse_again=logical.extract_sparse(packed,out/'again-download',out/'again',get,
        {'raw.bin':dict(source=current,head_keep=sparse.BLOCK,tail_keep=sparse.BLOCK)})
    logical_again=sparse.inspect_logical(out/'again/source/raw.bin',chunks(full),sparse_again['plans']['raw.bin'],current)
    assert logical_again['sha256']==digest(full)
    rejected=[]
    for name in ('immutable-late-corruption','immutable-truncated','immutable-extra','retained-head-change',
        'retained-tail-change','write-archived-hole','working-truncated','concurrent-raw-mutation',
        'concurrent-other-file-mutation','not-stopped','resumed-during-archive','bad-upload-receipt','failed-upload'):
        trial=out/name;trial.mkdir();body=trial/'work';body.mkdir()
        live=body/'raw.bin';p=sparse.materialize(live,chunks(raw),expected,sparse.BLOCK,sparse.BLOCK)
        other=body/'other.txt';other.write_text('protected\n')
        src=raw
        if name=='immutable-late-corruption':src=raw[:-1]+bytes([raw[-1]^1])
        if name=='immutable-truncated':src=raw[:-1]
        if name=='immutable-extra':src=raw+b'extra'
        if name in ('retained-head-change','retained-tail-change','write-archived-hole'):
            pos={'retained-head-change':len(header)+3,'retained-tail-change':len(raw)-3,'write-archived-hole':p['hole_start']+sparse.BLOCK}[name]
            with live.open('r+b')as f:
                f.seek(pos);b=f.read(1);f.seek(pos);f.write(bytes([b[0]^1]))
        if name=='working-truncated':
            with live.open('r+b')as f:f.truncate(len(raw)-1)
        def source_chunks():
            for i,data in enumerate(chunks(src)):
                if i==3 and name=='concurrent-raw-mutation':
                    with live.open('ab')as f:f.write(b'race')
                if i==3 and name=='concurrent-other-file-mutation':other.write_text('changed\n')
                yield data
        count=0
        def stopped():
            nonlocal count
            count+=1
            return name!='not-stopped'and not(name=='resumed-during-archive'and count>1)
        dest=trial/'stage';dest.mkdir();published={};upload_calls=0
        def send(path):
            nonlocal upload_calls
            upload_calls+=1
            if name=='failed-upload':raise OSError('Injected failed upload')
            r=host_memory(published,dest,limit)(path)
            if name=='bad-upload-receipt':r['sha256']='0'*64
            return r
        try:logical.stream_pack(body,'failed',dest,send,{'raw.bin':dict(source=expected,plan=p,open_source=source_chunks)},stopped,limit)
        except (AssertionError,OSError,ValueError)as error:
            reason=str(error)
            if name=='bad-upload-receipt':assert reason=='Hosted asset identity/size/digest mismatch'and upload_calls==1
            if name=='failed-upload':assert reason=='Injected failed upload'and upload_calls==1
            rejected.append(dict(name=name,reason=reason,upload_calls=upload_calls))
        else:raise AssertionError('Accepted '+name)
        assert not(dest/'failed.parts.json').exists()
        assert live.exists()and other.exists()
        if name in ('bad-upload-receipt','failed-upload'):assert list(dest.glob('failed.tar.gz.part*'))
    for name in ('missing-native-member','wrong-native-source-sha','wrong-whole-archive-sha'):
        bad=copy.deepcopy(original);req=copy.deepcopy(request)
        if name=='missing-native-member':req={'missing.raw':req['raw.bin']}
        if name=='wrong-native-source-sha':req['raw.bin']['source']['sha256']='0'*64
        if name=='wrong-whole-archive-sha':bad['sha256']='0'*64
        try:logical.extract_sparse(bad,out/(name+'-download'),out/(name+'-restored'),get,req)
        except (AssertionError,OSError,ValueError)as error:rejected.append(dict(name=name,reason=str(error)))
        else:raise AssertionError('Accepted '+name)
    assert len(rejected)==16
    assert archive.sha(immutable)==expected['sha256']and archive.sha(source/'raw.bin')==expected['sha256']
    return dict(status='PASS_LOSSLESS_LOGICAL_ARCHIVE_AND16_CONTROLS_PLUS28_ORIGINAL_CONTROLS_NOT_NATIVE_ACTIVATION',
        ordinary_archive_compatible=True,all_current_bytes_preserved=True,header_backpatch_and_partial_tail_preserved=True,
        no_sparse_extensions_or_zero_prefix_exported=True,ordinary_restore=restore,
        second_generation_sparse_restore=sparse_again,logical_reconstructed=logical_again,
        original_archive_controls=old,original_sparse_controls=prefix,new_negative_controls=rejected,
        immutable_source_unchanged=True,full_capture_accepted=False,native_activation_qualified=False,full_phy_accepted=False)

def native_prefix(out):
    import cloud_pll845_native_reader as prepare
    import read_pll845_all_native_transient as reader
    from publish_cloud_results import result_tag
    from migrate_outputs_to_cloud import publish
    from route_cloud_newer_postcts import fetch
    out.mkdir(exist_ok=False)
    prepare.OUT=out/'original-reader';prepare.main()
    original=json.loads((prepare.OUT/'result.json').read_text())
    assert original['sources_unchanged']and len(original['reader_controls']['controls'])==16
    src=prepare.OUT/'header/native-header-prefix.bin'
    assert archive.sha(src)=='3281aa1763cd2cbe17010e2939d88f4ca428b9d663c36a9b8bd0a67ea0e16dfb'
    raw=src.read_bytes();table,meta=reader.parse(raw)
    contract=json.loads((prepare.OUT/'reader-contract.json').read_text())
    assert table==reader.contract_check(contract)and len(table)==5106
    expected=identity(raw,meta['header_bytes']);head=((meta['header_bytes']+sparse.BLOCK-1)//sparse.BLOCK)*sparse.BLOCK
    source=out/'native-prefix-working';source.mkdir()
    plan=sparse.materialize(source/'native.raw',chunks(raw),expected,head,sparse.BLOCK)
    shutil.copy2(prepare.OUT/'reader-contract.json',source/'reader-contract.json')
    stage=out/'hosted-stage';stage.mkdir()
    group='logical-native-prefix-archive';tag=result_tag(group,os.environ)
    packed=logical.stream_pack(source,'logical-native-prefix-'+os.environ['GITHUB_RUN_ID'],stage,
        lambda p:publish(p,tag),{'native.raw':dict(source=expected,plan=plan,open_source=lambda:chunks(raw))},lambda:True,512*1024)
    manifest_receipt=publish(stage/(packed['stem']+'.parts.json'),tag)
    receipts={r['name']:r for r in packed['hosted_receipts']}
    def get(row,path):fetch(receipts[row['name']]['url'],row['sha256'],path)
    proof=archive.extract_verified(packed,out/'native-download',out/'native-restored',get)
    recovered=out/'native-restored/native-prefix-working/native.raw'
    assert recovered.read_bytes()==raw and archive.sha(recovered)==expected['sha256']
    check=reader.controls(contract,recovered.read_bytes(),out/'recovered-reader-controls')
    assert check==original['reader_controls']
    sparse_restore=logical.extract_sparse(packed,out/'sparse-download',out/'sparse-restored',get,
        {'native.raw':dict(source=expected,head_keep=head,tail_keep=sparse.BLOCK)})
    again=out/'sparse-restored/native-prefix-working/native.raw'
    observed=sparse.inspect_logical(again,chunks(raw),sparse_restore['plans']['native.raw'],expected)
    assert observed['sha256']==expected['sha256']and archive.sha(src)==expected['sha256']
    return dict(status='PASS_REAL_GITHUB_LOGICAL_ARCHIVE_NATIVE5106_PREFIX_AND_ORIGINAL16_READER_CONTROLS_NOT_FULL1US',
        source=expected,rows=46,columns=5106,partial_payload_bytes=(len(raw)-meta['header_bytes'])%(8*len(table)),
        manifest=manifest_receipt,archive_sha256=packed['sha256'],archive_parts=len(packed['parts']),
        hosted_receipts=packed['hosted_receipts'],ordinary_restore=proof,sparse_restore=sparse_restore,
        reconstructed_source=observed,reader_controls=check,source_unchanged=True,
        all5106_column_bytes_preserved=True,native_activation_qualified=False,full_capture_accepted=False,full_phy_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['controls','native-prefix'],required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    pins=json.loads((ROOT/'scripts/logical-native-archive-pins.json').read_text())
    assert all(archive.sha(ROOT/k)==v for k,v in pins.items())
    out=ROOT/('cloud-logical-native-archive-'+a.case);out.mkdir(exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=a.case,full_phy_accepted=False)
    try:
        report.update((controls if a.case=='controls'else native_prefix)(out/'work'))
        assert all(archive.sha(ROOT/k)==v for k,v in pins.items());report['sources_unchanged']=True
    except BaseException as error:report.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        report['outputs']={str(p.relative_to(out)):archive.sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k]for k in ('status','error')if k in report}))
if __name__=='__main__':main()
