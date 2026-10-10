# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,shutil,sys
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent;Q=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-quarterstep-20261006';assert not(B/'source-freeze01.json').exists()
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((Q/'source-freeze01.json').read_text());assert all(pin(p)==v for p,v in f['pins'].items())
c=json.loads((B/'controls01.json').read_text());assert c['status']=='PASS_SAVED_STREAMING_READER_EQUIVALENCE_AND_CORRUPTION_CONTROLS'and len(c['checks'])==20
assert all(pin(p)==v for p,v in c['inputs'].items())
shutil.copyfile(B.parent/'pcie-tail115-streaming-reader-controls01.log',B/'controls01.log')
paths=set(map(Path,f['pins']))|set(map(Path,c['inputs']))|{Q/'source-freeze01.json',Q/'source-only-peer01-root.json'}
paths.update(p for p in B.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc')
numpyroot=Path(np.__file__).resolve().parent
paths.update(p for p in numpyroot.rglob('*')if p.is_file()and p.suffix in{'.py','.so'})
libs=numpyroot.parent/'numpy.libs'
if libs.exists():paths.update(p for p in libs.rglob('*')if p.is_file())
paths.update([R/'hw/soc/tools/cocotb-venv/bin/python',R/'hw/soc/tools/cocotb-venv/pyvenv.cfg'])
r=dict(status='FROZEN_BOUNDED_ANONYMOUS_SSD_RAW_READER_PENDING_SOURCE_PEER',sources={str(p):pin(p)for p in[B/'raw_table01.py',B/'test_reader01.py']},pins={str(p.absolute()):pin(p)for p in sorted(paths)},controls=pin(B/'controls01.json'),scope='Standalone saved-table loader only. Complete existing5/2.5/1.25ps payloads and455safety/measurement/time-grid equal with original verdicts retained; seventeen positive/corruption/floor/cleanup fixtures also executed. Current eighth sealer/comparison and native are untouched. Future adoption requires full derivative bindings to both sealer and comparison helper plus resource review; no0.3125ps native permission from this receipt.',peak_control_rss_kib=c['peak_rss_kib'],resource_contract=dict(AS=2*1024**3,SSD_payload_cap='explicit caller limit; currently1GiB in full saved tests',SSD_floor=1024**3,read_chunk=1024**2,header_cap=4*1024**2,anonymous_mapping=True,read_only=True,no_native_children=True),physical_acceptance=False)
(B/'source-freeze01.json').write_text(json.dumps(r,indent=2)+'\n');print(len(paths),pin(B/'source-freeze01.json'))
