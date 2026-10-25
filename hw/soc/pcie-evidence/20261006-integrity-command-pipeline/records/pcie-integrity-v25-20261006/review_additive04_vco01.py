# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source/hash/AST and saved-diagnostic read; no producer imports."""
from pathlib import Path
import ast, difflib, hashlib, json, xml.etree.ElementTree as ET
R=Path.cwd(); B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def textpin(t):return dict(bytes=len(t.encode()),sha256=hashlib.sha256(t.encode()).hexdigest())
def literal(tree,name):
 rows=[x for x in tree.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in x.targets)]
 assert len(rows)==1;return ast.literal_eval(rows[0].value)
fpath=B/'source-freeze04.json';assert pin(fpath)==dict(bytes=75168,sha256='a1c125fdb02559a5c3269351c2a918c731327c538cef8b6a4c70101a453c591f')
f=json.loads(fpath.read_text());assert len(f['sources'])==302 and f['functional_predicates']==43
for path,v in f['sources'].items():assert pin(R/path)==v,path
p=json.loads((B/'source-only-peer-rx03.json').read_text());assert p['status']=='PASS_SOURCE_ONLY_V25_REGISTERED_COMMAND_IMPLEMENTATION'and p['findings']==[]
assert p['freeze']==pin(B/'source-freeze03.json')
s=json.loads((B/'reset-repair-source-supplement04.json').read_text());assert len(s['changes'])==5
assert s['parent_freeze']==pin(B/'source-freeze03.json') and s['failed_capture']==pin(B/'failed-controls01/validation.json')
for path,v in s['changes'].items():
 assert textpin(v['before_body'])==v['before']==p['source_pins'][path]
 assert textpin(v['after_body'])==v['after']==pin(R/path)==f['product_sources'][path]
 assert (R/path).read_text()==v['after_body']
 assert ''.join(difflib.unified_diff(v['before_body'].splitlines(True),v['after_body'].splitlines(True)))==v['full_diff']
for path,v in f['product_sources'].items():
 if path not in s['changes']:assert p['source_pins'][path]==v
# Independent complete-body inverse for the only RTL/generator semantic delta.
comment=' // Direct reset checks also prevent stale derived-enable writes at 1-to-X/Z\n // asynchronous reset transitions; they are redundant for known controls.\n'
for path in ['scripts/generate_pcie_integrity_command_v25.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v']:
 actual=(R/path).read_text();old=s['changes'][path]['before_body']
 inverse=actual.replace(comment,'')
 for a,b in [('if(rst_ni && step) begin','if(step) begin'),('if(rst_ni && enabled) begin','if(enabled) begin'),('if(rst_ni && enabled && command_valid) begin','if(enabled && command_valid) begin'),('if(rst_ni && enabled && active_o && command_valid) slot_verdict','if(enabled && active_o && command_valid) slot_verdict')]:
  assert inverse.count(a)==1
  inverse=inverse.replace(a,b)
 assert inverse==old
# Independently reconstruct the entire framer from pinned V23 and every ledger edit.
base=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v';actual=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v'
t=base.read_text();assert pin(base)['sha256']=='505db8d1daa5c5263a16a3584175bc89a73d1b6e35f16e10b64f1f9f6483dde6'
for e in s['whole_framer_ledger']:
 assert t.count(e['before'])==e['count'];t=t.replace(e['before'],e['after'])
assert t==actual.read_text()
for e in reversed(s['whole_framer_ledger']):
 assert t.count(e['after'])==e['count'];t=t.replace(e['after'],e['before'])
assert t==base.read_text() and len(s['whole_framer_ledger'])==14
# Full support-body inverses, not only diff metadata.
u=json.loads((B/'support-derivation04.json').read_text());zero_support_substitutions=[]
for e in u['bridges']:
 assert Path(e['parent']).read_text()==e['parent_body'] and pin(e['parent'])==e['parent_pin']
 assert Path(e['candidate']).read_text()==e['candidate_body'] and pin(e['candidate'])==e['candidate_pin']
 t=e['parent_body']
 for before,after in e['substitutions']:
  if before not in t:zero_support_substitutions.append(dict(candidate=e['candidate'],literal=before))
  t=t.replace(before,after)
 assert t==e['candidate_body']
 assert ''.join(difflib.unified_diff(e['parent_body'].splitlines(True),e['candidate_body'].splitlines(True)))==e['full_diff']
# Full298 payload bits at PW5; command_valid and visible commit checked separately.
ct=ast.parse((R/'sw/tests/test_pcie_gen3_integrity_v25_command.py').read_text());tb=literal(ct,'TB');faults=literal(ct,'FAULTS')
assert len(faults)==12 and sum(1 for x in faults if x[0]=='reset_apply_guard_removed')==1
assert 2*5+128+4*16+48+2*4*5+2*4==298
assert 'reg [297:0] held_command;'in tb and 'for(t=0;t<10;t=t+1)'in tb
assert 'V25_COMMAND_UNKNOWN_CONTROL_PAYLOAD_HOLD'in tb and 'V25_COMMAND_UNKNOWN_CONTROL_WRITES'in tb
for name in ['address','commit','data','keep','sop','eop','dllp','sequence','tags','verdict_enable','verdict_tags','verdict_value']:
 assert tb.count('dut.command_'+name)>=2
assert '3:rst_ni=(t%2)?1\'bz:1\'bx;'in tb
assert 'if(dut.command_valid!==1 || dut.visible_commit_ptr!==held_commit)'in tb
for token in ['unknown_holds!=','V25_COMMAND_REQUIRED_RELATION_WITNESS']:
 if token.endswith('!='):continue
 assert token in tb
fault=next(x for x in faults if x[0]=='reset_apply_guard_removed')
assert fault[1:] == ('if(rst_ni && enabled && command_valid) begin','if(enabled && command_valid) begin','V25_COMMAND_UNKNOWN_CONTROL_WRITES')
# The fault prelude selector changes; all fault injection and restart code remains exact.
path='sw/tests/test_pcie_gen3_integrity_v25_block_burst.py';v=s['changes'][path]
new=ast.parse(v['after_body']);old=ast.parse(v['before_body'])
by=lambda x:{n.name:ast.dump(n,include_attributes=False)for n in x.body if isinstance(n,ast.FunctionDef)}
a,b=by(old),by(new);assert a.keys()==b.keys();assert [n for n in a if a[n]!=b[n]]==['run_burst']
assert a['pending_fault_campaign']==b['pending_fault_campaign']
assert 'blocks, expected, packets = stimulus(minimum)\n' in v['after_body']
# Recount the preserved failed campaign, and inspect actual native diagnostic traces.
root=ET.parse(B/'controls01.xml').getroot();cases=root.findall('.//testcase');fails=[x for x in cases if x.find('failure')is not None or x.find('error')is not None]
assert len(cases)==42 and len(fails)==2
failure_names=[x.attrib['name'] for x in fails]
assert any('positive' in n for n in failure_names) and any('pending_badblock' in n for n in failure_names)
diags={}
for name,expected in s['diagnostics'].items():
 q=B/name/'result.json';assert pin(q)==expected
 d=json.loads(q.read_text());diags[name]=dict(result=pin(q),simulation_log=pin(B/name/'simulation.log'))
log=(B/'component-diagnostic01/simulation.log').read_text()
assert 'rst=x enabled=1 step=1 drive=0 valid=1 slot8=12340005'in log
assert 'rst=x enabled=x step=0 drive=0 valid=1 slot8=12340006'in log
assert 'V25_COMMAND_UNKNOWN_CONTROL_WRITES kind=6 slot=8'in log
for name in ['burst-diagnostic01','burst-baseline-diagnostic02']:
 log=(B/name/'simulation.log').read_text();assert 'cap=1 bad=0 token=0 occupied=61'in log and 'FRAMER_UNEXPECTED_FAULT'in log
assert not Path('/dev/shm/nssoc-integrity-v25-full-controls02').exists() and not (B/'status02.json').exists()
assert all(pin(R/path)==v for path,v in f['sources'].items())
out=dict(status='PASS_SOURCE_ONLY_V25_REGISTERED_COMMAND_IMPLEMENTATION',reviewer='vco_loaded_feedback',freeze=pin(fpath),launcher=pin(B/'launch_controls04.py'),detacher=pin(B/'detach_controls04.py'),findings=[],method=pin(__file__),prior_complete_source_peer=pin(B/'source-only-peer-rx03.json'),supplement=pin(B/'reset-repair-source-supplement04.json'),support=pin(B/'support-derivation04.json'),rehash_inputs=302,product_sources=10,whole_changed_bodies=5,whole_framer_inverse_edits=14,support_whole_inverses=2,shared_ledger_zero_occurrence_substitutions=zero_support_substitutions,reviewer_attempts_retained=['additive04-reviewer-attempt01','additive04-reviewer-attempt02'],old_campaign=dict(tests=42,passed=40,failed=2,failure_names=failure_names,xml=pin(B/'controls01.xml')),saved_diagnostics=diags,source_pins=f['product_sources'],reviewed_semantics=['Four direct reset terms suppress procedural writes when rst_ni is X/Z even if continuous enabled/step still carry a previous value on the asynchronous1-to-X/Z edge. Known1/0 reset behavior and all other writer/parser bodies remain unchanged.','The actual saved trace shows command slot8 applied between ASYNC_ACTIVE and ASYNC_NBA before the failed strict check; this supports a product correction rather than a bench delay.','All10 original X/Z transition hold/resume cases stay intact. The new298-bit snapshot covers every pending payload/metadata field; valid/frontier and complete slot/cache/verdict arrays have separate strict four-state checks.','Removing the direct APPLY reset qualifier is a real source mutation reproducing the witnessed class of asynchronous write; the12th component fault must actually fail at the expected diagnostic in the fresh campaign.','Only the pending-fault prelude selects the already passing normal25-packet ring64/stall stream. Dense128-packet ring16/ready1 remains a separate test; all three pending badblock/capacity/fresh-restart boundaries are unchanged.','Detached source/tool pins, CPU6/2GiB, entry/continuous/terminal floors, owned polling/reaping/cancellation and no healthy deadline remain exact parent bodies.'],metadata_qualification='freeze04.current_test_scope is inherited stale prose42/11/no-execution. Authoritative current values are43 selected predicates with12 component faults and1 excludedMAX4118; actual prior40PASS2FAIL is preserved. This receipt does not rewrite the original freeze or erase history.',limits='Source/saved-byte review only. No producer or test import, compiler/HDL/native execution or signal. This additive review authorizes only frozen functional campaign after fresh resource/runtime checks; no actual03-to04 functionalPASS, timing, mapping/adoption, or general legacy unknown-state equivalence. Full-framer behavior across arbitrary unknown reset epochs remains outside the isolated command-component relation.')
q=B/'source-only-peer-rx04.json';assert not q.exists();q.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(peer=pin(q),inputs=302,changes=5,prior_actual=[40,2])))
