# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent complete failed-run archive check; no numerical continuation."""
import hashlib,json,tarfile
from pathlib import Path
B=Path(__file__).resolve().parent;L=B.parent/'pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=L/'terminal-preservation09.json';d=json.loads(p.read_text());a=Path(d['archive']['path']);assert pin(a)=={k:d['archive'][k] for k in ('bytes','sha256')}
mp=L/'terminal-members09.json';assert pin(mp)==d['member_manifest'];members=json.loads(mp.read_text());seen=set();raw_bytes=0;changed=[]
with tarfile.open(a,'r|xz') as tf:
 for m in tf:
  assert m.isfile() and m.name not in seen;seen.add(m.name);raw_bytes+=m.size
  expected={k:members[m.name][k] for k in ('bytes','sha256')};assert dict(bytes=m.size,sha256=hashlib.file_digest(tf.extractfile(m),'sha256').hexdigest())==expected
  original=Path(members[m.name]['original'])
  if not original.exists() or pin(original)!=expected:changed.append(str(original))
assert seen==members.keys() and len(seen)==2392
assert not changed,changed
raw=Path(d['result']['path']);assert pin(raw)=={k:d['result'][k] for k in ('bytes','sha256')}
result=json.loads(raw.read_text());assert result['status']=='ERROR_NATIVE_OR_STREAM_CAPTURE'
failed=raw.parent/'capture/parts/publication-00120.json';assert pin(failed)==d['failed_publication'];assert json.loads(failed.read_text())['status']=='FAIL'
assert d['native_1us_complete'] is False and d['new_native_started'] is False
j=dict(status='PASS_INDEPENDENT_FULL_FAILED_PLL_CAPSULE_READBACK',archive=dict(path=str(a),members=len(seen),raw_member_bytes=raw_bytes,**pin(a)),member_manifest=dict(path=str(mp),**pin(mp)),preservation=dict(path=str(p),**pin(p)),last_actual_simulation_seconds=d['last_actual_simulation_seconds'],original_public_completed_parts=120,later_part120_recovery=pin(B/'recovered-part120-release01.json'),original_result_unmodified=True,findings=[],method=pin(__file__),scope='Preserved incomplete383.288ns run and original publication failure. No1us/acquisition/timestep-comparison/PHY acceptance. Later rawpart upload does not alter original failed result.')
(B/'pcie-pll-max125-publication120-failure-validation-20261006.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
