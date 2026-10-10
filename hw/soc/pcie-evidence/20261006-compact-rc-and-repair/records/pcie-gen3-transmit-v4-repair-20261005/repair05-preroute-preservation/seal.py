# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal closed TX05 proof/nativeports before its separate live detailed route."""
from pathlib import Path
import hashlib,json,tarfile,sys,shutil
R=Path.cwd();O=Path(__file__).resolve().parent;B=O.parent;S=B/'repair05-source'
sys.path.insert(0,str(B));import proof_gate_repair05 as gate

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ['bytes','sha256']},str(p)
assert gate.verify_binding()['status']=='PASS_ACTUAL_TX05_PROOF_AND_MUTATION_EXECUTION_BOUND'
C=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05');P=Path('/dev/shm/nssoc-tx-path-v4-repair05-physical-replay-02')
r=json.loads((C/'result.json').read_text());assert r['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC';assert r['inputs']=={n:pin(n) for n in r['inputs']};assert r['outputs']=={n:pin(C/n) for n in r['outputs']}
p=json.loads((P/'result.json').read_text());assert p['status']=='PASS_EXACT_BOUND_TX05_PHYSICAL_NETLIST_PORT_REPLAY';assert p['tests']==dict(passed=3,failed=0,skipped=0);assert p['inputs']=={n:pin(n) for n in p['inputs']};assert p['outputs']=={n:pin(P/n) for n in p['outputs']}
proof=json.loads((S/'pre-drt-proof-port-review.json').read_text());assert proof['candidate']==pin(C/'repaired.v')
prior=json.loads((B/'repair03-peer/release.json').read_text());assert prior['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
files={}
for root in [C,gate.E,P,Path('/dev/shm/nssoc-tx-path-v4-repair05-physical-replay-01')]:
 for q in root.rglob('*'):
  if q.is_file() and '__pycache__' not in q.parts:assert not q.is_symlink();files['native/'+root.name+'/'+str(q.relative_to(root))]=q
for q in S.iterdir():
 if q.is_file() and q.name!='drt-launch01.log':files['method/repair05-source/'+q.name]=q
for n in ['postroute_repair05.py','normalize_repair05.py','proof_gate_repair05.py','replay_repair05.py','replay_repair05_resume02.py','owned_lifecycle05.py','proof05/compare.py','proof05/mutations.py','drt_repair05.py','detailed_rc_repair05.py']:
 files['method/'+n]=B/n
for n in ['review.json','package.json','release.json','independent-result-peer-rx.json','pcie-tx-repair03-finite-physical-validation-20261005.json']:files['prior-public/TX03/'+n]=B/'repair03-peer'/n
for n in ['LICENSES/Apache-2.0.txt','LICENSES/CERN-OHL-W-2.0.txt','LICENSES/CC-BY-4.0.txt','scripts/check_pcie_integrity.py','scripts/check_pcie_integrity_native.py','scripts/cocotb_results.py','hw/soc/tb/cocotb/test_soc_pcie_gen3_tx_path_v4.py','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_tx_path_v4','hw/soc/rtl/pcie/soc_pcie_gen3_tx_path_v4.v']:files['source/'+n]=R/n
files['method/seal.py']=Path(__file__)
v=dict(status='PRESERVED_TX05_COMPLETE_LOGIC_AND_PORTS_ACTUAL_ROUTE_PENDING',proof=proof,prior_public_assets=prior['assets'],failed_first_ports='Retained environment-onlySREmismatch beforeDUTcompile; rootvenvsymlinkresolve error. Lexicalvenv02 actual3portsPASS, inheritedGPIpathwarning remains.',optimization='ActualTX03SPEF-.601762 loadedbeforefirstrepair,488resize335setup2holdbuffers; finalGRT estimatesonly.',physical_acceptance=False,qualified_rc=False,full_phy_acceptance=False,live_route_included=False,scope='All unique closed candidate,normalization,proof,controls,nativeports and original failures. Existing originalgold expansion reusedbyteexact; source methods included. LiveDRT/native files excluded. Restore completedcapture afterpowerloss; interrupted route restarts fresh.')
vp=O/'pcie-tx-repair05-preroute-validation-20261006.json';assert not vp.exists();vp.write_text(json.dumps(v,indent=2)+'\n');files['validation.json']=vp
notice=O/'NOTICES.txt';notice.write_text('Finite TX05 pre-route development evidence. No actual routed timing, qualified RC, fullPHY or chip acceptance. Project licenses included; generated compiled IHP standard-cell models use the pinned Apache-2.0 PDK functional library. Tool binaries and full PDK sources are not redistributed. Native GPI executable-path warning and failed first launcher retained. Previous public TX03 capsule supplies baseline route and source dependencies. Active detailed routing files excluded.\n');files['NOTICES.txt']=notice
members={n:dict(restore_path=str(q),**pin(q)) for n,q in files.items()};archive=O/'pcie-tx-repair05-preroute-proof-ports-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'x:xz',preset=3) as tar:
 for n,q in files.items():
  assert shutil.disk_usage('/dev/shm').free>=528*1024**2 and archive.stat().st_size<160*1024**2
  tar.add(q,arcname=n,recursive=False)
assert members=={n:dict(restore_path=str(q),**pin(q)) for n,q in files.items()}
seen=set()
with tarfile.open(archive,'r|xz') as tar:
 for m in tar:
  assert m.isfile() and m.name not in seen;seen.add(m.name)
  with tar.extractfile(m) as f:row=dict(bytes=m.size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
  assert row=={k:members[m.name][k] for k in row}
assert seen==set(members)
record=dict(status='PASS_CLOSED_TX05_FULL_MEMBER_READBACK',archive=dict(path=str(archive),**pin(archive)),members=members,member_count=len(members),validation=pin(vp),physical_acceptance=False,live_route_included=False)
(O/'package.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(archive=record['archive'],members=len(members))))
