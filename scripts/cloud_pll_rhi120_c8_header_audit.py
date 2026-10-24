#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audit the actual saved RHI120 capture and column mismatch without native activation."""
import collections,hashlib,json,os,struct,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
import cloud_streamed_native_archive as archive
import read_pll845_all_native_transient as reader
import read_pll845_full_native_op as full_op
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-rhi120-c8-header-audit'
REPO='repos/Melihakbulut221/nssoc/'
RUN=39925042125
SUMMARY='74033b131a40f5009565b1dd6e219f1b6748f555f750b1c715ebbc77ad93be8d'
PARTS='bf1b8dcc19d1b8b31eb6934537f0efe728e7f8a6fd5060d1e1334d22627d436d'
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);stage=Path(os.environ['RUNNER_TEMP'])/'rhi120-audit-parts';stage.mkdir()
 r=dict(status='WAITING_FOR_ORIGINAL_PUBLICATION',source_head=os.environ['GITHUB_SHA'],native_started=False,
  native_activation_allowed=False,whole_archive_verified=False,checkpoint_accepted_for_resume=False,
  full_capture_accepted=False,full_phy_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  deadline=time.monotonic()+3600
  while True:
   run=api('actions/runs/'+str(RUN))
   assert run['head_sha']=='ece94d479509de8fda3ac37ef4f0a4d9856aef85'
   if run['status']=='completed':break
   assert time.monotonic()<deadline,'Original publisher still live; no restart or activation'
   print(json.dumps(dict(waiting_for_run=RUN,status=run['status'])),flush=True);time.sleep(60)
  assert run['conclusion']=='failure'
  r['original_run_conclusion']=run['conclusion']
  base=f'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{RUN}-1-pll-rhi120-c8-native-initial/'
  stem=f'pll-rhi120-c8-native-initial-{RUN}-1'
  fetch(base+stem+'.summary.json',SUMMARY,OUT/'prior-summary.json')
  fetch(base+stem+'.parts.json',PARTS,OUT/'prior-parts.json')
  prior=json.loads((OUT/'prior-summary.json').read_text());manifest=json.loads((OUT/'prior-parts.json').read_text())
  assert prior['status']=='FAIL_OR_ERROR'and prior['error']=='AssertionError()'and prior['checkpoint_saved']
  assert prior['checkpoint_prefix']['sha256']==prior['outputs']['case/actual-acquisition.raw']
  assert prior['zero_source_operating_point']['native_columns']==5105
  r['archive_controls']=archive.controls();r['status']='VERIFYING_COMPLETE_ORIGINAL_ARCHIVE';save()
  seen=set();observed={};selected={};raw_meta=None
  def download(part,path):
   print(json.dumps(dict(read_part=part['index'],of=len(manifest['parts']))),flush=True)
   fetch(base+part['name'],part['sha256'],path)
  with archive.verified_remote_parts(manifest,stage,download)as packed:
   with tarfile.open(fileobj=packed,mode='r|gz')as tar:
    for m in tar:
     p=PurePosixPath(m.name)
     assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==manifest['source_directory']
     assert m.name not in seen and(m.isdir()or m.isfile());seen.add(m.name)
     if not m.isfile():continue
     rel=str(PurePosixPath(*p.parts[1:]));digest=hashlib.sha256();count=0;prefix=b'';tail=b''
     small=rel in ('case/op.raw','result.json','case/boots.log')
     if small:assert m.size<=2*1024**2
     f=tar.extractfile(m)
     while chunk:=f.read(4*1024**2):
      digest.update(chunk);count+=len(chunk)
      if small:prefix+=chunk
      elif rel=='case/actual-acquisition.raw':
       if len(prefix)<reader.MAX_HEADER:prefix=(prefix+chunk)[:reader.MAX_HEADER]
       tail=(tail+chunk)[-256*1024:]
     assert count==m.size
     actual=digest.hexdigest();observed[rel]=actual
     expected=SUMMARY if rel=='result.json'else prior['outputs'][rel]
     assert actual==expected,('Original member changed',rel)
     if small:
      selected[rel]=prefix
      if rel=='case/op.raw':(OUT/'actual-op.raw').write_bytes(prefix)
     if rel=='case/actual-acquisition.raw':
      (OUT/'actual-native-prefix.bin').write_bytes(prefix)
      table,meta=reader.parse(prefix);stride=8*len(table);rows,partial=divmod(m.size-meta['header_bytes'],stride)
      assert rows>1000
      start=meta['header_bytes']+(rows-1)*stride
      offset=start-(m.size-len(tail));assert 0<=offset<=len(tail)-8
      last=struct.unpack('<d',tail[offset:offset+8])[0];assert 0<last<=1e-6
      raw_meta=dict(**meta,complete_rows=rows,partial_row_bytes=partial,last_time_s=last,raw_bytes=m.size,raw_sha256=actual)
  assert observed==dict(prior['outputs'],**{'result.json':SUMMARY})
  assert selected['result.json']==(OUT/'prior-summary.json').read_bytes()
  assert selected['case/boots.log'].decode().splitlines()==['native-entrypoint']
  assert raw_meta is not None
  vectors=prior['preparation']['vectors'];op=selected['case/op.raw']
  op_result=full_op.read(op,vectors);assert op_result==prior['zero_source_operating_point']
  r['all_native_op_controls']=full_op.controls(op,vectors);assert len(r['all_native_op_controls'])==12
  text=op[:op.index(reader.MARKER)].decode('ascii')
  optable=[line.split()for line in text.split('Variables:\n',1)[1].splitlines()]
  assert len(optable)==5105 and all(len(row)==3 for row in optable)
  tran={(row[1],row[2])for row in table[1:]};ops={(row[1],row[2])for row in optable}
  mapped={row[1]:(int(row[0]),row[2])for row in table}
  required_missing=[v for v in vectors if v not in mapped or mapped[v][1]!='voltage']
  r.update(status='COMPLETE_ORIGINAL_ARCHIVE_AND_NATIVE_TABLE_DIAGNOSIS_NOT_RESUME_OR_ACCEPTANCE',
   whole_archive_verified=True,archive_bytes=manifest['bytes'],archive_sha256=manifest['sha256'],
   source_run=RUN,source_summary_sha256=SUMMARY,source_parts_sha256=PARTS,
   observed_member_count=len(observed),every_original_member_hash_verified=True,
   native_position=raw_meta,native_unit_counts=dict(collections.Counter(row[2]for row in table)),
   op_unit_counts=dict(collections.Counter(row[2]for row in optable)),op_columns=len(optable),
   original_width_assertion=(len(table)==len(optable)+1==5106),
   original_op_identity_assertion=(tran==ops),transient_only=sorted(tran-ops),op_only=sorted(ops-tran),
   original_required_vector_assertion=(not required_missing),required_missing=required_missing,
   original_failure_preserved=True,zero_source_op=op_result)
  contract=dict(source_preparation_run=39920519407,source_preparation_sha256='63c6b8d34ecf277dce223427c72bdb943ed0dc010c80f496d8feb33f268f94dd',
   source_header_run=RUN,source_header_sha256=hashlib.sha256((OUT/'actual-native-prefix.bin').read_bytes()[:raw_meta['header_bytes']]).hexdigest(),
   source_summary_sha256=SUMMARY,raw_table=table,raw_table_sha256=reader.digest(table),
   required_vectors=vectors,required_vectors_sha256=reader.digest(vectors),
   required_vector_indices={v:mapped[v][0]for v in vectors if v in mapped},native_terminal_probes=2737,
   all_native_terminal_probes_covered=not required_missing,full_capture_accepted=False)
  (OUT/'observed-column-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
