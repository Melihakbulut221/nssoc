# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# This fragment is included literally in the complete reviewed driver.
def capture(source,out,rows,c):
 expected=n.vectors(rows,c['extra_vectors'])
 seen=bytearray()
 class HeaderPrefix:
  def readline(self,limit):
   line=source.readline(limit);seen.extend(line);return line
 try:
  header,meta=life.tiny.parse_header(HeaderPrefix(),expected)
  require(meta['declared_points']==0 and sys.byteorder=='little','NativeFIFO format')
  require(len(header)<=HEADER_CAP,'Bounded native header')
  meter=Meter(meta['columns'],rows,c);width=len(meta['columns'])*8
  require(width==1134*8,'Exact570 full raw row width')
 except BaseException as error:
  # The exact inherited parser reads at most 65535+4097 header bytes.
  # Preserve even a rejected early header, but never consume unread FIFO data.
  require(len(seen)<=65536+4097,'Inherited parser bounded failed header')
  blob=gzip.compress(bytes(seen),mtime=0);free,_=guard(out,len(blob),terminal_tail=True)
  with(out/'wave.raw.gz').open('xb',buffering=0)as dst:
   left=blob
   while left:
    count=dst.write(left);require(count is not None and count>0,'Complete failed-header write progress');left=left[count:]
   dst.flush();os.fsync(dst.fileno())
  n.common.atomic(out/'capture-failure.json',dict(status='FAILED_HEADER_PREFIX_RETAINED',error=repr(error),received_raw_bytes=len(seen),received_raw_sha256=hashlib.sha256(seen).hexdigest(),failure_shared_free_bytes=free,resumable_solver_checkpoint=False))
  raise
 del seen
 raw_limit=MAX_ROWS*width+HEADER_CAP+64
 pending=bytearray();whole=hashlib.sha256(header);payload=hashlib.sha256()
 compressor=zlib.compressobj(level=6,wbits=31);raw_bytes=len(header);queued=b'';flushed=False
 with(out/'wave.raw.gz').open('xb',buffering=0)as dst:
  def write(blob):
   nonlocal queued
   require(not queued,'No overwritten queued compressed bytes')
   queued=blob;guard(out,len(blob))
   while queued:
    count=dst.write(queued);require(count is not None and count>0,'Complete compressed write progress');queued=queued[count:]
  try:
   write(compressor.compress(header))
   while raw:=source.read(65536):
    whole.update(raw);raw_bytes+=len(raw)
    write(compressor.compress(raw));pending.extend(raw)
    require(raw_bytes<=raw_limit,'Bounded native raw bytes including header and adaptive samples')
    count=len(pending)//width
    if count:
     blob=bytes(pending[:count*width]);payload.update(blob)
     meter.push(np.frombuffer(blob,'<f8').reshape(count,-1));del pending[:count*width]
   tail=compressor.flush();flushed=True;write(tail);dst.flush();os.fsync(dst.fileno())
  except BaseException as error:
   # Preserve every byte already read, including a queued compressed block and
   # zlib's buffered tail. This is a failed finite prefix, never a resumable
   # solver checkpoint or a valid complete waveform.1MiB is reserved for it.
   tail=queued+(b''if flushed else compressor.flush());queued=b'';flushed=True
   require(len(tail)<=FAILED_TAIL_RESERVE,'Bounded gzip failure tail')
   failure_shared_free,_=guard(out,len(tail),terminal_tail=True)
   failure_ssd_free=shutil.disk_usage(B).free
   tail_left=tail
   while tail_left:
    count=dst.write(tail_left);require(count is not None and count>0,'Complete failed-tail write progress');tail_left=tail_left[count:]
   dst.flush();os.fsync(dst.fileno())
   n.common.atomic(out/'capture-failure.json',dict(status='FAILED_CAPTURE_PREFIX_RETAINED',error=repr(error),received_raw_bytes=raw_bytes,received_raw_sha256=whole.hexdigest(),complete_rows_reduced=meter.count,pending_bytes=len(pending),failed_tail_bytes=len(tail),failure_shared_free_bytes=failure_shared_free,failure_ssd_free_bytes=failure_ssd_free,failed_only_reserved_finalization=True,resumable_solver_checkpoint=False))
   raise
 require(bytes(pending)==str(meter.count).encode(),'Exact native sample-count trailer')
 safety,data,grid=meter.finish()
 digest,total=hashlib.sha256(),0
 with gzip.open(out/'wave.raw.gz','rb')as src:
  while part:=src.read(1024**2):
   guard(out);digest.update(part);total+=len(part)
 require(total==raw_bytes and digest.hexdigest()==whole.hexdigest(),'Lossless gzip all-byte replay')
 guard(out)
 return dict(columns=meta['columns'],raw_table=meta['raw_table'],rows=meter.count,values=meter.count*len(meta['columns']),raw_bytes=raw_bytes,raw_sha256=whole.hexdigest(),payload_sha256=payload.hexdigest(),safety=safety,measurement=measurement(data,c),time_grid=grid,compression_readback=True,storage=dict(filesystem='SSD',per_point_bytes=POINT_LIMIT,aggregate_bytes=AGGREGATE_LIMIT,maximum_rows=MAX_ROWS,raw_limit_bytes=raw_limit,file_fsync_at_close=True,live_power_loss_tail_durable=False,resumable_solver_checkpoint=False))
