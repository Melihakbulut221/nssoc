#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect actual saved PLL header in cloud; never activate native simulation."""
import collections,hashlib,json,os,re,tarfile
from pathlib import Path
import cloud_streamed_native_archive as archive
from run_cloud_tx_layout_repair import fetch,sha
import read_pll845_full_native_transient as frozen
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll845-header-review'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);stage=OUT/'parts';stage.mkdir()
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation_allowed=False,full_capture_accepted=False,full_phy_accepted=False)
 try:
  base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39571416471-1-pll845-storage-diagnosis/'
  stem='pll845-storage-diagnosis-39571416471-1'
  fetch(base+stem+'.summary.json','ab2c29b7979ab533abcbae1f0a676009a5d115eef844b19c23ed106d6e93b2fa',OUT/'prior-summary.json')
  fetch(base+stem+'.parts.json','d99458739d8476a4676e9b29b2e7303e47a14a84ff324e3adfc761419f648665',OUT/'prior-parts.json')
  prior=json.loads((OUT/'prior-summary.json').read_text());manifest=json.loads((OUT/'prior-parts.json').read_text())
  assert prior['status']=='FAIL_OR_ERROR' and not prior['whole_archive_verified']
  raw=next(x for x in prior['member_census']if x['path']=='case/actual-acquisition.raw')
  assert raw['sha256']=='17a116d880d748a3bf773f6d8268b16b7fa06c914a19dabbf8439819acb8e88a'
  seen=set();selected={}
  def download(part,path):fetch(base+part['name'],part['sha256'],path)
  with archive.verified_remote_parts(manifest,stage,download)as packed:
   with tarfile.open(fileobj=packed,mode='r|gz')as t:
    for m in t:
     p=Path(m.name);assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==manifest['source_directory']
     assert m.name not in seen and(m.isdir()or m.isfile());seen.add(m.name)
     if m.isfile():
      data=t.extractfile(m).read();assert len(data)==m.size
      rel=str(Path(*p.parts[1:]))
      if rel in ('native-header-prefix.bin','result.json'):
       assert m.size<=frozen.MAX_HEADER
       (OUT/rel.replace('result.json','source-result.json')).write_bytes(data);selected[rel]=hashlib.sha256(data).hexdigest()
  assert selected['result.json']=='ab2c29b7979ab533abcbae1f0a676009a5d115eef844b19c23ed106d6e93b2fa'
  data=(OUT/'native-header-prefix.bin').read_bytes();pos=data.find(frozen.MARKER);assert 0<=pos<frozen.MAX_HEADER
  text=data[:pos+len(frozen.MARKER)].decode('ascii');(OUT/'native-header.txt').write_text(text)
  def field(key):
   xs=[x.split(':',1)[1].strip()for x in text.splitlines()if x.startswith(key+':')]
   assert len(xs)==1;return xs[0]
  assert field('Flags')=='real'and field('Plotname').lower()=='transient analysis'
  table=[x.split()for x in text.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
  width=int(field('No. Variables'));assert len(table)==width and 1<width<=20000
  assert all(len(x)==3 for x in table)and [x[0]for x in table]==list(map(str,range(width)))
  assert table[0]==['0','time','time']and len({x[1]for x in table})==width
  r['header']={'bytes':pos+len(frozen.MARKER),'declared_rows':int(field('No. Points')),'columns':len(table),'expected_original_columns':1695,'matches_original_column_count':len(table)==1695,
    'unit_counts':dict(collections.Counter(x[2]for x in table)),
    'not_wrapped_voltage':[x for x in table[1:]if not (x[2]=='voltage'and re.fullmatch(r'v\([^()\s]+\)',x[1]))],
    'first_vectors':table[:8],'last_vectors':table[-8:]}
  try:frozen.header(OUT/'native-header-prefix.bin')
  except AssertionError as e:r['frozen_reader_rejection']=repr(e)
  else:raise AssertionError('Expected original reader rejection not reproduced')
  r['source_raw_member']=raw;r['source_diagnostic_archive_verified']=True;r['selected_sha256']=selected
  r['scope']='Header observation only. Original full archive scan was incomplete. No payload-value, whole-source-archive, timing, lock or PHY acceptance.'
  r['status']='COMPLETE_ACTUAL_PLL_HEADER_OBSERVATION_ORIGINAL_REJECTION_REPRODUCED'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
