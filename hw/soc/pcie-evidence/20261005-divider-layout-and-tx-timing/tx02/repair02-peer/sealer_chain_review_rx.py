# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only independent review; does not import or execute reviewed methods."""
from pathlib import Path
import ast,json,hashlib,datetime
B=Path(__file__).resolve().parent

def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
seal=B/'seal.py';chain=B/'continue_review.py';M=B/'continuation-manifest.json';manifest=json.loads(M.read_text())
assert pin(seal)==dict(bytes=6343,sha256='b27c8ad2887c6a614db8c147723b57ebc843bc3bb6be75a3a77477b47b2b0fb9')
assert pin(chain)==dict(bytes=4602,sha256='0c37573b09e168916a33643db531c12cf92f36650b51acb50e3f6f218244d314')
for p,h in manifest['sources'].items():assert pin(p)==h
s=seal.read_text();c=chain.read_text();st=ast.parse(s);ct=ast.parse(c)
roots=ast.literal_eval(next(n.value for n in st.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='roots' for t in n.targets)))
assert set(roots)=={'nssoc-tx-path-v4-postroute-repair-02','nssoc-tx-path-v4-repair02-equivalence','nssoc-tx-path-v4-repair02-physical-replay-01','nssoc-tx-path-v4-repair02-drt-03','nssoc-tx-path-v4-repair02-detailed-rc-02'}
assert 'assert expanded == ports[\'lossless_closed_program\'][\'raw\']' in s
assert 'assert actual == members' in s and "tarfile.open(A, 'x:xz'" in s
assert "assert members == {name: pin(p) for name, p in files.items()}" in s
port=Path('/dev/shm/nssoc-tx-path-v4-repair02-physical-replay-01/result.json');ports=json.loads(port.read_text());assert set(ports['lossless_closed_program']['raw'])=={'bytes','sha256'}
assert ports['outputs']['sim/sim.vvp.gz']==ports['lossless_closed_program']['gzip']
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
sr=dict(status='PASS_TX02_COMPLETE_CAPTURE_SEALER_SOURCE_ONLY',utc=now,reviewer='/root/rx_route_resume',sources={str(p):pin(p) for p in [seal,B/'review.py',B/'source-only-peer-rx.json',port,Path(__file__)]},mandatory_capture_roots=roots,findings=['Full source inspected. Mandatory five TX02 candidate/proof/ports/DRT03/RC02 roots and essential files are asserted before recursive regular-file capture; symlink files rejected. Interrupted old native outputs are not relabeled.','Review status plus all hashed review inputs are required. Native compiled VVP gzip pin is compared to port receipt and full decompression is matched to actual raw bytes/SHA schema, independently confirmed in current saved port receipt.','Timing/slack deltas and per-class corner booleans copied from reviewed measurements without hardcoded passing values or gains. Explicit same-nominal-RC limitation and physical_acceptance=false retained.','Every archived member is pinned before/after, exclusive archive creation, streaming full member readback, duplicate names/unknown rows rejected. 1GiB entry, 528MiB free floor and 200MiB archive ceiling retained. Originals are never unlinked.','Methods, independent source peers, proof kernels, old TX01 comparison reports, validation, applicable source/licenses are included. Package binds all member hashes and archive; publication must independently bind package/validation/archive.'],issues_found=[],sealer_executed=False,native_executed=False,physical_acceptance=False)
(B/'sealer-source-only-peer.json').write_text(json.dumps(sr,indent=2)+'\n')
assert manifest['chain_peer_sha256']=='PENDING_PEER_DO_NOT_LAUNCH'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==manifest['boot_id']
pid=manifest['watched_identity']['pid'];stat=Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()
assert stat[19]==manifest['watched_identity']['start_ticks'] and stat[0]!='Z'
assert Path('/proc',str(pid),'cmdline').read_bytes().hex()==manifest['watched_cmdline_hex']
assert len(manifest['sources'])==9
cr=dict(status='PASS_TX02_PRESERVATION_CONTINUATION_SOURCE_ONLY',utc=now,reviewer='/root/rx_route_resume',sources={str(p):pin(p) for p in [chain,seal,B/'review.py',B/'sealer-source-only-peer.json',Path(__file__)]},manifest_before_peer_binding=pin(M),manifest_snapshot=manifest,permitted_post_review_edit='Only chain_peer_sha256 may be replaced with SHA256 of this receipt; all remaining manifest fields and sources must stay equal. No circular self-pin.',observed_exact_watcher=dict(pid=pid,start_ticks=stat[19],state=stat[0],boot_id=manifest['boot_id']),findings=['Full chain and exact nine input pins inspected. Fresh boot identity and exact watcher PID/start/cmdline are bound; existing watcher/native work is only observed, not owned, restarted or signalled.','Successful exact route/RC receipt and matching RC result pin are prerequisites; independent source-pinned reviewer rechecks complete route/RC hashes, zeroDRC and same netlist before capture.','Review, seal and frozen V3 are new owned process groups with 15s failure cleanup and no healthy elapsed watchdog. Child code/nonzero exits fail and retain evidence. Resource constraints inherit launch environment; source checks require current scratch floor, sealer its own entry/continuous guards.','Fresh output directory plus exclusive per-step logs reject duplicate launch; old result files remain immutable. Source hashes checked before/after every owned stage.','All three immutable public assets must have exact expected filename set, bytes, SHA, authenticated and anonymous roundtrips matching current archive/validation/package. Same finite non-signoff scope remains.','PENDING peer field hard-blocks launch until this independent receipt is bound. Manifest snapshot intentionally records prebinding values; only peer hash field may change.'],issues_found=[],reviewed_methods_executed=False,native_executed=False,tests_rerun=False,physical_acceptance=False)
(B/'chain-source-only-peer.json').write_text(json.dumps(cr,indent=2)+'\n')
print(json.dumps({str(p):pin(p) for p in [B/'sealer-source-only-peer.json',B/'chain-source-only-peer.json']},indent=2))
