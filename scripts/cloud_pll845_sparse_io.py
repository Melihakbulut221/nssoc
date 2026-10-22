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
    # materialize() has already checked the entire raw and payload SHA256.
    # Do not hash zero-filled holes as though they were original waveform data.
    for name,digest in report['outputs'].items():
        if name==RAW:continue
        assert archive.sha(out/name)==digest,('Changed source capsule file',name)
    saved=dict(format=FORMAT,member=RAW,checkpoint=spec,url=url,source=source,
        manifest=manifest,plan=proof['plans'][RAW],restore=proof)
    (out/STATE).write_text(json.dumps(saved,indent=2)+'\n')
    assert state(out)==saved
    return dict(source=source,restore=proof,logical_source_stays_immutable=True,
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
