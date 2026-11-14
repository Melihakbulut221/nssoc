# SPDX-License-Identifier: Apache-2.0
"""Verify sequential restoration of every frozen input; no CAD jobs restarted."""
import pathlib,json,tarfile,hashlib,time
P=pathlib.Path;out=P('out');out.mkdir();root=P('restored');root.mkdir()
def sha(p):
 with P(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
r={'status':'RUNNING','accepted':False,'full_chip_lvs_passed':False};code=1
try:
 assert sha('pkg.tgz')=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
 started=time.monotonic();contract=None;positions={}
 with tarfile.open('pkg.tgz','r|gz') as t:
  for m in t:
   if not m.isfile():continue
   assert m.name not in positions;positions[m.name]=(m.offset_data,m.size)
   if m.name.endswith('/input-contract.json'):
    assert contract is None;contract=json.loads(t.extractfile(m).read());prefix=str(P(m.name).parent)+'/files/'
 assert contract is not None;r['header_scan_seconds']=time.monotonic()-started
 expected={prefix+name:(name,row) for name,row in contract['input_files'].items()};order=[positions[name][0] for name in expected]
 backward=[a-b for a,b in zip(order,order[1:]) if b<a]
 r['prior_lookup_order']={'file_count':len(order),'backward_seeks':len(backward),'cumulative_backward_uncompressed_bytes':sum(backward),'archive_uncompressed_span':max(o+s for o,s in positions.values()),'scope':'Metadata-only seek burden, not measured runtime of previous jobs.'}
 restored={};total=0;started=time.monotonic()
 with tarfile.open('pkg.tgz','r|gz') as t:
  for m in t:
   if m.name not in expected:continue
   assert m.isfile();name,row=expected[m.name];rel=P(name);assert not rel.is_absolute() and '..' not in rel.parts and name not in restored
   dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
   with t.extractfile(m) as src,dest.open('wb') as dst:
    while True:
     data=src.read(1024*1024)
     if not data:break
     digest.update(data);dst.write(data);size+=len(data)
   actual=digest.hexdigest();assert actual==row['sha256'] and size==m.size
   assert sha(dest)==actual,'Written file readback mismatch'
   restored[name]=actual;total+=size
   if len(restored)%500==0:print(json.dumps({'verified_files':len(restored),'bytes':total}),flush=True)
 assert set(restored)==set(contract['input_files'])
 assert restored=={name:row['sha256'] for name,row in contract['input_files'].items()}
 r.update(status='PASS_EXACT_SEQUENTIAL_RESTORE',restore_seconds=time.monotonic()-started,verified_files=len(restored),verified_bytes=total,restored_manifest_sha256=hashlib.sha256(json.dumps(restored,sort_keys=True).encode()).hexdigest(),all_file_hashes_and_written_bytes_verified=True)
 code=0
except Exception as e:r['status']='ERROR';r['error']=type(e).__name__+': '+str(e)
finally:
 (out/'restore-performance.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
raise SystemExit(code)
