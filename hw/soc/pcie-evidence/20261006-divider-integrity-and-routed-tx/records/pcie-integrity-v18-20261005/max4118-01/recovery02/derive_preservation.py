# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive recovery-aware seal and observer; no native, capture or publication run."""
from pathlib import Path
import ast,hashlib,json
C=Path(__file__).resolve().parent;M=C.parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
ledgers={}
for name in ['seal.py','continue_preservation.py']:
 old=M/name;text=old.read_text();changes=[]
 def sub(a,b):
  global text
  assert text.count(a)==1,(name,a,text.count(a));text=text.replace(a,b);changes.append(dict(before=a,after=b))
 sub('B = Path(__file__).resolve().parent','C = Path(__file__).resolve().parent\nB = C.parent')
 if name=='seal.py':
  sub('"""Seal closed MAX4118 attempts, including actual failures; no simulation rerun."""','"""Seal observed orphan direct and owned miter with honest wait provenance."""')
  sub("    status = read(B / 'status.json')", "    status = read(C / 'status.json')")
  sub("    assert status['status'] in {'COMPLETE_PENDING_INDEPENDENT_XML_REVIEW_AND_SEAL',\n                                'FAILED_CASES_RETAINED_PENDING_REVIEW_AND_SEAL'}\n    assert not status['current_descendants']", "    assert status['status'] in {'COMPLETE_TWO_PROFILES_XML_VERIFIED_REQUIRES_RECOVERY_AWARE_SEAL',\n                                'CLOSED_TWO_PROFILES_FAILURE_RETAINED_REQUIRES_RECOVERY_AWARE_SEAL'}\n    assert not status['current_external'] and not status['current_owned']\n    recovery_policy = read(C / 'policy.json')\n    assert recovery_policy['pins'] == {p: pin(p) for p in recovery_policy['pins']}\n    assert status['policy'] == pin(C / 'policy.json')\n    assert status['old_controller_abruptly_lost'] and not status['original_parent_wait_status_recoverable']\n    for identity in recovery_policy['adopted_births'] + recovery_policy['lost_controllers'] + [status['controller']]:\n        path = Path('/proc') / str(identity['pid']) / 'stat'\n        if path.exists():\n            fields = path.read_text().rsplit(') ', 1)[1].split()\n            assert fields[19] != identity['start_ticks'] or fields[0] == 'Z'")
  sub("    assert status['policy'] == pin(B / 'policy.json')\n", "    assert recovery_policy['pins'][str(B / 'policy.json')] == pin(B / 'policy.json')\n")
  sub("    owner = read(B / 'owner.json')\n    assert owner['status'] == 'HEALTHY' and len(owner['processes']) == 2", "    owner = read(C / 'owner.json')\n    assert owner['status'] == 'HEALTHY' and len(owner['processes']) == 1")
  sub("    for stage, owned in zip(status['stages'], owner['processes']):\n        assert owned['status'] == 'REAPED_NO_LIVE_MEMBERS'\n        assert owned['returncode'] == stage['returncode']\n        assert not owned['members_at_leader_exit']", "    assert [s['name'] for s in status['stages']] == ['direct', 'miter']\n    for stage in status['stages']:\n        if stage['name'] == 'direct':\n            assert stage['returncode'] is None\n            assert stage['returncode_provenance'] == 'unavailable_non_child_orphan'\n        else:\n            owned = owner['processes'][0]\n            assert owned['status'] == 'REAPED_NO_LIVE_MEMBERS'\n            assert owned['returncode'] == stage['returncode']\n            assert not owned['members_at_leader_exit']\n            assert stage['returncode_provenance'] == 'waited_owned_child'")
  sub("        passed = stage['returncode'] == 0", "        assert stage['helper_result'] == dict(path=str(path), **pin(path))\n        assert stage['pytest_xml'] == dict(path=str(B / (stage['name'] + '-pytest.xml')), **pin(B / (stage['name'] + '-pytest.xml')))\n        assert stage['actual_cocotb_counts'] == counts and stage['actual_cocotb_case_count'] == len(cases)\n        passed = stage['passed']\n        if stage['name'] == 'miter':\n            assert passed == (stage['returncode'] == 0)")
  sub("        rows.append(dict(name=stage['name'], returncode=stage['returncode'], passed=passed,", "        rows.append(dict(name=stage['name'], returncode=stage['returncode'], returncode_provenance=stage['returncode_provenance'], passed=passed,")
  sub("controller_status=pin(B / 'status.json'), policy=pin(B / 'policy.json'),", "controller_status=pin(C / 'status.json'), policy=pin(B / 'policy.json'), recovery_policy=pin(C / 'policy.json'), recovery_peer=pin(C / 'source-peer.json'), original_controller_abruptly_lost=True, direct_wait_status_unavailable=True,")
  sub("    for name in policy['pins']:\n", "    recovery_methods = ['run.py', 'policy.json', 'source-peer.json', 'source_peer_pll.py', 'source-peer-pll.log', 'status.json', 'owner.json', 'controller.log', 'launch.json', 'test_completion_race.py', 'completion-race-control.json', 'completion-race-control.log', 'completion-race-wrong-python-attempt01.log', 'derive_preservation.py', 'preservation-derivation.json', 'seal.py', 'continue_preservation.py', 'preservation-policy.json', 'preservation-source-peer.json', 'preservation_peer_root.py', 'preservation-peer-root.log']\n    for name in recovery_methods:\n        p = C / name\n        assert p.is_file(), ('Mandatory recovery evidence', name)\n        files['recovery/' + name] = p\n    for p in sorted(C.rglob('*')):\n        if p.is_file() and ({'source-candidate01', 'preservation-source-candidate01', 'preservation-source-candidate02'} & set(p.parts) or p.name.startswith('old-')):\n            files['recovery/' + str(p.relative_to(C))] = p\n    for name in ['first-case-started-observation.json', 'first-case-started-snapshot.log']:\n        files['method/' + name] = B / name\n    for name in policy['pins']:\n")
 else:
  sub('"""Observe existing MAX4118 owner, then seal/publish its closed captures once."""','"""Observe exact recovery owner then preserve closed observed/owned profiles."""')
  # New observer/control metadata lives in C; actual unique assets and historical
  # original method/evidence remain in B.
  for stem in ['preservation-status.json','preservation-policy.json','preservation-source-peer.json','preservation-owner.json']:
   text2=text.replace("B / '"+stem+"'","C / '"+stem+"'")
   assert text2!=text
   changes.append(dict(before=text,after=text2,whole_text_transport=True));text=text2
  sub("peer['status'] == 'PASS_SOURCE_ONLY_V18_MAX4118_PRESERVATION'", "peer['status'] == 'PASS_SOURCE_ONLY_V18_MAX4118_RECOVERY_PRESERVATION'")
  sub("status='WAITING_EXISTING_MAX4118_CONTROLLER'", "status='WAITING_EXISTING_MAX4118_RECOVERY_CONTROLLER'")
  sub("with (B / (name + '.log')).open('x') as log:", "with (C / (name + '.log')).open('x') as log:")
  sub("log=pin(B / (name + '.log')))", "log=pin(C / (name + '.log')))")
  sub("terminal = load(B / 'status.json')", "terminal = load(C / 'status.json')")
  sub("assert terminal['status'] in {'COMPLETE_PENDING_INDEPENDENT_XML_REVIEW_AND_SEAL',\n                                           'FAILED_CASES_RETAINED_PENDING_REVIEW_AND_SEAL'}\n            assert not terminal['current_descendants']\n            stage('seal', [sys.executable, str(B / 'seal.py')])", "assert terminal['status'] in {'COMPLETE_TWO_PROFILES_XML_VERIFIED_REQUIRES_RECOVERY_AWARE_SEAL',\n                                           'CLOSED_TWO_PROFILES_FAILURE_RETAINED_REQUIRES_RECOVERY_AWARE_SEAL'}\n            assert not terminal['current_external'] and not terminal['current_owned']\n            stage('seal', [sys.executable, str(C / 'seal.py')])")
 ast.parse(text)
 inverse=text
 for c in reversed(changes):
  if c.get('whole_text_transport'):assert inverse==c['after'];inverse=c['before']
  else:assert inverse.count(c['after'])==1;inverse=inverse.replace(c['after'],c['before'])
 assert inverse==old.read_text()
 out=C/name;assert not out.exists();out.write_text(text)
 ledgers[name]=dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(out),**pin(out)),changes=changes)
p=C/'preservation-derivation.json';assert not p.exists();p.write_text(json.dumps(ledgers,indent=2)+'\n')
oldp=json.loads((M/'preservation-policy.json').read_text())
pins=oldp['pins'].copy()
for p in [C/'run.py',C/'policy.json',C/'source-peer.json',C/'seal.py',C/'continue_preservation.py',C/'derive_preservation.py',C/'preservation-derivation.json']:
 pins[str(p)]=pin(p)
# Original dead controller identity is retained only in historical policy.
status=json.loads((C/'status.json').read_text());policy=dict(pins=pins,controller=status['controller'],boot_id=status['boot_id'],scope='Separate passive observer, owned inner seal/V3 children only after recovered external direct and own miter have terminal exact XML receipts. Original abrupt parent-loss evidence remains included.15second failure grace, no healthy timeout, unchanged native profiles.')
p=C/'preservation-policy.json';assert not p.exists();p.write_text(json.dumps(policy,indent=2)+'\n')
for name in ['seal.py','continue_preservation.py','preservation-derivation.json','preservation-policy.json']:print(name,pin(C/name))
