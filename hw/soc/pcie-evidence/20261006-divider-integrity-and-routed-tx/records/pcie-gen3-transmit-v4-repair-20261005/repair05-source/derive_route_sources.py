# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Derive fresh TX05 route/RC only after exact proof and real three-port replay."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,re,sys,ast
import xml.etree.ElementTree as ET
B=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent
C=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05');P=Path('/dev/shm/nssoc-tx-path-v4-repair05-physical-replay-02')
sys.path.insert(0,str(B));import proof_gate_repair05 as gate

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
binding=gate.verify_binding();pr=json.loads((P/'result.json').read_text())
assert pr['status']=='PASS_EXACT_BOUND_TX05_PHYSICAL_NETLIST_PORT_REPLAY'
assert pr['inputs']=={p:pin(p) for p in pr['inputs']}
assert pr['outputs']=={n:pin(P/n) for n in pr['outputs']}
assert pr['tests']=={'passed':3,'failed':0,'skipped':0}
cases=ET.parse(P/'results.xml').getroot().findall('.//testcase');assert len(cases)==3 and all(len(c)==0 for c in cases)
assert '10 passed' in (S/'binding-controls02.log').read_text()
assert '8 passed' in (S/'lifecycle-controls02.log').read_text()
raw=(C/'native.log').read_text();slacks={};paths={}
for corner in ['slow','typical','fast']:
 paths[corner]={}
 for direction in ['max','min']:
  tag=f'TX05_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY_{corner}_{direction}\n'
  assert raw.count(tag)==1
  section=raw.split(tag)[1].split('TX05_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY_')[0].split('NATIVE_TX05_BROAD_CANDIDATE_COMPLETE')[0]
  for block in section.split('Startpoint:')[1:]:
   values=re.findall(r'([+-]?[0-9]+\.[0-9]+)\s+slack \((?:MET|VIOLATED)\)',block);assert len(values)==1
   if 'Path Group: asynchronous' in block:kind='recovery' if direction=='max' else 'removal'
   else:
    assert 'Path Group: development_clock' in block;kind='setup' if direction=='max' else 'hold'
   paths[corner].setdefault(kind,[]).append(float(values[0]))
 slacks[corner]={k:min(v) for k,v in paths[corner].items()};assert set(slacks[corner])=={'setup','hold','recovery','removal'}
proof=dict(status='PASS_COMPLETED_TX05_BOUND_PROOF_AND_THREE_NATIVE_PORT_CASES',binding=pin(gate.E/'proof-execution-binding.json'),states=3850,functions=11680,kernel_faults=10,binding_controls=10,lifecycle_actual_controls=8,port_result=pin(P/'result.json'),port_cases=[c.attrib for c in cases],candidate=pin(C/'repaired.v'),GRT_ESTIMATES_ONLY=slacks,all_reported_GRT_path_slacks=paths,scope='Actual proof and ports; no detailed route/actualRC forTX05 yet. GRT summaries use minimum of all reported paths perkind, never lastrow.')
(S/'pre-drt-proof-port-review.json').write_text(json.dumps(proof,indent=2)+'\n')
bridges=[];files={}
for old,new in [('drt_repair03.py','drt_repair05.py'),('detailed_rc_repair03.py','detailed_rc_repair05.py')]:
 source=B/old;target=B/new;before=source.read_text()
 after=before.replace('repair03','repair05').replace('repair-03','repair-05').replace('TX03','TX05').replace('tx03','tx05').replace('repair05-physical-replay-01','repair05-physical-replay-02')
 after=after.replace('from pathlib import Path','from pathlib import Path\nfrom owned_lifecycle05 import owned_popen, stop_failed_group',1)
 start=after.index('tree=ast.parse(');end=after.index('\n',after.index(';exec(compile(',start))
 after=after[:start]+"ns={'stop_failed_group':stop_failed_group}"+after[end:]
 after=after.replace('subprocess.Popen(', 'owned_popen(')
 after=after.replace('files=[Path(__file__),','files=[Path(__file__),Path(__file__).resolve().parent/\'owned_lifecycle05.py\',',1)
 after=after.replace('TX candidate03: seven measured complex/XOR driver-load isolations and three buffer upsizes following actualTX02 nominalRC. Existing hold repair preserved.','TX candidate05: actualTX03 nominalSPEF initialization, 488resizeoperations335setupbuffers2holdbuffers; completed canonical proof and native ports required. Final GRT estimates are not routed timing.')
 assert 'ast.parse(' not in after and 'subprocess.Popen(' not in after
 ast.parse(after);assert not target.exists();target.write_text(after)
 a,z=before.splitlines(True),after.splitlines(True)
 ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(z[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
 assert ''.join(o['before'] for o in ops)==before and ''.join(o['after'] for o in ops)==after
 bridges.append(dict(before=dict(path=str(source),**pin(source)),after=dict(path=str(target),**pin(target)),opcodes=ops));files[str(target)]=pin(target)
files[str(B/'owned_lifecycle05.py')]=pin(B/'owned_lifecycle05.py')
(S/'route-rc-source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n')
r=dict(status='FROZEN_TX05_FRESH_ROUTE_AND_RC_NO_NATIVE_ROUTE_EXECUTION',method=pin(__file__),files=files,bridge=pin(S/'route-rc-source-bridge.json'),completed_proof_port_review=pin(S/'pre-drt-proof-port-review.json'),scope='ExactTX03 native route/RC Tcl unchanged except fresh05paths. WNOWAIT owned helper replaces old lifecycle, pinned asinput; unchanged4ns2.5GiBCPU4/nohealthyelapsedtimeout. Same-netlist byteidentity andDRC0 required before fresh nominalRC. NoqualifiedRC orfullchipclaim.')
(S/'route-rc-source-freeze.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(files=files,GRT_ESTIMATES_ONLY=slacks),indent=2))
