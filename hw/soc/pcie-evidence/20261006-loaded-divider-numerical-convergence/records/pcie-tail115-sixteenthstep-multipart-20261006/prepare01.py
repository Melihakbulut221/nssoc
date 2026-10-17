# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded byte partition of an immutable archive, with full inverse readback."""
from pathlib import Path
import hashlib,json,os,shutil
B=Path(__file__).resolve().parent;R=Path.cwd()
SOURCE=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006/pcie-vco-v6-divider-tail115-v1-sixteenthstep-06-01.tar.xz'
EXPECTED=dict(bytes=773973792,sha256='70f9431fa42ffd5039a8c4e6dce860a7603b5440a1414e3b2e473387b0db0763')
LIMIT=32*1024**2;CHUNK=1024**2
STEM='pcie-vco-v6-divider-tail115-v1-sixteenthstep-06-01.tar.xz'
def pin(p):
 p=Path(p);assert p.is_file()and not p.is_symlink()
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def verify(manifest,folder):
 assert manifest['part_limit_bytes']>0 and manifest['parts'];offset=0;whole=hashlib.sha256();seen=set()
 for i,row in enumerate(manifest['parts']):
  name=row['name'];assert name==f"{manifest['archive']['name']}.part{i:04d}"and name not in seen and Path(name).name==name;seen.add(name)
  assert row['offset']==offset and 0<row['bytes']<=manifest['part_limit_bytes'];p=folder/name;assert p.is_file()and not p.is_symlink();h=hashlib.sha256();size=0
  with p.open('rb')as f:
   while data:=f.read(CHUNK):whole.update(data);h.update(data);size+=len(data)
  assert size==row['bytes']and h.hexdigest()==row['sha256'];offset+=size
 assert dict(bytes=offset,sha256=whole.hexdigest())=={k:manifest['archive'][k]for k in ['bytes','sha256']}
 return dict(bytes=offset,sha256=whole.hexdigest(),parts=len(seen))
def split(source,folder,limit,stem):
 assert limit>0 and Path(stem).name==stem and not folder.exists();initial=pin(source);folder.mkdir();rows=[];offset=0
 with source.open('rb')as f:
  i=0
  while offset<initial['bytes']:
   size=min(limit,initial['bytes']-offset);name=f'{stem}.part{i:04d}';h=hashlib.sha256();remaining=size
   with (folder/name).open('xb')as out:
    while remaining:
     data=f.read(min(CHUNK,remaining));assert data;out.write(data);h.update(data);remaining-=len(data)
    out.flush();os.fsync(out.fileno())
   rows.append(dict(name=name,offset=offset,bytes=size,sha256=h.hexdigest()));offset+=size;i+=1
  assert not f.read(1)
 manifest=dict(status='EXACT_ORDERED_ARCHIVE_PARTITION_FULL_STREAM_RECONSTRUCTION_PASS',archive=dict(name=stem,**initial),part_limit_bytes=limit,parts=rows,scope='Ordered byte slices of one unchanged tar.xz. Concatenating every listed part in index/offset order reconstructs the exact original archive. Individual parts are not standalone archives.')
 assert verify(manifest,folder)==dict(**initial,parts=len(rows));assert pin(source)==initial;return manifest
if __name__=='__main__':
 assert pin(SOURCE)==EXPECTED and shutil.disk_usage(B).free>EXPECTED['bytes']+1024**3
 manifest=split(SOURCE,B/'parts01',LIMIT,STEM);assert len(manifest['parts'])==24
 (B/'pcie-tail115-sixteenthstep-multipart-manifest01.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (B/'local-reconstruction01.json').write_text(json.dumps(dict(status='PASS_EXACT_MULTIPART_RECONSTRUCTION',method=pin(__file__),source=pin(SOURCE),reconstruction=verify(manifest,B/'parts01')),indent=2)+'\n')
 print(json.dumps(verify(manifest,B/'parts01')))
