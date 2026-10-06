# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Create separate RX14A route/RC producers after exact executed proof+ports."""
from pathlib import Path
import ast,difflib,hashlib,importlib.util,json,xml.etree.ElementTree as ET
S=Path(__file__).resolve().parent;B=S.parent;N=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-14a');E=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-equivalence');P=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-physical-replay-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
spec=importlib.util.spec_from_file_location('rx14a_saved_gate',B/'proof_gate_repair14a.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);binding=gate.verify_binding()
port=json.loads((P/'result.json').read_text());own=json.loads((P/'owned-driver.json').read_text());assert port['status']=='PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING' and port['tests']==dict(passed=6,failed=0,skipped=0);assert own['status']=='PASS_EXACT_PROVED_RX14A_SIX_NATIVE_PORT_CASES'
for r in [port,own]:
 for p,v in r['inputs'].items():assert pin(p)==v
xmls=list(P.rglob('*.xml'));cases=[]
for p in xmls:
 for c in ET.parse(p).getroot().iter('testcase'):assert c.find('failure') is None and c.find('error') is None and c.find('skipped') is None;cases.append(c.attrib)
assert len(cases)==6
proof=json.loads((E/'equivalence.json').read_text());assert proof['states']==1804 and proof['matched']==proof['targets']==5443 and not proof['mismatches'];assert len(json.loads((E/'mutation-controls.json').read_text())['controls'])==10
files={};pairs=[]
for stem in ['drt','detailed_rc']:
 old=B/(stem+'_repair13.py');new=B/(stem+'_repair14a.py');original=old.read_text();text=original.replace('repair13','repair14a').replace('repair-13','repair-14a').replace('RX13','RX14A').replace('rx13_','rx14a_')
 if stem=='drt':
  oldscope='RX candidate13: six measured critical-wire buffer isolations and four cell upsizes following actual routed12 nominalRC. Fullnative1804state/5443function binaryproof+10controls+6physicalportsPASS. Fresh26Q2DRT;actualnominalRCstillrequired;GRTsetup+.030562 hold+.105448.'
  newscope='RX candidate14a: eleven exact-single-load buf2 isolations after actual routed13 nominalRC. Two GRT drive alternatives measured, buf4 rejected; unchanged4ns/globalGRTsetup+.032734 hold+.105402. Fullnative1804state/5443function binaryproof+10controls+6physicalportsPASS. Fresh26Q2DRT and actualnominalRC remain required; targetedGRT is not acceptance.'
  assert oldscope in text;text=text.replace(oldscope,newscope)
 assert not new.exists();ast.parse(text);new.write_text(text);files[str(new)]=pin(new)
 for f in ['limit','on_signal','interrupted']:
  a=[n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name==f];z=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==f]
  assert ast.dump(ast.Module(a,[]))==ast.dump(ast.Module(z,[]))
 a=original.splitlines(True);z=text.splitlines(True);ops=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes():ops.append(dict(tag=tag,before=''.join(a[i:j]),after=''.join(z[k:l])))
 assert ''.join(x['before'] for x in ops)==original and ''.join(x['after'] for x in ops)==text
 pairs.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
(S/'route-rc-source-bridge.json').write_text(json.dumps(pairs,indent=2)+'\n')
review=dict(status='PASS_RX14A_ACTUAL_PROOF_BINDING_AND_SIX_PORT_CASES_REHASHED_BEFORE_DRT',gate_execution_binding=pin(E/'proof-execution-binding.json'),canonical_states=1804,canonical_targets=5443,actual_mutation_controls=10,actual_port_cases=cases,port_receipt=pin(P/'result.json'),port_owner=pin(P/'owned-driver.json'),same_candidate=pin(N/'repaired.v'),scope='Only saved completed fresh14a proof/ports reviewed; no proof or physical replay rerun. Originalgold11 reuse bound explicitly. Newroute/RC still required.')
(S/'pre-drt-proof-port-review.json').write_text(json.dumps(review,indent=2)+'\n')
r=dict(status='FROZEN_RX14A_ROUTE_AND_NOMINAL_RC_SOURCE_NO_NATIVE_STARTED',method=pin(__file__),files=files,bridge=pin(S/'route-rc-source-bridge.json'),gate_review=pin(S/'pre-drt-proof-port-review.json'),limits=dict(cpu=8,address_space=2684354560,entry_free=1073741824,shared_floor=553648128,healthy_elapsed_watchdog=None),scope='Only new14a paths/version/metadata from frozen13. Exact actual proof binding/ports mandatory; newDRT same netlist/zeroDRC and allinput/output hashes guard RC. Same nominal model, cellcorners and constraints; no signoff.')
(S/'route-rc-source-freeze.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
