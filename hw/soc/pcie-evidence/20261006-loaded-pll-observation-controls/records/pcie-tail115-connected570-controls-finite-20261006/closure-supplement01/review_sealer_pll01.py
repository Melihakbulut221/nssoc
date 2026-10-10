# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent closed-selector/source review; never opens FIFO or runs producers."""
from pathlib import Path
import hashlib,json,stat
F=Path(__file__).resolve().parent;R=Path.cwd();T=F.parent/'pcie-tail115-connected570-tuning-20261006';C=F.parent/'pcie-tail115-connected570-save-batches-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=F/'snapshot-inputs01.json';assert pin(p)==dict(bytes=102730,sha256='d1d388caf91c3a2ac05e7fd3c93132ce2f8cd44a79ab47cccca0e8763d1487ed')
s=json.loads(p.read_text());assert len(s['files'])==379 and sum(x['bytes']for x in s['files'].values())==37170830
for name,value in s['files'].items():
 q=Path(name);assert q.is_relative_to(R) and stat.S_ISREG(q.lstat().st_mode) and pin(q)==value,name
 assert 'native03'not in q.parts and q.name not in ('campaign03.json','controller03.log','pcie-570-launch03.log')
for e in s['closed_empty_fifo_metadata']:
 q=Path(e['path']);assert stat.S_ISFIFO(q.lstat().st_mode)
 o=q.parent/'owned-processes.json';assert pin(o)==e['owned_processes'];d=json.loads(o.read_text());assert d['status']=='CANCELLED'
 for child in d['processes']:assert child['status']=='FAILURE_REAPED' and child['returncode']is not None and not Path('/proc',str(child['identity']['pid'])).exists()
assert len(s['closed_empty_fifo_metadata'])==9
counts={}
for root,folder,n in [(T,'finite-controls05',11),(T,'storage-controls04',23),(T,'lifecycle-controls04',7),(C,'native-control01',8)]:
 d=json.loads((root/folder/'result.json').read_text());assert d['cases']==n and len(d['outcomes'])==n and all(x['passed'] for x in d['outcomes']);counts[folder]=n
assert sum(counts.values())==49
names=['prepare_snapshot01.py','prepare_snapshot02.py','seal_finite01.py','complete_finite01.py']
sources={n:(F/n).read_text()for n in names}
assert "rel.parts[0]=='native03'"in sources[names[1]] and "stat.S_ISREG(p.lstat().st_mode)"in sources[names[1]]
seal=sources['seal_finite01.py'];complete=sources['complete_finite01.py']
assert 'for name,value in originals.items()'in seal and 'assert seen==members'in seal and 'for p,v in originals.items():assert pin(p)==v,p'in seal
assert "guard()"in seal and "resource.RLIMIT_AS)[0]<=2*1024**3"in seal and "=={10}"in seal
assert "authenticated_roundtrip"in complete and "anonymous_roundtrip"in complete and "seen==json.loads"in complete
assert all(name in complete for name in ('method_allowlist','compact_evidence','original_evidence'))
receipt=dict(status='PASS_SOURCE_ONLY_CLOSED570_FINITE_SELECTOR_AND_SEALER',snapshot=pin(p),methods={n:pin(F/n)for n in names},reviewer_method=pin(__file__),findings=[],closed_files=379,closed_bytes=37170830,closed_fifo_metadata=9,current_control_composition=counts,all_native03_bytes_excluded=True,scope='Full four source bodies and closed selector pins read; exact copied-byte archive census/full readback/post-hash plus immutable publication gates reviewed. No selector, sealer, control, EDA or network executed.',required_dispatch='Both seal and completion require external CPU10/2GiB/256MiB finite-folder cap, entry/continuous/terminal 512MiB shared and1GiB SSD floor checks. External dispatcher is a separate gate; this receipt does not approve an unseen wrapper.',no_physics_acceptance=True)
q=F/'sealer-source-peer-pll01.json';assert not q.exists();q.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(receipt=pin(q),counts=counts)))
