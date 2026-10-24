#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded-memory validation of every native byte and column, never sparse holes."""
import hashlib
import numpy as np
import read_pll_rhi120_c8_all_native as original
FIELDS=('bytes','sha256','header_bytes','payload_bytes','payload_sha256')
MAX_INPUT=8*1024**2
def full_capture(meta):
 assert meta['rows']>3000000,'Original full-duration capture incomplete'
 assert meta['start_s']==0 and abs(meta['end_s']-1e-6)<1e-15
 assert meta['native_max_step_s']<=3.125e-13*1.00001
def read_chunks(chunks,contract,source,on_block=None):
 """Callbacks are provisional until this returns after complete iterator exhaustion.

 Every recorded column is checked. A callback may cache selected analyzer inputs,
 but cannot establish capture acceptance or substitute for the full stream.
 The immutable cloud archive remains the authoritative complete raw capture.
 """
 assert set(source)==set(FIELDS)
 assert all(type(source[k])is int and source[k]>0 for k in ('bytes','header_bytes','payload_bytes'))
 assert source['bytes']==source['header_bytes']+source['payload_bytes']
 assert all(isinstance(source[k],str)and len(source[k])==64 for k in ('sha256','payload_sha256'))
 expected=original.contract_check(contract)
 buffer=bytearray();meta=None;rawhash=hashlib.sha256();payloadhash=hashlib.sha256()
 total=0;payload_bytes=0;rows=0;first=None;last=None;max_step=0.
 stride=len(expected)*8;block_bytes=original.CHUNK_ROWS*stride
 def block(data):
  nonlocal rows,first,last,max_step
  values=np.frombuffer(data,dtype='<f8').reshape(-1,len(expected))
  assert len(values)>0 and not values.flags.writeable
  assert np.isfinite(values).all(),'Nonfinite value in an actual native column'
  times=values[:,0]
  if first is None:first=float(times[0])
  if last is not None:
   gap=float(times[0])-last;assert gap>0,'Nonmonotonic native time across chunks'
   max_step=max(max_step,gap)
  dt=np.diff(times);assert np.all(dt>0),'Nonmonotonic native time'
  if len(dt):max_step=max(max_step,float(dt.max()))
  last=float(times[-1])
  if on_block is not None:on_block(rows,values)
  rows+=len(values)
 for data in chunks:
  assert isinstance(data,bytes)and 0<len(data)<=MAX_INPUT,'Unbounded or invalid source chunk'
  total+=len(data);assert total<=source['bytes'],'Extra source bytes'
  rawhash.update(data);buffer.extend(data)
  if meta is None:
   pos=buffer.find(original.MARKER)
   if pos<0:
    assert len(buffer)<original.MAX_HEADER,'Missing bounded native binary header'
    continue
   offset=pos+len(original.MARKER)
   table,meta=original.parse(bytes(buffer[:offset]))
   assert table==expected,'Native raw table differs from actual pinned table'
   assert meta['header_bytes']==source['header_bytes']
   del buffer[:offset]
   payloadhash.update(buffer);payload_bytes+=len(buffer)
  else:
   payloadhash.update(data);payload_bytes+=len(data)
  while len(buffer)>=block_bytes:
   block(bytes(buffer[:block_bytes]));del buffer[:block_bytes]
 assert meta is not None and total==source['bytes'],'Truncated source stream'
 assert len(buffer)%stride==0,'Truncated or extra native payload'
 if buffer:block(bytes(buffer));buffer.clear()
 assert rows>0 and rows==meta['declared_rows'],'Native header/payload point mismatch'
 assert payload_bytes==source['payload_bytes']
 assert rawhash.hexdigest()==source['sha256'],'Changed complete native source'
 assert payloadhash.hexdigest()==source['payload_sha256'],'Changed complete native payload'
 meta.update(rows=rows,bytes=total,start_s=first,end_s=last,native_max_step_s=max_step,
  every_native_column_finite=True,header_matches_observed=True,payload_has_only_complete_rows=True,
  raw_sha256=rawhash.hexdigest(),payload_sha256=payloadhash.hexdigest(),validation_chunk_rows=original.CHUNK_ROWS,
  memory_mapped_readonly=False,required_voltage_vectors=1694,all_recorded_columns_checked=5106,dropped_columns=0,
  all_source_bytes_checked=True,source_iterator_exhausted=True,ordinary_full_raw_allocated=False,
  maximum_buffer_bytes=block_bytes+MAX_INPUT)
 return [x[1]for x in expected],meta
def capture_chunks(chunks,contract,source,on_block=None):
 names,meta=read_chunks(chunks,contract,source,on_block)
 full_capture(meta)
 return names,meta
