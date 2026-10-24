#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read every actual PLL raw column against a cloud-verified native table contract."""
import hashlib,json,re
from pathlib import Path
import numpy as np
MARKER=b'Binary:\n';MAX_HEADER=2*1024**2;CHUNK_ROWS=256
def digest(value):
 return hashlib.sha256(json.dumps(value,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def parse(data):
 pos=data.find(MARKER);assert 0<=pos<MAX_HEADER,'Missing bounded native binary header'
 offset=pos+len(MARKER);text=data[:offset].decode('ascii')
 def field(key):
  xs=[x.split(':',1)[1].strip()for x in text.splitlines()if x.startswith(key+':')]
  assert len(xs)==1,('Missing/duplicate native field',key)
  return xs[0]
 assert field('Flags')=='real'and field('Plotname').lower()=='transient analysis'
 width=int(field('No. Variables'));rows=int(field('No. Points'))
 assert width>1 and rows>=0 and text.count('Variables:\n')==1
 table=[x.split()for x in text.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
 assert len(table)==width and all(len(x)==3 for x in table)
 assert [x[0]for x in table]==list(map(str,range(width)))
 assert table[0]==['0','time','time']and len({x[1]for x in table})==width
 # The exact recorded table below, not a permissive name pattern, decides which
 # internal simulator nodes are permitted (including nested flow(...) names).
 assert all(x[2]in('voltage','current')for x in table[1:])
 return table,dict(header_bytes=offset,declared_rows=rows,columns=width)
def contract_check(contract):
 assert contract['source_preparation_run']==39920519407
 assert contract['source_preparation_sha256']=='63c6b8d34ecf277dce223427c72bdb943ed0dc010c80f496d8feb33f268f94dd'
 assert contract['source_header_run']==39925042125
 assert hashlib.sha256((json.dumps(contract,indent=2)+'\n').encode()).hexdigest()=='fc36b8aec35974c35c5dd3f5041f87d6667a0d76e60a3dbac7d47cd8728b79f8'
 table=contract['raw_table'];vectors=contract['required_vectors']
 assert len(table)==5106 and digest(table)==contract['raw_table_sha256']
 assert len(vectors)==len(set(vectors))==1694 and digest(vectors)==contract['required_vectors_sha256']
 assert len({x[1]for x in table})==5106
 mapped={x[1]:(int(x[0]),x[2])for x in table}
 assert all(v in mapped and mapped[v][1]=='voltage'for v in vectors)
 assert contract['required_vector_indices']=={v:mapped[v][0]for v in vectors}
 assert contract['native_terminal_probes']==2737 and contract['all_native_terminal_probes_covered']
 return table
def read(path,contract):
 expected=contract_check(contract);path=Path(path)
 with path.open('rb')as f:table,meta=parse(f.read(MAX_HEADER))
 assert table==expected,'Native raw table differs from actual pinned table'
 payload=path.stat().st_size-meta['header_bytes'];stride=8*len(table)
 assert payload>0 and payload%stride==0,'Truncated or extra native payload'
 rows=payload//stride;assert rows==meta['declared_rows'],'Native header/payload point mismatch'
 values=np.memmap(path,dtype='<f8',mode='r',offset=meta['header_bytes'],shape=(rows,len(table)))
 last=None;max_step=0.
 for start in range(0,rows,CHUNK_ROWS):
  block=values[start:start+CHUNK_ROWS]
  assert np.isfinite(block).all(),'Nonfinite value in an actual native column'
  times=block[:,0]
  if last is not None:
   gap=float(times[0])-last;assert gap>0,'Nonmonotonic native time across chunks'
   max_step=max(max_step,gap)
  dt=np.diff(times);assert np.all(dt>0),'Nonmonotonic native time'
  if len(dt):max_step=max(max_step,float(dt.max()))
  last=float(times[-1])
 with path.open('rb')as f:raw_sha=hashlib.file_digest(f,'sha256').hexdigest()
 meta.update(rows=rows,bytes=path.stat().st_size,start_s=float(values[0,0]),end_s=float(values[-1,0]),
  native_max_step_s=max_step,every_native_column_finite=True,header_matches_observed=True,
  payload_has_only_complete_rows=True,raw_sha256=raw_sha,validation_chunk_rows=CHUNK_ROWS,
  memory_mapped_readonly=True,required_voltage_vectors=1694,all_recorded_columns_checked=5106,
  dropped_columns=0)
 return [x[1]for x in table],values,meta
def capture(path,contract):
 names,values,meta=read(path,contract)
 assert meta['rows']>3000000,'Original full-duration capture incomplete'
 assert meta['start_s']==0 and abs(meta['end_s']-1e-6)<1e-15
 assert meta['native_max_step_s']<=3.125e-13*1.00001
 return names,values,meta
def controls(contract,prefix,out):
 """Use recorded native prefix plus explicit synthetic corruption fixtures."""
 out=Path(out);out.mkdir();table,original=parse(prefix)
 assert table==contract_check(contract)
 stride=8*len(table);rows=(len(prefix)-original['header_bytes'])//stride
 assert rows>2
 source=prefix[:original['header_bytes']]
 def replace_points(head,n):
  result,count=re.subn(rb'(?m)^(No. Points:)[^\n]*$',lambda m:m[1]+b' '+str(n).encode(),head)
  assert count==1;return result
 # Test fixture only: prefix remains unchanged; short capture can never pass
 # capture(). Only complete rows from that preserved prefix enter this fixture.
 path=out/'fixture.raw';body=prefix[original['header_bytes']:original['header_bytes']+rows*stride]
 path.write_bytes(replace_points(source,rows)+body)
 names,values,meta=read(path,contract)
 actual=np.frombuffer(body,dtype='<f8').reshape(rows,len(table))
 assert np.array_equal(values,actual)and names==[x[1]for x in table];del values
 rejected=[]
 try:capture(path,contract)
 except AssertionError:rejected.append('short_actual_prefix_not_full1us')
 else:raise AssertionError('Short actual prefix accepted as full capture')
 native=dict(complete_prefix_rows=rows,all5106_columns_bit_exact=True,
  prefix_partial_bytes=(len(prefix)-original['header_bytes'])%stride,
  source_declared_rows=original['declared_rows'],prefix_sha256=hashlib.sha256(prefix).hexdigest())
 n=CHUNK_ROWS+3;a=np.zeros((n,len(table)),dtype='<f8');a[:,0]=np.arange(n)*3.125e-13
 a[:,1:]=np.arange(1,len(table))[None,:]*1e-6
 head=replace_points(source,n)
 def write(h=head,data=a,tail=b''):path.write_bytes(h+data.tobytes()+tail)
 write();_,values,_=read(path,contract);assert np.array_equal(values,a);del values
 missing=set(contract['required_vector_indices'].values())
 extra_voltage=next(int(x[0])for x in table[1:]if x[2]=='voltage'and int(x[0])not in missing)
 current=next(int(x[0])for x in table[1:]if x[2]=='current')
 required=next(iter(missing))
 for label,row,col,value in [
  ('nan_unrequested_internal_voltage',CHUNK_ROWS,extra_voltage,float('nan')),
  ('inf_recorded_source_current',CHUNK_ROWS,current,float('inf')),
  ('nan_required_terminal',0,required,float('nan')),
  ('nan_last_column',n-1,len(table)-1,float('nan')),
  ('duplicate_time_chunk_boundary',CHUNK_ROWS,0,a[CHUNK_ROWS-1,0]),
  ('reversed_time_final',n-1,0,0.)]:
  bad=a.copy();bad[row,col]=value;write(data=bad)
  try:read(path,contract)
  except AssertionError:rejected.append(label)
  else:raise AssertionError('Accepted '+label)
 required_name=contract['required_vectors'][0].encode()
 extra_name=table[extra_voltage][1].encode();current_name=table[current][1].encode()
 for label,bad in [
  ('missing_required_identity',head.replace(required_name,b'v(missing_required_identity)',1)),
  ('changed_extra_identity',head.replace(extra_name,b'v(unrecognized_extra_identity)',1)),
  ('changed_current_identity',head.replace(current_name,b'i(unrecognized_current)',1)),
  ('wrong_points',replace_points(head,n+1)),
  ('wrong_plot',head.replace(b'Transient Analysis',b'Operating Point')),
  ('wrong_unit',head.replace(b'voltage',b'current',1)),
  ('duplicate_field',head.replace(b'Variables:\n',b'No. Points: 4\nVariables:\n'))]:
  assert bad!=head;write(h=bad)
  try:read(path,contract)
  except AssertionError:rejected.append(label)
  else:raise AssertionError('Accepted '+label)
 for label,tail,trunc in [('extra_payload',b'x',False),('truncated_payload',b'',True)]:
  write(tail=tail)
  if trunc:
   with path.open('r+b')as f:f.truncate(path.stat().st_size-1)
  try:read(path,contract)
  except AssertionError:rejected.append(label)
  else:raise AssertionError('Accepted '+label)
 path.unlink()
 assert len(rejected)==16
 return dict(status='PASS_ACTUAL_PREFIX_ALL_COLUMNS_AND16_CORRUPTION_CONTROLS_NOT_FULL_CAPTURE',
  native_prefix=native,controls=rejected,synthetic_positive_rows=n,columns=5106,
  full1us_capture_accepted=False,lock_or_safety_accepted=False,live_native_process_changed=False)
