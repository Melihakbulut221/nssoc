# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preliminary source-only reader; never imports or runs reviewed producers."""
from pathlib import Path
import ast,hashlib,json,difflib
R=Path.cwd();B=R/'hw/soc/out/pcie-integrity-v25-20261006';D=B/'draft-before-unknown-control02'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
g=R/'scripts/generate_pcie_integrity_command_v25.py';v=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v';base=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v';t=R/'sw/tests/test_pcie_gen3_integrity_v25_command.py';p=B/'source-bridge-draft02.json'
bridge=json.loads(p.read_text());assert len(bridge['edits'])==14
x=base.read_text()
for e in bridge['edits']:
 assert x.count(e['before'])==e['count'];x=x.replace(e['before'],e['after'])
assert x==v.read_text();assert pin(v)=={k:bridge['candidate'][k]for k in ['bytes','sha256']}
for e in reversed(bridge['edits']):
 assert x.count(e['after'])==e['count'];x=x.replace(e['after'],e['before'])
assert x==base.read_text();assert pin(base)['sha256']==bridge['baseline_sha256']
old='''     command_valid<=0;
     if(step) command_valid<=1;'''
new='''     // Match the procedural apply gate, including unknown external controls:
     // if enabled is X, neither apply nor replacement occurs; retain ownership.
     if(enabled) begin
       command_valid<=0;
       if(step) command_valid<=1;
     end'''
for current in (g,v):
 previous=D/current.name;a=previous.read_text();z=current.read_text();assert a.count(old)==1 and z==a.replace(old,new)
ns={}
for node in ast.parse(t.read_text()).body:
 if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and node.targets[0].id in ('TB','FAULTS'):ns[node.targets[0].id]=ast.literal_eval(node.value)
assert len(ns['FAULTS'])==11 and len({x[0]for x in ns['FAULTS']})==11
assert 'comparisons!=4102' in ns['TB'] and 'for(t=0;t<4096;t=t+1)' in ns['TB']
for q in ['unknown_holds!=','force ','release ']:assert q not in ns['TB']
for q in ['for(t=0;t<8;t=t+1)','for(t=0;t<2;t=t+1)','for(t=0;t<5;t=t+1)','V25_COMMAND_UNKNOWN_CONTROL_HOLD','V25_COMMAND_UNKNOWN_CONTROL_RESUME','V25_COMMAND_UNKNOWN_FAULT_FALLTHROUGH','V25_COMMAND_PREVIOUS_VERDICT_LOOKUP','V25_COMMAND_DUPLICATE_PRIORITY']:assert q in ns['TB']
inputs={str(x):pin(x)for x in (g,v,base,t,p,D/g.name,D/v.name,D/t.name,D/'manifest.json')}
r=dict(status='PRELIMINARY_SOURCE_REVIEW_V25_COMMAND_COMPONENT_AND_UNKNOWN_ENABLE_NO_FINAL_APPROVAL',reviewer='/root/vco_loaded_feedback',method=pin(__file__),inputs=inputs,whole_byte_forward_inverse=14,exact_generator_and_product_delta='Only explicit enabled procedural guard plus three explanatory comment lines around valid consume/replacement; all other bytes equal preserved draft.',reviewed_arguments=['NBA apply reads complete previous command while simultaneous capture replaces every payload/metadata field.','Reference writer snapshot before edge is compared after candidate apply: all seven slot fields, cache, verdict array and visible commit frontier.','4102 planned one-edge comparisons =4096 randomized/XZ payload trials +3 duplicate/prior-verdict trials +3 ending/drain trials; actual native execution remains pending.','Unknown flush/start/abort/reset makes enabled X/Z-derived unknown and both APPLY and CAPTURE valid replacement skip; pending ownership retained and resumes after known enable.','Unknown fault expression with enabled true follows original procedural fallthrough; pending command applies and consumes.','Five separate epoch invalidations reject stale valid/frontier; eleven literal real writer mutations require specific diagnostics; no forced DUT state.'],limitations=['Source-only preliminary reading; no reviewed producer imports, test collection, HDL compilation, simulation or native map.','Component controls do not establish full-DUT transaction/backpressure/fault/latency equivalence. RX owns final source gate after complete test packet.','Actual cache contents may change on known fault as already documented; epoch quarantine must be witnessed by full-DUT controls.'],findings=[])
(B/'preliminary-command-component-peer-vco02.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(receipt=pin(B/'preliminary-command-component-peer-vco02.json'),faults=len(ns['FAULTS']),status=r['status'])))
