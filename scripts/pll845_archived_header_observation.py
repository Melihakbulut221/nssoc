#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Specific archived PLL header observation; not a final waveform reader."""
import collections,hashlib,json,tarfile
from pathlib import Path
import cloud_streamed_native_archive as archive
from run_cloud_tx_layout_repair import fetch,sha
MAX_HEADER=2*1024**2
MARKER=b'Binary:\n'
HEADER_SHA='44cef9ce591b2c6bb87ba9416e78a4da9f233666e0169d2bcb3bd0e469084577'
def header(data):
 assert isinstance(data,bytes)
 pos=data.find(MARKER);assert 0<=pos<MAX_HEADER
 raw=data[:pos+len(MARKER)];text=raw.decode('ascii')
 def field(key):
  xs=[x.split(':',1)[1].strip()for x in text.splitlines()if x.startswith(key+':')]
  assert len(xs)==1,('Missing or duplicate field',key)
  return xs[0]
 assert field('Flags')=='real'and field('Plotname').lower()=='transient analysis'
 assert text.count('Variables:\n')==1
 width=int(field('No. Variables'));rows=int(field('No. Points'))
 table=[x.split()for x in text.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
 assert width==5106 and len(table)==width and rows==0
 assert all(len(x)==3 for x in table)and [x[0]for x in table]==list(map(str,range(width)))
 names=[x[1]for x in table];assert len(set(names))==width and table[0]==['0','time','time']
 assert collections.Counter(x[2]for x in table)==dict(time=1,voltage=5088,current=17)
 assert all((x[1].startswith('v(')and x[1].endswith(')'))if x[2]=='voltage'else(x[1].startswith('i(')and x[1].endswith(')'))for x in table[1:])
 assert len(raw)==196539 and hashlib.sha256(raw).hexdigest()==HEADER_SHA,'Different native archived header'
 return names,dict(header_bytes=len(raw),declared_rows=rows,columns=width,header_sha256=HEADER_SHA,
  unit_counts=dict(time=1,voltage=5088,current=17),original_1695_column_contract_matches=False,
  diagnostic_only=True,all_terminal_values_audited=False)
def qualify(out):
 out=Path(out);out.mkdir();stage=out/'parts';stage.mkdir()
 base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39580323368-1-pll845-header-review/'
 stem='pll845-header-review-39580323368-1'
 fetch(base+stem+'.summary.json','3a7216a9e65f5ef330395a61cc198ace08f30f8949d2bff09dcc0c0495f500d9',out/'summary.json')
 fetch(base+stem+'.parts.json','863c7b65a2fd41aabc6dcd8d738edec87ee79290cba9056b9605505c5acc5477',out/'parts.json')
 report=json.loads((out/'summary.json').read_text());m=json.loads((out/'parts.json').read_text())
 assert report['status']=='COMPLETE_ACTUAL_PLL_HEADER_OBSERVATION_ORIGINAL_REJECTION_REPRODUCED'
 def download(part,path):fetch(base+part['name'],part['sha256'],path)
 data=None;seen=set()
 with archive.verified_remote_parts(m,stage,download)as packed:
  with tarfile.open(fileobj=packed,mode='r|gz')as t:
   for member in t:
    p=Path(member.name);assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==m['source_directory']
    assert member.name not in seen and(member.isdir()or member.isfile());seen.add(member.name)
    if member.isfile():
     b=t.extractfile(member).read();assert len(b)==member.size
     rel=str(Path(*p.parts[1:]))
     if rel=='native-header.txt':
      assert hashlib.sha256(b).hexdigest()==report['outputs'][rel]==HEADER_SHA
      data=b
 assert data is not None
 names,meta=header(data);assert len(names)==5106
 faults={
 'missing_binary_marker':data.replace(MARKER,b'BinaryX\n'),
 'duplicate_width_field':data.replace(b'Variables:\n',b'No. Variables: 5106\nVariables:\n'),
 'wrong_plot':data.replace(b'Transient Analysis',b'Operating Point'),
 'wrong_real_format':data.replace(b'Flags: real',b'Flags: complex'),
 'incorrect_voltage_unit':data.replace(b'voltage',b'current',1),
 'truncated_header':data[:-2],
 'wrong_archived_identity':data.replace(b'v(avdd)',b'v(xvdd)',1),
 'changed_width':data.replace(b'No. Variables: 5106',b'No. Variables: 1695')
 }
 rejected=[]
 for label,bad in faults.items():
  assert bad!=data,label
  try:header(bad)
  except (AssertionError,ValueError):rejected.append(label)
  else:raise AssertionError('Accepted header corruption '+label)
 (out/'native-header.txt').write_bytes(data)
 return dict(actual_archived_header_sha256=HEADER_SHA,metadata=meta,source_run=39580323368,
  verified_diagnostic_archive=True,rejected=rejected,full_capture_or_acquisition_accepted=False)
