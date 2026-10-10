# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real SSD file and finite-byte controls; injected floors are explicitly named."""
from pathlib import Path
import copy,errno,gzip,hashlib,io,json,os,resource,shutil,sys
from unittest.mock import patch
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B))
import characterize_clamped570_02 as m
D=B/'storage-controls04'

def main():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 assert not D.exists();D.mkdir();cases=[];oldroot=m.NATIVE_ROOT;m.NATIVE_ROOT=D/'native';m.NATIVE_ROOT.mkdir();p=m.NATIVE_ROOT/'one';p.mkdir();q=m.NATIVE_ROOT/'two';q.mkdir()
 def ok(label,extra=None):cases.append(dict(case=label,passed=True,**(extra or {})))
 def reject(label,call,diagnostic):
  try:call()
  except BaseException as e:assert diagnostic in str(e),(label,repr(e));ok(label,dict(diagnostic=str(e)))
  else:raise AssertionError(label+' was accepted')
 def sparse(file,size):
  with file.open('wb')as f:f.truncate(size)
 try:
  m.guard(p);ok('actual_empty_ssd_point_and_aggregate')
  f=p/'sparse.bin';sparse(f,m.POINT_LIMIT-m.RECEIPT_RESERVE);m.guard(p);ok('actual_sparse_point_exact_reserved_cap')
  reject('actual_sparse_point_one_byte_over',lambda:m.guard(p,1),'Point1280MiB');f.unlink()
  # Three sequential point directories count failed evidence equally.
  sparse(f,1024**3);other=q/'failed-point.bin';sparse(other,m.AGGREGATE_LIMIT-1024**3-m.RECEIPT_RESERVE);m.guard(p);ok('actual_sparse_aggregate_exact_cap_including_failed_other_point')
  reject('actual_sparse_aggregate_one_byte_over',lambda:m.guard(p,1),'Aggregate4GiB');f.unlink();other.unlink()
  link=p/'link';link.symlink_to(D/'absent');reject('actual_dangling_file_link',lambda:m.guard(p),'No linked');link.unlink()
  link=m.NATIVE_ROOT/'linked-root';link.symlink_to(q,target_is_directory=True);reject('actual_directory_link',lambda:m.sampled_bytes(m.NATIVE_ROOT),'No linked');link.unlink()
  os.mkfifo(p/'stream.fifo');m.guard(p);ok('exact_owned_stream_fifo');(p/'stream.fifo').unlink()
  os.mkfifo(p/'wrong.fifo');reject('wrong_special_fifo',lambda:m.guard(p),'Only exact');(p/'wrong.fifo').unlink()
  f.write_bytes(b'closed');regular=m.regular_bytes;attempts=[]
  def transient(path):
   attempts.append(str(path))
   if len(attempts)==1:raise FileNotFoundError(errno.ENOENT,'Actual namespace rescan injection')
   return regular(path)
  with patch.object(m,'regular_bytes',transient):assert m.sampled_bytes(p)==6
  assert len(attempts)==2;ok('one_ENOENT_restarts_complete_tree',dict(attempts=len(attempts)))
  attempts=[]
  def churn(path):attempts.append(str(path));raise FileNotFoundError(errno.ENOENT,'Repeated injected churn')
  with patch.object(m,'regular_bytes',churn):reject('four_complete_ENOENT_attempts_stop',lambda:m.sampled_bytes(p),'Repeated injected churn')
  assert len(attempts)==4
  with patch.object(m,'regular_bytes',side_effect=PermissionError(errno.EACCES,'Injected non-ENOENT')):reject('non_ENOENT_is_fatal',lambda:m.sampled_bytes(p),'Injected non-ENOENT')
  f.unlink();usage=m.shutil.disk_usage
  def disk(free_shared=None,free_ssd=None):
   def probe(path):
    actual=usage(path);free=free_shared if str(path)=='/dev/shm' else free_ssd
    return actual if free is None else actual._replace(free=free)
   return probe
  with patch.object(m.shutil,'disk_usage',disk(free_shared=m.FLOOR-1)):reject('injected_shared_floor_one_byte_low',lambda:m.guard(p),'Shared512MiB')
  with patch.object(m.shutil,'disk_usage',disk(free_ssd=m.SSD_FLOOR+m.RECEIPT_RESERVE-1)):reject('injected_ssd_floor_reserved_tail_one_byte_low',lambda:m.guard(p),'SSD1GiB')
  with patch.object(m.shutil,'disk_usage',disk(free_ssd=m.SSD_FLOOR+m.RECEIPT_RESERVE,free_shared=m.FLOOR)):m.guard(p);ok('injected_both_normal_floors_exact_boundary')
  with patch.object(m.shutil,'disk_usage',disk(free_ssd=m.RECEIPT_RESERVE,free_shared=0)):
   m.guard(p,m.FAILED_TAIL_RESERVE,terminal_tail=True);ok('failed_only_finalization_uses_pre_reserved_tail_despite_floor_trigger')
  reject('failed_tail_cannot_exceed_reservation',lambda:m.guard(p,m.FAILED_TAIL_RESERVE+1,terminal_tail=True),'Reserved failed-tail')
  # Actual production parser/gzip/Meter over a closed finite fixture.
  c,rows,_=m.config(.6);c=copy.deepcopy(c);c.update(stop_s=3*c['step_s'],window_s=[0,3*c['step_s']]);body=(B/'finite-controls01/positive.raw').read_bytes();oldmeasurement=m.measurement;m.measurement=lambda data,c:dict(passed=False,synthetic_transport_only=True)
  try:
   for label in ('short_writes','shared_floor_after_received_block','bad_trailer','bad_header','empty_header','declared_nonzero_points'):
    folder=m.NATIVE_ROOT/label;folder.mkdir();data=body if label!='bad_trailer'else body[:-1]+b'5';
    if label=='bad_header':data=body.replace(b'No. Variables: 1134',b'No. Variables: 1135')
    if label=='empty_header':data=b''
    if label=='declared_nonzero_points':data=body.replace(b'No. Points: 0',b'No. Points: 4')
    stream=io.BytesIO(data)
    if label=='short_writes':
     opening=Path.open;counts=[]
     class Short:
      def __init__(self,f):self.f=f
      def __enter__(self):return self
      def __exit__(self,*args):return self.f.__exit__(*args)
      def write(self,b):counts.append(len(b));return self.f.write(b[:7])
      def flush(self):return self.f.flush()
      def fileno(self):return self.f.fileno()
     def opened(path,*a,**kw):
      f=opening(path,*a,**kw)
      return Short(f)if path==folder/'wave.raw.gz'and a and a[0]=='xb'else f
     with patch.object(Path,'open',opened):result=m.capture(stream,folder,rows,c)
     assert result['rows']==4 and len(counts)>2;ok('actual_partial_FileIO_write_loop',dict(writes=len(counts)))
    elif label=='shared_floor_after_received_block':
     calls=[]
     def low_after_header(path):
      if str(path)=='/dev/shm':
       calls.append(1)
       if len(calls)>=2:return usage(path)._replace(free=0)
      return usage(path)
     with patch.object(m.shutil,'disk_usage',low_after_header):reject('actual_capture_preserves_received_prefix_on_shared_floor_failure',lambda:m.capture(stream,folder,rows,c),'Shared512MiB')
     failure=json.loads((folder/'capture-failure.json').read_text());assert failure['failure_shared_free_bytes']==0 and failure['failed_only_reserved_finalization']
     prefix=data[:stream.tell()];saved=gzip.decompress((folder/'wave.raw.gz').read_bytes());assert saved==prefix and hashlib.sha256(saved).hexdigest()==failure['received_raw_sha256'];assert len(saved)==failure['received_raw_bytes']
    elif label in ('bad_header','empty_header','declared_nonzero_points'):
     reject('actual_'+label+'_received_prefix_retained',lambda:m.capture(stream,folder,rows,c),'NativeFIFO format'if label=='declared_nonzero_points'else'Exact native column census'if label=='bad_header'else'Bounded complete native raw header')
     failed=json.loads((folder/'capture-failure.json').read_text());prefix=data[:stream.tell()]
     assert failed['status']=='FAILED_HEADER_PREFIX_RETAINED'and failed['received_raw_sha256']==hashlib.sha256(prefix).hexdigest()and gzip.decompress((folder/'wave.raw.gz').read_bytes())==prefix
    else:reject('actual_bad_native_trailer_rejected_full_gzip_retained',lambda:m.capture(stream,folder,rows,c),'Exact native sample-count trailer')
    if label not in ('shared_floor_after_received_block','bad_header','empty_header','declared_nonzero_points'):assert gzip.decompress((folder/'wave.raw.gz').read_bytes())==data
  finally:m.measurement=oldmeasurement
 finally:m.NATIVE_ROOT=oldroot
 report=dict(status='PASS_ACTUAL_SSD_CAP_FLOOR_SPECIAL_FILE_AND_FINITE_FAILURE_CONTROLS',cases=len(cases),outcomes=cases,method=m.pin(__file__),producer=m.pin(m.__file__),scope='Actual sparse/file/FIFO/byte operations; injected disk observations and transient errors are explicit. No native simulator or publication. Emergency closure cannot turn exception into PASS. Complete received prefix, not unread FIFO bytes, is retained; finite gzip has fsync only at close and no solver checkpoint.')
 (D/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(result=m.pin(D/'result.json'),cases=len(cases))))
if __name__=='__main__':main()
