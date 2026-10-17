# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind TX03 fresh route/RC methods to completed new proof and port evidence."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

B=Path('hw/soc/out/pcie-gen3-transmit-v4-repair-20261005').resolve()
S=B/'repair03-source'
P=Path('/dev/shm/nssoc-tx-path-v4-repair03-physical-replay-01')
C=Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03')


def pin(path):
    path=Path(path)
    with path.open('rb') as f:
        return {'bytes':path.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}


spec=importlib.util.spec_from_file_location('tx03_completed_gate',B/'proof_gate_repair03.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
binding=gate.verify_binding()
pr=json.loads((P/'result.json').read_text())
assert pr['status']=='PASS_EXACT_BOUND_TX03_PHYSICAL_NETLIST_PORT_REPLAY'
assert pr['inputs']=={p:pin(p) for p in pr['inputs']}
assert pr['outputs']=={n:pin(P/n) for n in pr['outputs']}
assert pr['tests']=={'passed':3,'failed':0,'skipped':0}
cases=ET.parse(P/'results.xml').getroot().findall('.//testcase')
assert len(cases)==3 and all(len(c)==0 for c in cases)
assert '10 passed' in (S/'binding-controls.log').read_text()
raw=(C/'native.log').read_text()
slacks={}
for corner in ('slow','typical','fast'):
    slacks[corner]={}
    for direction in ('max','min'):
        tag=f'CANDIDATE_GLOBAL_ROUTE_ESTIMATES_ONLY_{corner}_{direction}\n'
        section=raw.split(tag)[1].split('CANDIDATE_GLOBAL_ROUTE_ESTIMATES_ONLY_')[0]
        for block in section.split('Startpoint:')[1:]:
            values=re.findall(r'([+-]?[0-9]+\.[0-9]+)\s+slack \((?:MET|VIOLATED)\)',block)
            assert len(values)==1
            if 'Path Group: asynchronous' in block:
                kind='recovery' if direction=='max' else 'removal'
            else:
                assert 'Path Group: development_clock' in block
                kind='setup' if direction=='max' else 'hold'
            slacks[corner][kind]=float(values[0])
proof={'status':'PASS_COMPLETED_TX03_BOUND_PROOF_AND_THREE_NATIVE_PORT_CASES',
       'binding':pin(gate.E/'proof-execution-binding.json'),
       'states':3850,'functions':11680,'kernel_faults':10,'binding_controls':10,
       'port_result':pin(P/'result.json'),'port_cases':[c.attrib for c in cases],
       'candidate':pin(C/'repaired.v'),'GRT_ESTIMATES_ONLY':slacks,
       'scope':'Completed actual proof and ports; no detailed route or actualRC forTX03 yet.'}
(S/'pre-drt-proof-port-review.json').write_text(json.dumps(proof,indent=2)+'\n')
bridges=[]
files={}
for oldname,newname in [('drt_repair02_resume03.py','drt_repair03.py'),('detailed_rc_repair02_resume03.py','detailed_rc_repair03.py')]:
    source=B/oldname;target=B/newname;before=source.read_text()
    after=before.replace('repair02','repair03').replace('repair-02','repair-03').replace('TX02','TX03').replace('tx02','tx03')
    after=after.replace('repair03-drt-03','repair03-drt-01').replace('repair03-detailed-rc-02','repair03-detailed-rc-01')
    after=after.replace('TX candidate02: six measured driver-load isolations, nine buf1->buf4, one hold buffer following actualTX01 nominalRC.',
                        'TX candidate03: seven measured complex/XOR driver-load isolations and three buffer upsizes following actualTX02 nominalRC. Existing hold repair preserved.')
    after=after.replace('GRTsetup+.684261 recovery+.149536 hold+.065914.','FreshGRT estimates retained separately; not routed timing.')
    assert not target.exists()
    target.write_text(after)
    a=before.splitlines(True);z=after.splitlines(True)
    ops=[{'tag':tag,'before':''.join(a[i:j]),'after':''.join(z[k:l])}
         for tag,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
    assert ''.join(o['before'] for o in ops)==before and ''.join(o['after'] for o in ops)==after
    bridges.append({'before':{'path':str(source),**pin(source)},'after':{'path':str(target),**pin(target)},'opcodes':ops})
    files[str(target)]=pin(target)
(S/'route-rc-source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n')
freeze={'status':'FROZEN_TX03_FRESH_ROUTE_AND_RC_METHODS_NO_NATIVE_ROUTE_EXECUTION',
        'method':pin(__file__),'files':files,'bridge':pin(S/'route-rc-source-bridge.json'),
        'completed_proof_port_review':pin(S/'pre-drt-proof-port-review.json'),
        'scope':'Exact TX02 DRT03/RC02 method bodies retained except new03fresh01 output paths/status/version and accurate candidate metadata. Unchanged4nsconstraints,2.5GiB,CPU4,resource floors/no healthyelapsedtimeout. Newroute same-netlist/DRC0 and exactproof/ports mandatory.'}
(S/'route-rc-source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps({'sources':files,'GRT_ESTIMATES_ONLY':slacks},indent=2))
