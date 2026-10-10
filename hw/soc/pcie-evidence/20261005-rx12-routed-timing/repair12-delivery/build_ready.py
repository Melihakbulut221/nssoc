# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite closed RX12 delivery allowlist; no staging or native/capture rerun."""
from pathlib import Path
import hashlib,json,datetime
B=Path(__file__).resolve().parent.parent;R=B.parents[3];O=B/'repair12-delivery'
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
files={}
for directory in ['repair12-source','repair12-peer','repair12-continuation01']:
 for p in sorted((B/directory).rglob('*')):
  if p.is_file():assert not p.is_symlink();files[str(p.relative_to(R))]=pin(p)
for name in ['drt_repair12.py','postroute_repair12.py','normalize_repair12.py','replay_repair12.py','proof_gate_repair12.py','detailed_rc_repair12.py']:
 p=B/name;files[str(p.relative_to(R))]=pin(p)
p=Path(__file__);files[str(p.relative_to(R))]=pin(p)
review=json.loads((B/'repair12-peer/publication-review.json').read_text());assert review['status']=='PASS_RX12_COMPLETED_CAPTURE_AND_THREE_IMMUTABLE_PUBLIC_ASSETS_REVIEW'
release=json.loads((B/'repair12-peer/release.json').read_text());assert pin(B/'repair12-peer/release.json')==review['release']
controller=json.loads((B/'repair12-continuation01/result.json').read_text());assert pin(B/'repair12-continuation01/result.json')==review['controller'];assert controller['status']=='COMPLETE_RX12_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
for identity in [controller['controller_identity'],*[row['identity'] for row in controller['stages']]]:
 p=Path('/proc')/str(identity['pid'])/'stat'
 if p.exists():
  f=p.read_text().rsplit(') ',1)[1].split();assert f[19]!=identity['start_ticks'] or f[0]=='Z'
pkg=json.loads((B/'repair12-peer/package.json').read_text());assert pin(Path(pkg['archive']['path']))=={k:pkg['archive'][k] for k in ['bytes','sha256']}
r=dict(status='READY_FINITE_RX12_ROUTE_RC_PROOF_AND_DUAL_PUBLIC_CAPTURE',utc=datetime.datetime.now(datetime.UTC).isoformat(),new_product_source_allowlist={},compact_files=files,compact_file_count=len(files),compact_bytes=sum(p['bytes'] for p in files.values()),archive=pkg['archive'],archive_members=pkg['member_count'],full_readback_review=dict(path=str((B/'repair12-peer/publication-review.json').relative_to(R)),**pin(B/'repair12-peer/publication-review.json')),public_assets=release['assets'],observed_owned_processes_closed=True,measured_nominal_corner_slacks_ns=review['nominal_cell_corner_slacks_ns'],slow_setup_improvement_vs_published11_ns=.088680,limitations=['Slow setup remains−0.521801ns; all nominal holds/recovery/removal positive.','Zero router DRC and same logical netlist are finite standalone byte-receiver results, not full-chip LVS or foundry DRC approval.','NominalRC reused across slow/typical/fast cell libraries; qualified extraction, separate RC corners and full-chip timing remain open.','Default150 byte receiver, not final widePCS/current widepacket receiver.','New originalgold native expansion was not rerun; exact published11 gold pin reused. Saved completed candidate12 proof/10faults/6ports revalidated, not rerun during packaging.'],prior_preservation_dependency='Already published phase21 C21/rx12-preroute and exact source/prerequisite maps; this inventory adds completed finalDRT/RC/review/publication. No active RX13 candidate paths included.',physical_acceptance=False,scope='Finite exact109-file closed working evidence allowlist for root delivery. Out evidence methods only; no new product RTL source. Root owns documentation/license/staging/commit/push. All unique original outputs and prior failed evidence retained.')
p=O/'ready-finite.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p),files=len(files))))
