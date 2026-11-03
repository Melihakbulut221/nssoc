# SPDX-License-Identifier: Apache-2.0
"""Bound release asset sizes without omitting any native archive bytes."""
import hashlib,json,tempfile
from pathlib import Path
def pin(path):
 path=Path(path)
 with path.open("rb")as f:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def partition(archive,limit=1800000000):
 archive=Path(archive);assert limit>0
 original=pin(archive)
 if original["bytes"]<=limit:return [archive],None
 parts=[];expected=[];remaining=original["bytes"]
 with archive.open("rb")as source:
  while remaining:
   target=archive.with_name(archive.name+".part"+format(len(parts),"04d"));count=min(remaining,limit)
   h=hashlib.sha256();size=0
   with target.open("xb")as out:
    while size<count:
     block=source.read(min(1024*1024,count-size));assert block
     assert out.write(block)==len(block);h.update(block);size+=len(block)
   want=dict(bytes=size,sha256=h.hexdigest());assert pin(target)==want
   parts.append(target);expected.append(dict(name=target.name,**want));remaining-=count
  assert not source.read(1)
 joined=hashlib.sha256();total=0
 for part in parts:
  with part.open("rb")as stream:
   for block in iter(lambda:stream.read(1024*1024),b""):joined.update(block);total+=len(block)
 assert dict(bytes=total,sha256=joined.hexdigest())==original
 assert pin(archive)==original and sum(p["bytes"]for p in expected)==original["bytes"]
 report=dict(format="ordered-byte-parts-v1",archive_name=archive.name,archive=original,part_limit=limit,parts=expected,
   joined_bytes_independently_verified=True,no_native_archive_bytes_omitted=True)
 archive.unlink()
 return parts,report
def controls():
 rows=[]
 with tempfile.TemporaryDirectory(prefix="nssoc-archive-transport-")as directory:
  for size in(1,199,200,201,450):
   data=bytes((i*37+i//13)%256 for i in range(size));path=Path(directory)/("archive"+str(size));path.write_bytes(data)
   parts,report=partition(path,200);joined=b"".join(p.read_bytes()for p in parts)
   assert joined==data and all(p.stat().st_size<=200 for p in parts)
   if size>200:
    assert report and not path.exists()
    assert hashlib.sha256(b"".join(p.read_bytes()for p in reversed(parts))).hexdigest()!=report["archive"]["sha256"]
    assert hashlib.sha256(joined[:-1]).hexdigest()!=report["archive"]["sha256"]
   else:assert report is None and parts==[path]
   rows.append(dict(bytes=size,parts=len(parts),complete_byte_roundtrip=True,order_and_truncation_faults_rejected=size>200))
 return dict(cases=rows,native_electrical_or_physical_evidence=False)
