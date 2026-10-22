#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Qualify lossless sparse reconstruction on the real 5106-column native prefix."""
import hashlib,json,os,re
from pathlib import Path
import numpy as np
import cloud_pll845_native_reader as prepare
import read_pll845_all_native_transient as reader
import cloud_native_sparse_prefix_store as sparse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-sparse-reader'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_capture_accepted=False,
  full_phy_accepted=False,live_native_process_changed=False,real1us_checkpoint_modified=False)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  pins=json.loads((ROOT/'scripts/pll845-sparse-reader-pins.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in pins.items())
  prepare.OUT=OUT/'original-reader';prepare.main()
  original=json.loads((prepare.OUT/'result.json').read_text())
  assert original['sources_unchanged']and original['reader_controls']['native_prefix']['complete_prefix_rows']==46
  assert len(original['reader_controls']['controls'])==16
  contract=json.loads((prepare.OUT/'reader-contract.json').read_text())
  rawsource=prepare.OUT/'header/native-header-prefix.bin'
  original_hash=sha(rawsource)
  assert original_hash=='3281aa1763cd2cbe17010e2939d88f4ca428b9d663c36a9b8bd0a67ea0e16dfb'
  def trial(source,label):
   header=source.read_bytes()[:reader.MAX_HEADER];table,meta=reader.parse(header)
   assert table==reader.contract_check(contract)
   raw=source.read_bytes();payload=raw[meta['header_bytes']:]
   identity=dict(bytes=len(raw),sha256=sha(source),header_bytes=meta['header_bytes'],
    payload_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest())
   def chunks():
    with source.open('rb')as f:
     while data:=f.read(sparse.CHUNK):yield data
   path=OUT/(label+'-sparse.raw')
   head=((meta['header_bytes']+sparse.BLOCK-1)//sparse.BLOCK)*sparse.BLOCK
   plan=sparse.materialize(path,chunks(),identity,head_keep=head,tail_keep=sparse.BLOCK)
   assert plan['hole_stop']-plan['hole_start']>=2*sparse.BLOCK
   observed=sparse.inspect_logical(path,chunks(),plan,identity)
   assert observed['sha256']==identity['sha256']
   restored=OUT/(label+'-restored.raw')
   with restored.open('xb')as f:
    for data in sparse.logical_chunks(path,chunks(),plan,identity):f.write(data)
   assert sha(restored)==identity['sha256']and restored.read_bytes()==raw
   assert sha(source)==identity['sha256']
   return path,restored,dict(source=identity,plan=plan,logical=observed,all_source_bytes_preserved=True)
  native_sparse,native_restored,native_proof=trial(rawsource,'actual-prefix')
  result['actual_prefix']=native_proof
  controls=reader.controls(contract,native_restored.read_bytes(),OUT/'restored-reader-controls')
  assert controls==original['reader_controls']
  result['original16_reader_controls_reproduced']=controls
  # Separate valid short fixture uses only complete recorded rows, as the
  # original reader controls do. Never replace the preserved raw prefix.
  raw=rawsource.read_bytes();table,meta=reader.parse(raw)
  stride=8*len(table);rows=(len(raw)-meta['header_bytes'])//stride;assert rows==46
  head,count=re.subn(rb'(?m)^(No. Points:)[^\n]*$',lambda m:m[1]+b' '+str(rows).encode(),raw[:meta['header_bytes']]);assert count==1
  body=raw[meta['header_bytes']:meta['header_bytes']+rows*stride]
  fixture=OUT/'owned-complete-row-fixture.raw';fixture.write_bytes(head+body)
  names,values,baseline=reader.read(fixture,contract)
  actual=np.frombuffer(body,dtype='<f8').reshape(rows,len(table))
  assert np.array_equal(values,actual);del values
  working,recovered,proof=trial(fixture,'complete-row-fixture')
  try:reader.read(working,contract)
  except AssertionError as error:result['sparse_direct_reader_rejected']=str(error)
  else:raise AssertionError('Sparse file accepted without source reconstruction')
  after_names,after_values,after=reader.read(recovered,contract)
  assert names==after_names and after==baseline and np.array_equal(after_values,actual)
  del after_values
  try:reader.capture(recovered,contract)
  except AssertionError as error:result['short_capture_rejected']=str(error)
  else:raise AssertionError('Short native fixture accepted as original full1us')
  result['complete_row_fixture']=proof
  assert sha(rawsource)==original_hash and all(sha(ROOT/p)==h for p,h in pins.items())
  result.update(status='PASS_NATIVE5106_COLUMN_SPARSE_PREFIX_RECONSTRUCTION_AND_ORIGINAL16_READER_CONTROLS_NOT_FULL1US',
   all5106_columns_bit_exact=True,complete_native_prefix_rows=rows,
   original_partial_payload_bytes_preserved=(len(raw)-meta['header_bytes'])%stride,
   original_native_prefix_unchanged=True,original_reader_source_unchanged=True,
   all5106_column_sparse_reconstruction_qualified=True,original_full1us_capture_qualified=False)
 except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save();print(json.dumps({k:result[k]for k in ('status','error')if k in result}))
if __name__=='__main__':main()
