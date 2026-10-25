#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded last-complete-row observation, retaining a full row plus partial row."""
import math,struct
COLUMNS=5106
TAIL_BYTES=2*8*COLUMNS
def position(size,header_bytes,tail,columns=COLUMNS):
 assert columns==COLUMNS and size>header_bytes
 stride=8*columns;rows,remainder=divmod(size-header_bytes,stride)
 assert rows>0 and len(tail)>=stride+remainder,'Tail misses the last complete row'
 absolute=header_bytes+(rows-1)*stride;index=absolute-(size-len(tail))
 assert 0<=index<=len(tail)-8
 last=struct.unpack('<d',tail[index:index+8])[0]
 assert math.isfinite(last)and last>=0
 return dict(complete_rows=rows,partial_row_bytes=remainder,last_native_time_s=last,
  tail_bytes=len(tail),tail_file_offset=size-len(tail),all_terminal_values_audited=False)
def controls():
 stride=8*COLUMNS;head=b'header\n';row=lambda t:struct.pack('<d',t)+bytes(stride-8)
 full=head+row(0.)+row(1.)+row(2.)
 positive=[];old_window_rejected=[]
 for partial in (0,1,16383,24688,24689,stride-1):
  data=full+b'x'*partial
  result=position(len(data),len(head),data[-TAIL_BYTES:])
  assert result['complete_rows']==3 and result['partial_row_bytes']==partial and result['last_native_time_s']==2.
  positive.append(partial)
  if stride+partial>65536:
   try:position(len(data),len(head),data[-65536:])
   except AssertionError:old_window_rejected.append(partial)
   else:raise AssertionError('Insufficient old tail accepted')
 rejected=[]
 for label,data in [('nan_last_time',head+row(float('nan'))),('negative_time',head+row(-1.)),('no_complete_row',head+b'x')]:
  try:position(len(data),len(head),data[len(head):])
  except AssertionError:rejected.append(label)
  else:raise AssertionError('Invalid complete row accepted')
 assert old_window_rejected and len(rejected)==3
 return dict(columns=COLUMNS,retained_tail_bytes=TAIL_BYTES,positive_partial_byte_counts=positive,
  insufficient65536byte_tail_rejected=old_window_rejected,invalid_time_or_missing_row_rejected=rejected,
  native_or_full_capture_accepted=False)
