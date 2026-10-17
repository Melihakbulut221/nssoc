#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Stream a complete native evidence archive into independently verified assets."""
import argparse,copy,hashlib,io,json,os,subprocess,tarfile,tempfile
from pathlib import Path

def verify_parts(manifest,directory):
    assert manifest['format']=='ordered-tar-gzip-parts-v1' and manifest['parts']
    seen=set();whole=hashlib.sha256();total=0
    for i,row in enumerate(manifest['parts']):
        name=row['name'];assert Path(name).name==name and name not in seen and row['index']==i
        assert name==manifest['stem']+'.tar.gz.part'+str(i).zfill(4);seen.add(name)
        path=directory/name;assert path.stat().st_size==row['bytes'] and row['bytes']>0
        part=hashlib.sha256()
        with path.open('rb') as stream:
            while data:=stream.read(4*1024**2):part.update(data);whole.update(data);total+=len(data)
        assert part.hexdigest()==row['sha256'],'Changed evidence part'
    assert total==manifest['bytes'] and whole.hexdigest()==manifest['sha256'],'Changed/incomplete archive ordering'
    return dict(parts=len(seen),bytes=total,sha256=whole.hexdigest(),all_parts_and_combined_bytes_verified=True)

def pack(directory,stem,destination,part_bytes=1024**3):
    assert directory.is_dir() and Path(stem).name==stem and stem not in ('','.','..') and part_bytes>0
    process=subprocess.Popen(['tar','-czf','-','--',directory.name],cwd=directory.parent,stdout=subprocess.PIPE)
    parts=[];whole=hashlib.sha256();total=0;stream=None;used=0
    try:
        while data:=process.stdout.read(4*1024**2):
            whole.update(data);total+=len(data);offset=0
            while offset<len(data):
                if stream is None:
                    name=stem+'.tar.gz.part'+str(len(parts)).zfill(4);stream=(destination/name).open('xb');digest=hashlib.sha256();used=0
                count=min(part_bytes-used,len(data)-offset);piece=data[offset:offset+count];stream.write(piece);digest.update(piece);offset+=count;used+=count
                if used==part_bytes:
                    stream.close();stream=None;parts.append(dict(index=len(parts),name=name,bytes=used,sha256=digest.hexdigest()))
        if stream is not None:
            stream.close();stream=None;parts.append(dict(index=len(parts),name=name,bytes=used,sha256=digest.hexdigest()))
        assert process.wait()==0 and total>0,'Native archive failed'
    finally:
        if stream is not None:stream.close()
        if process.poll() is None:process.kill();process.wait()
    manifest=dict(format='ordered-tar-gzip-parts-v1',stem=stem,source_directory=directory.name,bytes=total,sha256=whole.hexdigest(),parts=parts,part_limit_bytes=part_bytes,
                  meaning='Concatenate strictly in index order; verify every part and combined SHA256 before extracting. No original waveform samples removed.')
    manifest['verification']=verify_parts(manifest,destination)
    (destination/(stem+'.parts.json')).write_text(json.dumps(manifest,indent=2)+'\n');return manifest

def controls():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);source=root/'evidence';source.mkdir();payload=bytes(range(256))*32;(source/'native-wave.bin').write_bytes(payload)
        m=pack(source,'fixture',root,127);assert len(m['parts'])>1
        joined=b''.join((root/r['name']).read_bytes() for r in m['parts'])
        with tarfile.open(fileobj=io.BytesIO(joined),mode='r:gz') as archive:assert archive.extractfile('evidence/native-wave.bin').read()==payload
        bad=[]
        x=copy.deepcopy(m);x['parts']=x['parts'][::-1];bad.append(x)
        x=copy.deepcopy(m);x['parts']=x['parts'][:-1];bad.append(x)
        x=copy.deepcopy(m);x['parts'][0]['sha256']='0'*64;bad.append(x)
        x=copy.deepcopy(m);x['sha256']='0'*64;bad.append(x)
        x=copy.deepcopy(m);x['parts'][0]['name']='../escape';bad.append(x)
        for x in bad:
            try:verify_parts(x,root)
            except (AssertionError,FileNotFoundError):pass
            else:raise AssertionError('Malformed archive manifest accepted')
        p=root/m['parts'][0]['name'];original=p.read_bytes();p.write_bytes(bytes([original[0]^1])+original[1:])
        try:verify_parts(m,root)
        except AssertionError:pass
        else:raise AssertionError('Corrupted evidence part accepted')
    return dict(positive_roundtrip=True,negative_controls=6,all_native_payload_bytes_preserved=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--directory',type=Path);p.add_argument('--stem');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true','Evidence handling executes on hosted runners'
    if a.self_test:print(json.dumps(controls()))
    else:print(json.dumps(pack(a.directory.resolve(),a.stem,Path.cwd())))
