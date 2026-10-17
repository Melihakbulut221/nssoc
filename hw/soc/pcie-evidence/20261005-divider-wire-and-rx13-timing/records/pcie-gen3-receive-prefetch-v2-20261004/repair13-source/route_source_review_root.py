# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent RX13 route/RC bridge and prerequisite capture readback."""
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

B = Path('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004')
S = B/'repair13-source'
E = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-equivalence')
P = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-physical-replay-01')


def pin(path):
    path = Path(path)
    with path.open('rb') as f:
        return {'bytes':path.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}


freeze = json.loads((S/'route-rc-source-freeze.json').read_text())
assert pin(S/'route-rc-source-bridge.json') == freeze['bridge']
bridge = json.loads((S/'route-rc-source-bridge.json').read_text())
subs = [('repair12','repair13'),('repair-12','repair-13'),('RX12','RX13'),
        ('rx12','rx13'),('candidate12','candidate13'),
        ('eight measured critical-wire buf4 insertions and two buf1->buf4 following actual routed11 nominalRC',
         'six measured critical-wire buffer isolations and four cell upsizes following actual routed12 nominalRC'),
        ('GRTsetup+.031432 hold+.104912','GRTsetup+.030562 hold+.105448')]
for item in bridge:
    a=Path(item['before']['path']).read_text()
    z=Path(item['after']['path']).read_text()
    assert pin(item['before']['path']) == {k:item['before'][k] for k in ('bytes','sha256')}
    assert pin(item['after']['path']) == freeze['files'][item['after']['path']]
    assert ''.join(o['before'] for o in item['opcodes']) == a
    assert ''.join(o['after'] for o in item['opcodes']) == z
    check=a
    for old,new in subs:
        check=check.replace(old,new)
    assert check==z
    inverse=z
    for old,new in reversed(subs):
        inverse=inverse.replace(new,old)
    assert inverse==a
g=json.loads((E/'proof-execution-binding.json').read_text())
assert g['status']=='PASS_ACTUAL_RX13_PROOF_AND_MUTATION_EXECUTION_BOUND'
assert g['before_inputs']==g['after_inputs']=={p:pin(p) for p in g['before_inputs']}
assert g['outputs']=={n:pin(E/n) for n in g['outputs']}
assert g['expanded_graphs_before']==g['expanded_graphs_after']
for name,entry in g['expanded_graphs_before'].items():
    assert pin(E/(name+'.json.gz'))==entry['compressed']
    h=hashlib.sha256();size=0
    with gzip.open(E/(name+'.json.gz'),'rb') as f:
        while data:=f.read(1048576):h.update(data);size+=len(data)
    assert {'bytes':size,'sha256':h.hexdigest()}==entry['expanded']
port=json.loads((P/'result.json').read_text())
assert port['status']=='PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING'
assert port['inputs']=={p:pin(p) for p in port['inputs']}
cases=ET.parse(P/'results.xml').getroot().findall('.//testcase')
assert len(cases)==6 and all(len(c)==0 for c in cases)
pre=json.loads((S/'pre-drt-proof-port-review.json').read_text())
assert pin(S/'pre-drt-proof-port-review.json')==freeze['gate_review']
assert pre['gate_execution_binding']==pin(E/'proof-execution-binding.json')
assert pre['port_receipt']==pin(P/'result.json')
assert pre['canonical_states']==1804 and pre['canonical_targets']==5443
assert pre['actual_mutation_controls']==10
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01').exists()
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01').exists()
out={'status':'PASS_SOURCE_ONLY_RX13_DRT_RC_AND_ACTUAL_PREREQUISITES',
     'findings':[],'method':pin(__file__),'source_freeze':pin(S/'route-rc-source-freeze.json'),
     'files':freeze['files'],'bridge':freeze['bridge'],'whole_source_forward_inverse':True,
     'allowed_substitutions':subs,'full_native_graph_byte_readback':g['expanded_graphs_before'],
     'actual_port_cases':[c.attrib['name'] for c in cases],
     'limits':freeze['limits'],'scope':'New route/RC source bodies unchanged except exact paths/version/accurate candidate metadata. Saved completed proof graphs/bindings and six native ports rehashed. Fresh CPU8 native DRT then RC permitted with existing resource and proof gates; no routed timing claim.'}
(S/'route-rc-source-only-peer-root.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
