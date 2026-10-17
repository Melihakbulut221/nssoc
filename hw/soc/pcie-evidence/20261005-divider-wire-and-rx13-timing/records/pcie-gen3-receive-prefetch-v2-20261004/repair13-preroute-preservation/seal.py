# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve only already closed RX13 candidate/proof/port captures; no router files."""
from pathlib import Path
import hashlib,json,shutil,tarfile
R=Path.cwd();B=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004';O=Path(__file__).resolve().parent
A=Path('/dev/shm/pcie-rx-repair13-preroute-proof-ports-20261005.tar.xz')
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
proof=json.loads((B/'repair13-source/pre-drt-proof-port-review.json').read_text());assert proof['canonical_states']==1804 and proof['canonical_targets']==5443 and proof['actual_mutation_controls']==10 and len(proof['actual_port_cases'])==6
old=json.loads((B/'repair12-peer/release.json').read_text());assert old['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in old['assets'])
files={}
for name in ['nssoc-rx-prefetch-v2-postroute-repair-13','nssoc-rx-prefetch-v2-repair13-equivalence','nssoc-rx-prefetch-v2-repair13-physical-replay-01']:
 root=Path('/dev/shm')/name;assert root.is_dir()
 for p in root.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:assert not p.is_symlink();files['native/'+name+'/'+str(p.relative_to(root))]=p
for p in (B/'repair13-source').iterdir():
 if p.is_file() and p.name not in ['drt-launch.log'] and p.suffix in ['.py','.json','.log','.diff']:files['method/repair13-source/'+p.name]=p
for n in ['postroute_repair13.py','normalize_repair13.py','proof_gate_repair13.py','replay_repair13.py','drt_repair13.py','detailed_rc_repair13.py','eco-proof/compare.py','eco-proof/mutations.py']:
 files['method/'+n]=B/n
for n in ['review.json','package.json','release.json','pcie-rx-repair12-finite-physical-validation-20261005.json']:files['prior-published/repair12/'+n]=B/'repair12-peer'/n
for n in ['LICENSES/Apache-2.0.txt','LICENSES/CERN-OHL-W-2.0.txt','scripts/check_pcie_gen3_receive.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_prefetch_v2.v']:files['source/'+n]=R/n
files['method/preroute-seal.py']=Path(__file__).resolve()
validation={'status':'PRESERVED_RX13_CANDIDATE_PROOF_PORTS_BEFORE_COMPLETED_DETAILED_ROUTE','completed_proof_ports':proof,'GRT_estimates_only':json.loads((B/'repair13-source/grt-screen.json').read_text()),'baseline_public_assets':old['assets'],'new_final_detailed_route_completed':False,'changed_design_nominal_RC_completed':False,'qualified_rc':False,'physical_acceptance':False,'scope':'Closed candidate13/GRT/native gate normalization/actual canonical proof and10controls/6nativeports only. Originalgold native expansion reused exactly. In-progress DRT files excluded; no final timing/DRC/fullPHY or mainchip acceptance. On abrupt power loss restore this finite capture instead of rerunning completed proofs/ports; interrupted route would restart fresh from candidate.'}
V=O/'pcie-rx-repair13-preroute-validation-20261005.json';assert not V.exists();V.write_text(json.dumps(validation,indent=2)+'\n');files['validation.json']=V
notice=O/'NOTICES.txt';notice.write_text('Finite pre-route preservation only. No final timing, physical or product acceptance. Project source licenses included. Upstream PDK models and tool binaries are pinned but not redistributed. Completed source and all unique closed native captures preserved; active routing outputs excluded. Previous published RX12 capsule provides source dependencies.\n');files['NOTICES.txt']=notice
members={name:{'restore_path':str(p.resolve()),**pin(p)} for name,p in files.items()}
assert not A.exists() and shutil.disk_usage('/dev/shm').free>=1024**3
minimum=shutil.disk_usage('/dev/shm').free
with tarfile.open(A,'x:xz',preset=3) as tar:
 for name,p in files.items():
  minimum=min(minimum,shutil.disk_usage('/dev/shm').free);assert minimum>=528*1024**2 and A.stat().st_size<70*1024**2;tar.add(p,arcname=name,recursive=False)
assert members=={name:{'restore_path':str(p.resolve()),**pin(p)} for name,p in files.items()}
seen=set()
with tarfile.open(A,'r|xz') as tar:
 for row in tar:
  assert row.isfile() and row.name not in seen;seen.add(row.name);want=members[row.name];assert {'bytes':row.size,'sha256':hashlib.file_digest(tar.extractfile(row),'sha256').hexdigest()}=={k:want[k] for k in ['bytes','sha256']}
assert seen==set(members)
record={'status':'PASS_IMMUTABLE_PREROUTE_FULL_MEMBER_READBACK','archive':{'path':str(A),**pin(A)},'members':members,'member_count':len(members),'minimum_shared_free':minimum,'baseline_public_assets':old['assets'],'source_inputs_after_seal_unchanged':True,'physical_acceptance':False,'qualified_rc':False}
P=O/'pcie-rx-repair13-preroute-package-20261005.json';assert not P.exists();P.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'archive':record['archive'],'member_count':len(members),'package':pin(P)},indent=2))
