# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json
R=Path.cwd();O=Path(__file__).resolve().parent;B=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-eighthstep-20261006';doc=R/'docs/145-pcie-divider-time-step-and-prefix-timing.md'
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
s=doc.read_text();p=json.loads((B/'numerical-policy01.json').read_text());f=json.loads((B/'source-freeze01.json').read_text())
assert f['numerical_predeclaration']==pin(B/'numerical-policy01.json')
assert p['frequency_limit_ppm']==100 and p['phase_limit_ps']==50
assert p['reference_step_s']==1.25e-12 and p['candidate_step_s']==6.25e-13
assert not Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-eighthstep-06-01').exists()
for phrase in ['This closes that one\nfinite nominal test. It does not close numerical convergence','1,079.469 ppm','The first two results remain FAIL.','with no fitted phase\noffset','separately declared\n100 ppm convergence target','Neither diagnostic changes a production\nchecker or converts either failed run into a pass.','distinct from the 1 µs closed-loop PLL acquisition study']:
 assert phrase in s,phrase
r=dict(status='PASS_DOC145_NUMERICAL_POLICY_SCOPE_ONLY',findings=[],document=pin(doc),source_freeze=pin(B/'source-freeze01.json'),predeclaration=pin(B/'numerical-policy01.json'),method=pin(Path(__file__)),eighth_native_absent_at_review=True,reviewed_claims=['1.25ps finite functional PASS is separate from pairwise numerical convergence','5ps and2.5ps FAIL remain unchanged','Actual adjacent frequency1079.469ppm exceeds separate100ppm target','35.272ps CML difference is unaligned; this alone is not pairwise acceptance','Predeclared100ppm frequency and50ps maximum unaligned edge-time criterion applies to future1.25/0.625ps comparison; no old native checker changed','Finite34ns openloop scope does not imply1us PLL, PVT or fullPHY'],scope='Narrow numerical-policy wording review only. RX owns full table/count/V24 factual review. No test/native/producer rerun or document edit.')
(O/'doc145-numerical-policy-peer-vco01.json').write_text(json.dumps(r,indent=2)+'\n');print(pin(O/'doc145-numerical-policy-peer-vco01.json'))
