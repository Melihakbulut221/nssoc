# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source review of recovery-aware closed-capture preservation."""
import ast,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
C=Path(__file__).resolve().parent
seen={}
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def check(p,h):
 assert pin(p)=={k:h[k] for k in ('bytes','sha256')},p;seen[str(p)]=pin(p)
p=json.loads((C/'preservation-policy.json').read_text())
assert pin(C/'preservation-policy.json')['sha256']=='a5cf827a511cd6361fe1cb1d97363d1c77db123a0a8e24166e5fe96500caa056'
for path,h in p['pins'].items():check(path,h)
for policy in [C/'policy.json',C.parent/'policy.json']:
 d=json.loads(policy.read_text())
 for path,h in d['pins'].items():check(path,h)
rt=json.loads((C.parent/'runtime-targets-observed01.json').read_text())
for path,h in rt['files'].items():check(path,h)
ledgers=json.loads((C/'preservation-derivation.json').read_text())
for name,d in ledgers.items():
 check(d['before']['path'],d['before']);check(d['after']['path'],d['after']);before=Path(d['before']['path']).read_text();after=Path(d['after']['path']).read_text();s=before
 for c in d['changes']:
  assert s.count(c['before'])==1;s=s.replace(c['before'],c['after'])
 assert s==after
 for c in reversed(d['changes']):
  assert s.count(c['after'])==1;s=s.replace(c['after'],c['before'])
 assert s==before
 olddefs={n.name:ast.dump(n) for n in ast.parse(before).body if isinstance(n,ast.FunctionDef)}
 newdefs={n.name:ast.dump(n) for n in ast.parse(after).body if isinstance(n,ast.FunctionDef)}
 assert olddefs.keys()==newdefs.keys()
 assert all(olddefs[n]==newdefs[n] for n in olddefs if n!='main')
source=(C/'seal.py').read_text();assert 'preservation_peer_root.py' in source and 'preservation-peer-root.log' in source
assert "stage['returncode'] is None" in source and "'unavailable_non_child_orphan'" in source
assert "counts == dict(passed=13, failed=0, skipped=0)" in source
assert "owned['status'] == 'REAPED_NO_LIVE_MEMBERS'" in source
watch=(C/'continue_preservation.py').read_text()
assert 'life.FAILURE_GRACE_SECONDS = 15.0' in watch
assert 'signal.' not in watch and "kind='" not in watch
assert "owner.launch('publisher' if name == 'publish' else 'native'" in watch
assert "all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in release['assets'])" in watch
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['boot_id']
q=Path('/proc')/str(p['controller']['pid']);fields=(q/'stat').read_text().rsplit(')',1)[1].split();assert fields[19]==p['controller']['start_ticks'] and fields[0]!='Z'
r={'status':'PASS_SOURCE_ONLY_V18_MAX4118_RECOVERY_PRESERVATION','utc':datetime.now(timezone.utc).isoformat(),'policy':pin(C/'preservation-policy.json'),'findings':[],'reviewer':'root','method':pin(Path(__file__)),'unique_input_files_rehashed':len(seen),'inputs':seen,'full_forward_and_inverse_derivations':2,'helper_function_ASTs_unchanged':True,'reviewed_contracts':['Original direct wait status explicitly unavailable; functional status derives from exact native helper plus complete13-case XML and pytest assertion XML.','Owned miter requires true waited exit,13-case XML and cycle-miter scope. Neither profile is repeated.','Sealing begins only after exact recovered controller and all original/recovery process births are gone or zombie, never from stale RUNNING.','Every closed member is fully rehashed; original failed preparation and abrupt-owner-loss evidence retained.','Observer does not signal or take ownership of preexisting native jobs. Only its own seal/publisher children use reviewed lifecycle cleanup.','Three unique public assets require exact full hashes and both authenticated/anonymous readback; no overwrite.'],'functional_result_claimed':False,'physical_acceptance':False}
assert not (C/'preservation-source-peer.json').exists();(C/'preservation-source-peer.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(seen),pin(C/'preservation-source-peer.json'))
