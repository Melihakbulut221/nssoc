# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Select closed570 source/control bytes; exclude the active full34ns campaign."""
from pathlib import Path
import hashlib,json,stat
F=Path(__file__).resolve().parent;R=Path.cwd();OUT=F.parent
T=OUT/'pcie-tail115-connected570-tuning-20261006';C=OUT/'pcie-tail115-connected570-save-batches-20261006'
ROOTS=[OUT/'pcie-tail115-pll-structure-20261006',OUT/'pcie-tail115-connected570-source-20261006',T,C]
def pin(p):
 with p.open('rb')as src:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(src,'sha256').hexdigest())
assert not(F/'snapshot-inputs01.json').exists()
peer=json.loads((T/'source-only-peer-root03.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_CLAMPED570_THREE_POINT_DIAGNOSTICS'and peer['freeze']==pin(T/'source-freeze03.json')and peer['findings']==[]
files={};excluded=[]
for root in ROOTS:
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root)
  if '__pycache__'in rel.parts or p.suffix=='.pyc':continue
  if root==T and(rel.parts[0]=='native03'or rel.name in ['campaign03.json','controller03.log']):
   if p.is_file():excluded.append(str(p))
   continue
  if p.is_dir():continue
  assert stat.S_ISREG(p.lstat().st_mode),str(p)
  files[str(p)]=pin(p)
for p in sorted(OUT.glob('pcie-570-*.log')):
 # The controller's open stdout is explicitly excluded even when it is quiet.
 if p.name=='pcie-570-launch03.log':continue
 files[str(p)]=pin(p)
for name in ['Apache-2.0','CC-BY-4.0','CERN-OHL-W-2.0','BSD-3-Clause']:
 p=R/'LICENSES'/(name+'.txt');files[str(p)]=pin(p)
for name in ['prepare_snapshot01.py','seal_finite01.py','complete_finite01.py','NOTICES.txt']:
 p=F/name;files[str(p)]=pin(p)
p=R/'scripts/publish_pcie_native_capture_v4.py';files[str(p)]=pin(p)
record=dict(status='CLOSED_SOURCE_AND_CONTROLS_SNAPSHOT_EXCLUDING_ACTIVE570_NATIVE',files=files,explicit_exclusion=['native03/**','campaign03.json','controller03.log','pcie-570-launch03.log'],currently_excluded=excluded,source_gate=pin(T/'source-only-peer-root03.json'),scope='Closed source composition, source corrections, retained failed02 native and exact49-control composition only. The2ps native demonstrates command format/startup/observation census, never tuning function. No native03 raw or live journals, no570 sign/range/polarity/closed-loop acceptance.')
(F/'snapshot-inputs01.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(files=len(files),bytes=sum(x['bytes']for x in files.values()),snapshot=pin(F/'snapshot-inputs01.json'))))
