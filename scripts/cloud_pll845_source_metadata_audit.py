#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read every byte of the exact PLL source archive without native activation.

Compare archived bytes with the controller's earlier output manifest. Preserve
publication metadata discrepancies; do not waive or repair any mismatched file.
"""
import hashlib,io,json,os,subprocess,tarfile
from pathlib import Path,PurePosixPath
import cloud_streamed_native_archive as archive
from route_cloud_newer_postcts import fetch
OUT=Path('cloud-pll845-source-metadata-audit')
RAW='case/actual-acquisition.raw'
SOURCE=dict(run='39674830790',attempt='1',stage='initial',
 summary_sha256='95f6e3053f2484af8ba2eab954b6d5f3536cc20898226a8f5c95f0f81df0b243',
 parts_sha256='9194f7614fea02517754431ea85873afdbd60782a270d1d69d9eb68eb461eb36')
def sha(b):return hashlib.sha256(b).hexdigest()
def scan(packed,report,summary_sha):
 prefix=report['checkpoint_prefix'];actual={};contents={};seen=set();raw_proof=None
 with tarfile.open(fileobj=packed,mode='r|gz')as tar:
  for m in tar:
   p=PurePosixPath(m.name)
   assert not p.is_absolute()and '..'not in p.parts and p.parts[0]=='cloud-pll845-native-acquisition'
   assert m.name not in seen and(m.isfile()or m.isdir());seen.add(m.name)
   if not m.isfile():continue
   name='/'.join(p.parts[1:]);assert name
   h=hashlib.sha256();payload=hashlib.sha256();size=0;small=bytearray()
   keep=('storage' in name or 'headroom' in name)and m.size<=524288
   with tar.extractfile(m)as f:
    while block:=f.read(archive.CHUNK):
     h.update(block)
     if name==RAW:
      start=max(0,prefix['header_bytes']-size)
      if start<len(block):payload.update(block[start:])
     if keep:small.extend(block)
     size+=len(block)
   assert size==m.size
   actual[name]=dict(bytes=size,sha256=h.hexdigest())
   if keep:contents[name]=small.decode(errors='replace')
   if name==RAW:
    raw_proof=dict(bytes=size,sha256=h.hexdigest(),header_bytes=prefix['header_bytes'],
     payload_bytes=size-prefix['header_bytes'],payload_sha256=payload.hexdigest())
    assert raw_proof==prefix,'Original native raw/payload identity failed'
 assert raw_proof is not None
 assert actual['result.json']['sha256']==summary_sha,'Archived summary differs'
 expected=report['outputs']
 missing=sorted(set(expected)-set(actual));extra=sorted(set(actual)-set(expected)-{'result.json'})
 mismatches={n:dict(recorded_sha256=d,archived_sha256=actual[n]['sha256'],bytes=actual[n]['bytes'])
  for n,d in expected.items()if n in actual and actual[n]['sha256']!=d}
 # Identify exact byte-equivalent tracked peers as evidence, never as a waiver.
 for name,item in mismatches.items():
  item['matching_recorded_paths']=[n for n,d in expected.items()if d==item['archived_sha256']]
  item['matching_archived_paths']=[n for n,d in actual.items()if d['sha256']==item['archived_sha256']]
 return dict(original_raw=raw_proof,missing=missing,extra=extra,mismatches=mismatches,
  actual=actual,storage_metadata_contents=contents,
  every_source_output_matches=not missing and not mismatches,
  native_activation_permitted=False,full_capture_accepted=False)
def controls():
 payload=b'head\n'+bytes(range(256))*3
 prefix=dict(bytes=len(payload),sha256=sha(payload),header_bytes=5,payload_bytes=len(payload)-5,payload_sha256=sha(payload[5:]))
 meta=b'original';overlay=b'published'
 report=dict(checkpoint_prefix=prefix,outputs={RAW:sha(payload),'storage-initialization-state.json':sha(meta),'storage-evidence/run-39674830790-attempt-1/state.json':sha(overlay),'runtime/native':sha(b'engine')})
 summary=json.dumps(report).encode()
 def packed(change=None,omit=None,unsafe=False):
  files={RAW:payload,'storage-initialization-state.json':overlay,'storage-evidence/run-39674830790-attempt-1/state.json':overlay,'runtime/native':b'engine','result.json':summary}
  if change:files.update(change)
  if omit:del files[omit]
  stream=io.BytesIO()
  with tarfile.open(fileobj=stream,mode='w:gz')as tar:
   for name,data in files.items():
    info=tarfile.TarInfo(('evil/../'if unsafe else'cloud-pll845-native-acquisition/')+name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
  stream.seek(0);return stream
 good=scan(packed(),report,sha(summary))
 assert set(good['mismatches'])=={'storage-initialization-state.json'}and not good['every_source_output_matches']
 assert good['mismatches']['storage-initialization-state.json']['matching_recorded_paths']==['storage-evidence/run-39674830790-attempt-1/state.json']
 changed=scan(packed({'runtime/native':b'changed'}),report,sha(summary))
 assert 'runtime/native'in changed['mismatches']and not changed['native_activation_permitted']
 missing=scan(packed(omit='runtime/native'),report,sha(summary));assert missing['missing']==['runtime/native']
 faults=[]
 for label,handle in [('changed_raw',packed({RAW:payload[:-1]+b'!'})),('changed_summary',packed({'result.json':summary+b' '})),('unsafe_member',packed(unsafe=True))]:
  try:scan(handle,report,sha(summary))
  except AssertionError:faults.append(label)
  else:raise AssertionError('Accepted '+label)
 return dict(status='PASS_SOURCE_AUDIT_CONTROLS_NOT_SOURCE_ACCEPTANCE',archive=archive.controls(),
  detected_metadata_overlay=True,detected_changed_native=True,detected_missing_native=True,rejected=faults)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,
  full_phy_accepted=False,native_activation_permitted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['controls']=controls();save()
  base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39674830790-1-pll845-native-acquisition-initial/'
  stem='pll845-native-acquisition-initial-39674830790-1'
  for suffix,digest in [('summary',SOURCE['summary_sha256']),('parts',SOURCE['parts_sha256'])]:
   fetch(base+stem+'.'+suffix+'.json',digest,OUT/(suffix+'.json'))
  report=json.loads((OUT/'summary.json').read_text());manifest=json.loads((OUT/'parts.json').read_text())
  assert report['run_id']==SOURCE['run']and report['run_attempt']==SOURCE['attempt']and report['stage']==SOURCE['stage']
  assert report['status']=='SAVED_ACTUAL_PHYSICAL845_ONE_US_PROCESS_NOT_FULL_CAPTURE_OR_ACCEPTANCE'and report['checkpoint_saved']
  assert manifest['source_directory']=='cloud-pll845-native-acquisition'
  stage=Path(os.environ['RUNNER_TEMP'])/'pll845-source-audit-part';stage.mkdir(exist_ok=False)
  def download(row,path):fetch(base+row['name'],row['sha256'],path)
  with archive.verified_remote_parts(manifest,stage,download)as stream:
   proof=scan(stream,report,SOURCE['summary_sha256'])
  assert not list(stage.iterdir());stage.rmdir()
  r['archive_verified']=dict(bytes=manifest['bytes'],sha256=manifest['sha256'],parts=len(manifest['parts']))
  r['audit']=proof
  r['status']='COMPLETE_SOURCE_ARCHIVE_AUDIT_REQUIRES_EXPLICIT_METADATA_RECONCILIATION'if not proof['every_source_output_matches']else'PASS_COMPLETE_SOURCE_ARCHIVE_AND_OUTPUT_MANIFEST'
  r['sources_unchanged']=True
 except BaseException as e:r.update(status='FAIL_SOURCE_ARCHIVE_AUDIT',error=repr(e));raise
 finally:save();print(json.dumps({k:r.get(k)for k in ['status','error','archive_verified']}),flush=True)
if __name__=='__main__':main()
