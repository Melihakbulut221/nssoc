#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Qualify stream validation against unchanged original16 controls and native prefix."""
import ast,hashlib,json,os,re,traceback
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pll_rhi120_c8_native_columns as columns
import read_pll_rhi120_c8_all_native as original
import read_pll_rhi120_c8_streamed as streamed
ROOT=Path(__file__).resolve().parents[1]
def digest(b):return hashlib.sha256(b).hexdigest()
def identity(data):
 _,meta=original.parse(data[:original.MAX_HEADER]);offset=meta['header_bytes']
 return dict(bytes=len(data),sha256=digest(data),header_bytes=offset,
  payload_bytes=len(data)-offset,payload_sha256=digest(data[offset:]))
def chunks(data):
 # Header, double and row splits deliberately disagree with physical records.
 i=0
 for n in [1,7,4093,65537,131071]:
  if i>=len(data):break
  yield data[i:i+n];i+=n
 while i<len(data):
  yield data[i:i+1024**2];i+=1024**2
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/'cloud-pll-rhi120-c8-stream-reader';out.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_started=False,
  full_capture_accepted=False,acquisition_accepted=False,full_phy_accepted=False)
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pins=json.loads((ROOT/'scripts/pll-rhi120-c8-stream-reader-method.json').read_text())
  assert all(digest((ROOT/p).read_bytes())==h for p,h in pins['protected'].items())
  def assertions(path,function):
   tree=ast.parse(path.read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==function)
   return [ast.dump(n,include_attributes=False)for n in f.body if isinstance(n,ast.Assert)]
  assert assertions(ROOT/'scripts/read_pll_rhi120_c8_all_native.py','capture')==assertions(ROOT/'scripts/read_pll_rhi120_c8_streamed.py','full_capture')
  ref=columns.load_reference(out/'reference');contract=ref['contract'];prefix=ref['prefix']
  before=digest(prefix);r['source_reference']=ref['restore_proof']
  baseline=original.controls(contract,prefix,out/'original-controls')
  calls=[]
  def stream_file(path,c):
   data=Path(path).read_bytes();collected=[]
   names,meta=streamed.read_chunks(chunks(data),c,identity(data),lambda start,a:collected.append(a.copy()))
   values=np.concatenate(collected);assert values.shape==(meta['rows'],5106)
   calls.append(dict(rows=meta['rows'],all5106_columns_checked=True,raw_sha256=meta['raw_sha256']))
   return names,values,meta
  # Test-only substitution: the unchanged original controls execute every
  # positive fixture and corruption against the new byte-stream mechanism.
  original_read=original.read
  with patch.object(original,'read',stream_file):
   after=original.controls(contract,prefix,out/'stream-controls')
  assert original.read is original_read and after==baseline and len(after['controls'])==16
  table,meta=original.parse(prefix);stride=len(table)*8
  rows=(len(prefix)-meta['header_bytes'])//stride
  header,count=re.subn(rb'(?m)^(No. Points:)[^\n]*$',lambda m:m[1]+b' '+str(rows).encode(),prefix[:meta['header_bytes']])
  assert count==1
  data=header+prefix[meta['header_bytes']:meta['header_bytes']+rows*stride]
  fixture=out/'owned-prefix-fixture.raw';fixture.write_bytes(data)
  names,values,oldmeta=original_read(fixture,contract)
  selected=[];newnames,newmeta=streamed.read_chunks(chunks(data),contract,identity(data),lambda start,a:selected.append(a.copy()))
  rebuilt=np.concatenate(selected)
  assert names==newnames and np.array_equal(values.view('<u8'),rebuilt.view('<u8'))
  for k in oldmeta:
   if k!='memory_mapped_readonly':assert oldmeta[k]==newmeta[k],k
  del values;fixture.unlink()
  rejected=[]
  for label in ['wrong-raw-hash','wrong-payload-hash','truncated-stream','late-transport-error','short-prefix-full-capture']:
   source=identity(data)
   def failing():
    yield from chunks(data)
    raise ValueError('Injected verification failure after native member end')
   iterator=chunks(data)
   if label=='wrong-raw-hash':source['sha256']='0'*64
   elif label=='wrong-payload-hash':source['payload_sha256']='0'*64
   elif label=='truncated-stream':iterator=chunks(data[:-1])
   elif label=='late-transport-error':iterator=failing()
   try:
    if label=='short-prefix-full-capture':streamed.capture_chunks(iterator,contract,source)
    else:streamed.read_chunks(iterator,contract,source)
   except (AssertionError,ValueError):rejected.append(label)
   else:raise AssertionError('Accepted corrupt/incomplete stream '+label)
  assert digest(prefix)==before and all(digest((ROOT/p).read_bytes())==h for p,h in pins['protected'].items())
  r.update(status='PASS_ALL5106_STREAM_READER_ORIGINAL16_CONTROLS_AND5_TRANSPORT_GATES_NOT_FULL_CAPTURE',
   original_controls_reproduced=after,transport_controls=rejected,positive_calls=calls,
   actual_prefix_complete_rows=rows,all_actual_prefix_sample_bits_equal=True,
   original_full_capture_assertions_ast_identical=True,sources_unchanged=True,
   original_reader_source_unchanged=True,scope='Bounded reader qualification only. Full1us terminal source and unchanged acquisition/device/PVT gates remain required.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(out)):digest(p.read_bytes())for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
  save();print(r['status'],flush=True)
if __name__=='__main__':main()
