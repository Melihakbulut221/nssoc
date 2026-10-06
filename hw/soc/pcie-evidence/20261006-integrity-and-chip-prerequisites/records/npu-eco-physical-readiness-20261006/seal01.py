# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite readiness source/control evidence only; no physical acceptance."""
import hashlib, io, json, tarfile, xml.etree.ElementTree as ET
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze01.json').read_text())
for p,e in f['sources'].items():assert pin(p)==e,p
peer=json.loads((B/'source-saved-peer-root01.json').read_text())
assert peer['status']=='PASS_SOURCE_AND_SAVED_READINESS_PEER_ACTUAL_BOOT_STILL_REQUIRED' and peer['findings']==[]
assert peer['freeze']==pin(B/'source-freeze01.json')
assert peer['actual_blocked_readiness']==json.loads((B/'readiness02.json').read_text())
for n in ['controls01.xml','root-controls01.xml']:
 t=ET.parse(B/n);cases=t.findall('.//testcase');assert len(cases)==47
 assert not t.findall('.//failure') and not t.findall('.//error') and not t.findall('.//skipped')
closed=['readiness-draft01.json','readiness02.json','source-freeze01.json','source-saved-peer-root01.json','controls01.log','controls01.xml','root-controls01.log','root-controls01.xml','ruff01.log','seal01.py']
files={f'methods/{Path(p).relative_to(R)}':Path(p) for p in f['sources']}
files.update({f'evidence/{n}':B/n for n in closed})
files['LICENSES/Apache-2.0.txt']=R/'LICENSES/Apache-2.0.txt'
notices=B/'NOTICES.txt';assert not notices.exists();notices.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: Apache-2.0\n\nFinite source/control evidence for the NPU physical-readiness gate.\n47 author controls and47 independent controls; no new EDA or boot execution.\nActual readiness remains BLOCKED pending strict vendor-model boot completion.\nHistorical binary proofs and native SRAM mapping are reused via explicit pinned\npublic evidence, not duplicated or re-executed in this capsule.\n')
files['NOTICES.txt']=notices
members={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())}
archive=B/'nssoc-npu-eco-readiness-source-controls-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=6) as tf:
 for n,p in sorted(files.items()):
  data=p.read_bytes();info=tarfile.TarInfo(n);info.size=len(data);info.mode=0o444;tf.addfile(info,io.BytesIO(data))
seen=set()
with tarfile.open(archive,'r:xz') as tf:
 for m in tf:
  assert m.isfile() and m.name not in seen and m.name in members
  with tf.extractfile(m) as stream:actual=dict(bytes=m.size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
  assert actual=={k:members[m.name][k] for k in ('bytes','sha256')};seen.add(m.name)
assert seen==set(members)
for n,p in files.items():assert pin(p)=={k:members[n][k] for k in ('bytes','sha256')}
v=dict(status='PASS_FINITE_READINESS_SOURCE_CONTROLS_FULL_ARCHIVE_READBACK_BOOT_STILL_REQUIRED',archive=dict(path=str(archive),**pin(archive)),members=members,member_count=len(members),member_bytes=sum(v['bytes'] for v in members.values()),full_member_readback=True,originals_rehashed=True,source_peer=pin(B/'source-saved-peer-root01.json'),actual_readiness_status='BLOCKED',control_executions=94,distinct_control_predicates=47,new_native_runs=0,scope='Publication preserves the readiness helper only. Does not pass or waive active strictboot or accept physical implementation.')
vp=B/'nssoc-npu-eco-readiness-source-validation-20261006.json';assert not vp.exists();vp.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(archive=pin(archive),validation=pin(vp),members=len(members))))
