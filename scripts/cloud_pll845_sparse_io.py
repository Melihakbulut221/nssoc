#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Production sparse working file with an immutable ordinary native archive source.

Only stopped processes may be inspected or published. Every source byte and
every current logical payload byte is checked. A sparse working file is never
passed to the full-waveform reader.
"""
import copy,hashlib,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path,PurePosixPath
import cloud_streamed_native_archive as archive
import cloud_logical_native_archive as logical
import cloud_native_sparse_prefix_store as sparse
from route_cloud_newer_postcts import fetch
RAW='case/actual-acquisition.raw'
STATE='sparse-source.json'
FIELDS=('bytes','sha256','header_bytes','payload_bytes','payload_sha256')
FORMAT='pll845-immutable-archive-sparse-source-v1'
_CACHE={}
def source_url(spec):
    assert set(spec)=={'run','attempt','stage','summary_sha256','parts_sha256'}
    assert str(spec['run']).isdigit()and str(spec['attempt']).isdigit()
    assert spec['stage']in ('initial','continuation')
    group='pll845-native-acquisition-'+spec['stage']
    stem=group+'-'+str(spec['run'])+'-'+str(spec['attempt'])
    return 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(spec['run'])+'-'+str(spec['attempt'])+'-'+group+'/',stem
def native_stopped():
    names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines()
    return not any(n.startswith('nssoc-pll-full-')for n in names)
def source_member_chunks(manifest,staging,download,member,size):
    """Consume the whole verified archive, even when the member precedes its end."""
    archive.validate_manifest(manifest)
    expected=manifest['source_directory']+'/'+logical.relative_name(member)
    assert type(size)is int and size>0
    staging=Path(staging);staging.mkdir(exist_ok=False)
    found=False;seen=set()
    with archive.verified_remote_parts(manifest,staging,download)as packed:
        with tarfile.open(fileobj=packed,mode='r|gz')as tar:
            for entry in tar:
                p=PurePosixPath(entry.name)
                assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==manifest['source_directory']
                assert entry.name not in seen,'Duplicate native archive member'
                seen.add(entry.name)
                assert entry.isfile()or entry.isdir(),'Unexpected native capsule type'
                if entry.name!=expected:continue
                assert not found and entry.isfile()and entry.size==size,'Wrong native source member size/type'
                found=True;remaining=size
                with tar.extractfile(entry)as f:
                    while data:=f.read(archive.CHUNK):
                        remaining-=len(data);assert remaining>=0
                        yield data
                    assert remaining==0
        assert found,'Missing immutable raw member'
    # Only a successfully exhausted verified iterator may remove its owned staging.
    assert not list(staging.iterdir());staging.rmdir()
def state(out):
    s=json.loads((Path(out)/STATE).read_text())
    assert s['format']==FORMAT and s['member']==RAW
    sparse.source_contract(s['source']);sparse.validate_plan(s['plan'],s['source'])
    archive.validate_manifest(s['manifest'])
    url,stem=source_url(s['checkpoint'])
    assert s['url']==url and s['manifest']['stem']==stem
    assert s['manifest']['source_directory']==Path(out).name
    return s
def open_source(out):
    s=state(out);parent=Path(out).parent
    stage=parent/('pll845-source-read-'+os.urandom(12).hex())
    def download(row,path):fetch(s['url']+row['name'],row['sha256'],path)
    return source_member_chunks(s['manifest'],stage,download,s['member'],s['source']['bytes'])
def restore(manifest,staging,root,download,report,spec,url,out):
    source=report['checkpoint_prefix'];sparse.source_contract(source)
    assert report['outputs'][RAW]==source['sha256']
    proof=logical.extract_sparse(manifest,staging,root,download,
        {RAW:dict(source=source,head_keep=2*1024**2,tail_keep=4*1024**2)})
    out=Path(out);raw=out/RAW
    assert raw.stat().st_size==source['bytes']
    assert archive.sha(out/'result.json')==spec['summary_sha256']
    reconciliation=reconcile_source_metadata(out,report,spec,source)
    # materialize() has already checked the entire raw and payload SHA256.
    # Do not hash zero-filled holes as though they were original waveform data.
    for name,digest in report['outputs'].items():
        if name==RAW:continue
        assert archive.sha(out/name)==digest,('Changed source capsule file',name)
    saved=dict(format=FORMAT,member=RAW,checkpoint=spec,url=url,source=source,
        manifest=manifest,plan=proof['plans'][RAW],restore=proof,metadata_reconciliation=reconciliation)
    (out/STATE).write_text(json.dumps(saved,indent=2)+'\n')
    assert state(out)==saved
    return dict(source=source,restore=proof,metadata_reconciliation=reconciliation,logical_source_stays_immutable=True,
        ordinary_full_raw_not_allocated=True,full_capture_accepted=False)
def snapshot(out,stop_check=native_stopped):
    out=Path(out);raw=out/RAW
    assert stop_check()is True,'Native process must be stopped before logical inspection'
    s=state(out);key=(sparse.identity(raw),archive.sha(out/STATE))
    if key not in _CACHE:
        proof=sparse.inspect_logical(raw,open_source(out),s['plan'],s['source'])
        assert stop_check()is True and key==(sparse.identity(raw),archive.sha(out/STATE))
        _CACHE.clear();_CACHE[key]=proof
    sparse.unchanged_hole(raw,s['plan'],s['source'])
    assert stop_check()is True
    return copy.deepcopy(_CACHE[key])
def contract(out,stop_check=native_stopped):
    p=snapshot(out,stop_check);return {k:p[k]for k in FIELDS}
def preserved(out,prior):
    s=state(out);assert s['source']==prior
    assert snapshot(out)['original_payload_preserved']
    return True
def hash_outputs(out):
    out=Path(out);result={}
    for p in out.rglob('*'):
        if not p.is_file()or p==out/'result.json':continue
        name=p.relative_to(out).as_posix()
        result[name]=snapshot(out)['sha256']if name==RAW else archive.sha(p)
    return result
def logical_member(out):
    s=state(out)
    return {RAW:dict(source=s['source'],plan=s['plan'],open_source=lambda:open_source(out))}

RECONCILIATION='scripts/pll845-source-publication-reconciliation.json'
AUDITED_SOURCE=dict(run='39674830790',attempt='1',stage='initial',
 summary_sha256='95f6e3053f2484af8ba2eab954b6d5f3536cc20898226a8f5c95f0f81df0b243',
 parts_sha256='9194f7614fea02517754431ea85873afdbd60782a270d1d69d9eb68eb461eb36')
def reconcile_inventory(out,report,record,verified_source):
    """Restore one original metadata path from its archived identical peer.

    Every archive file is first checked against an independently audited exact
    inventory. Native/raw/model/checkpoint bytes cannot be substituted here.
    """
    out=Path(out);raw_identity=sparse.identity(out/RAW)
    assert record['source']==AUDITED_SOURCE
    assert record['audit']['run']==39743545709
    assert record['audit']['summary_sha256']=='7e42f3c0e44c3bcedada9d6b4fe1327df365c86c88e36346b439a29e37b35222'
    assert report['outputs']==record['recorded_outputs']
    assert verified_source==record['original_raw']==report['checkpoint_prefix']
    actual=record['actual']
    files={p.relative_to(out).as_posix():p for p in out.rglob('*')if p.is_file()}
    assert set(files)==set(actual),'Uninventoried or missing source member'
    for name,p in files.items():
        assert not p.is_symlink()and p.resolve().is_relative_to(out.resolve())
        assert p.stat().st_size==actual[name]['bytes'],('Source member size changed',name)
        got=verified_source['sha256']if name==RAW else archive.sha(p)
        assert got==actual[name]['sha256'],('Audited archive member changed',name)
    target='storage-initialization-state.json'
    original='preallocated-storage-proof/state.json'
    published='storage-evidence/run-39674830790-attempt-1/preallocated-storage-proof/state.json'
    old=record['replacement']['recorded_sha256'];new=record['replacement']['archived_sha256']
    # Exact known archive metadata discrepancy only, with both byte-identical peers.
    differences={n for n,d in report['outputs'].items()if actual[n]['sha256']!=d}
    assert differences=={target}
    assert report['outputs'][target]==report['outputs'][original]==actual[original]['sha256']==old
    assert actual[target]['sha256']==actual[published]['sha256']==report['outputs'][published]==new
    assert record['replacement']==dict(target=target,original_peer=original,published_peer=published,recorded_sha256=old,archived_sha256=new)
    evidence=out/'publication-metadata-reconciliation/source-39674830790-attempt-1'
    evidence.mkdir(parents=True,exist_ok=False)
    retained=evidence/'published-storage-initialization-state.json'
    shutil.copyfile(out/target,retained)
    assert archive.sha(retained)==new
    shutil.copyfile(out/original,out/target)
    assert archive.sha(out/target)==old and archive.sha(out/original)==old and archive.sha(out/published)==new
    for name,digest in report['outputs'].items():
        got=verified_source['sha256']if name==RAW else archive.sha(out/name)
        assert got==digest,('Original source output not restored exactly',name)
    assert sparse.identity(out/RAW)==raw_identity,'Reconciliation touched native raw'
    proof=dict(source=record['source'],audit=record['audit'],replacement=record['replacement'],
        retained_published_metadata=retained.relative_to(out).as_posix(),
        original_all_output_hashes_restored=True,all_archived_files_verified_before_change=True,
        native_model_checkpoint_raw_unchanged=True,original_archive_unchanged=True)
    (evidence/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof
def reconcile_source_metadata(out,report,spec,verified_source):
    normalized=dict(spec,run=str(spec['run']),attempt=str(spec['attempt']))
    if normalized!=AUDITED_SOURCE:return dict(applied=False,reason='Not the exact audited historical publication')
    record=json.loads((Path(__file__).resolve().parents[1]/RECONCILIATION).read_text())
    validate_reconciliation_record(record)
    proof=reconcile_inventory(out,report,record,verified_source)
    return dict(applied=True,proof=proof)
def publication_evidence(out,run,attempt,host=None,headroom=None):
    """Create new owned evidence; never overwrite a controller-recorded path."""
    assert str(run).isdigit()and str(attempt).isdigit()
    out=Path(out);dest=out/('storage-publication/run-'+str(run)+'-attempt-'+str(attempt))
    assert not dest.exists(),'Publication evidence may not be overwritten'
    dest.mkdir(parents=True,exist_ok=False)
    host=Path(host)if host is not None else Path(os.environ['RUNNER_TEMP'])/'nssoc-pll845-preallocated-storage'
    headroom=Path(headroom)if headroom is not None else Path.cwd()/'cloud-pll-storage-headroom'
    def copy_one(src,dst):
        assert src.is_file()and not src.is_symlink()
        dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists()
        before=archive.sha(src);shutil.copyfile(src,dst)
        assert archive.sha(src)==archive.sha(dst)==before
    if (host/'state.json').exists():copy_one(host/'state.json',dest/'state.json')
    for srcroot,target in [(host/'logs',dest/'logs'),(headroom,dest/'headroom')]:
        if not srcroot.exists():continue
        assert srcroot.is_dir()and not srcroot.is_symlink()
        for src in sorted(srcroot.rglob('*')):
            assert not src.is_symlink()
            if src.is_file():copy_one(src,target/src.relative_to(srcroot))
    hashes={p.relative_to(out).as_posix():archive.sha(p)for p in dest.rglob('*')if p.is_file()}
    proof=dest/'manifest.json'
    proof.write_text(json.dumps(dict(run=str(run),attempt=str(attempt),outputs=hashes,
        separate_owned_namespace=True,controller_recorded_paths_not_overwritten=True),indent=2)+'\n')
    hashes[proof.relative_to(out).as_posix()]=archive.sha(proof)
    return dict(path=dest.relative_to(out).as_posix(),outputs=hashes)

def validate_reconciliation_record(record):
    assert record['source']==AUDITED_SOURCE
    assert record['audit']==dict(run=39743545709,source_head='6ec4e7d61ee04b554dc1b46d65e35426d9d39472',
        summary_sha256='7e42f3c0e44c3bcedada9d6b4fe1327df365c86c88e36346b439a29e37b35222',
        parts_sha256='eb24e15a1e5ffa8fd7d7984c9f66e6a874ba373cc92ce826174c87f92d899706')
    assert record['replacement']==dict(target='storage-initialization-state.json',
        original_peer='preallocated-storage-proof/state.json',
        published_peer='storage-evidence/run-39674830790-attempt-1/preallocated-storage-proof/state.json',
        recorded_sha256='8ad8d2e9c198aa484bf88d63ee2d3787135f193b4f99f3671121f5f04363513c',
        archived_sha256='7e96ec47f82a937f3ec1cf4b06ef038452c7136718255b3931adb63f9e3c2577')
    assert record['original_raw']==dict(bytes=116738387899,
        sha256='609bdad347f007b894fc0a08fe8ad89bf0ad2e29ea27a1b295d685c7411777f0',
        header_bytes=196539,payload_bytes=116738191360,
        payload_sha256='dc95861a8b7dc0ecb8094bab865e11464de99994d9fc7d73adba90c1b547c375')
    expected=record['recorded_outputs'];actual=record['actual']
    assert set(expected).issubset(actual)
    assert {n for n,d in expected.items()if actual[n]['sha256']!=d}=={'storage-initialization-state.json'}
    assert actual['result.json']['sha256']==AUDITED_SOURCE['summary_sha256']
    assert actual[RAW]['sha256']==expected[RAW]==record['original_raw']['sha256']
    assert actual[RAW]['bytes']==record['original_raw']['bytes']
    return True
