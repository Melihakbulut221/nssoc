# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Static contract/source binding; no HDL generation or execution."""
from pathlib import Path
import hashlib,json,re
R=Path.cwd();B=Path(__file__).resolve().parent;C=B/'architecture-contract02.json';A=B/'integration-audit02.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
c=json.loads(C.read_text());a=json.loads(A.read_text());checked={}
for entry in c['inputs']+a['inputs']:
 p=Path(entry['path']);expected={k:entry[k]for k in ['bytes','sha256']};assert pin(p)==expected;checked[str(p)]=expected
old=(B/'architecture-contract01.json').read_text();assert C.read_text()==old.replace('Stable production baseline V11 unchanged.','Stable comparison baseline V11 unchanged.')
assert a['contract02']['sha256']==pin(C)['sha256'] and a['nondefinition_mentions']==0
actual=[]
for p in sorted((R/'hw/soc/rtl').rglob('*.v')):
 for line_no,line in enumerate(p.read_text().splitlines(),1):
  if re.search(r'\bsoc_pcie_gen3_continuous_rx_integrity_v(?:11|23)\b',line):actual.append(dict(path=str(p.relative_to(R)),line=line_no,text=line,module_definition=bool(re.match(r'\s*module\b',line))))
assert actual==a['rtl_exact_name_mentions']
source=Path(c['inputs'][0]['path']).read_text()
for phrase in ['wire [PW-1:0] occupied=write_ptr-read_ptr;','wire [PW-1:0] committed=commit_ptr-read_ptr;','state_n=state;commit_n=commit_ptr;','if(flush_i || stream_start_i) begin','end else if((stream_abort_i && active_o) || fault_now) begin','if(ending && read_ptr==write_ptr && !retire_valid && (!output_valid || ready_i)) begin','if(step) slot_verdict[cache_slot]<=next_value;']:
 assert phrase in source,phrase
fields=c['state_contract']['command_fields'];assert set(fields)=={'valid','address','data','keep','sop','eop','dllp','sequence','tags','verdict_enable','verdict_tags','verdict_value','commit'}
assert [fields[k]for k in ['data','keep','sop','eop','dllp','sequence','verdict_enable','verdict_value']]==[128,16,16,16,16,48,4,4]
for name in ['slot_data','slot_keep','slot_sop','slot_eop','slot_dllp','slot_sequence','slot_tag']:
 assert re.search(r'\b'+name+r'\[\(write_ptr\+w\)&\(RING_DWORDS-1\)\]<=',source)
assert c['implementation_started']is False and c['native_started']is False
checks=[
'Complete command includes preincrement address, all seven slot-array payload/metadata fields, ordered verdict writes and parser commit; no partial cache-only stage.',
'Parser commit remains separate from visible commit; existing commit_n default uses parser frontier. Slot/tag/verdict/cache application and visible frontier share one old-command edge, while retirement sees preedge visible state.',
'Old valid command applies independently of current step/current_valid/ending; simultaneous replacement uses NBA old fields. Bubble clears valid and cannot replay. EDS requires pending empty and both frontiers/read/write/descriptor/public drain.',
'Fault/reset/start/flush/abort invalidate command and both frontiers before new epoch; scoreboard uses actual preedge public handshake. Inaccessible array differences are explicitly allowed only behind invalid ownership.',
'Occupancy remains reserved write_ptr minus actual read_ptr. Pending command is not subtracted to create free space; extended tags and lane last-writer priority remain unchanged.',
'Nominal extra output cycle is a restricted testable hypothesis, not universal equivalence. Stalled/fault/capacity behavior uses independent transaction ownership scoreboard, exact once/in-order data and known fault diagnostics.',
'Required controls cover final zero-keep drain, pending invalidation, four lane collisions, literal X/Z/procedural controls, capacity/wrap/reuse, actual sustained throughput, and eight real command-stage mutations.',
'Mapped command Q-to-ring/cache/verdict D ancestry and exclusion of direct parser payload bypass remain explicit future gates; unchanged4ns timing is measured after functional peer and no adoption follows source contract alone.',
'Source-limited integration audit correctly observes only two current wrapper definitions and separate owned paths; event pulses remain parser-timed while visible data is delayed, requiring consumer audit before integration.'
]
r=dict(status='PASS_SOURCE_ONLY_V25_REGISTERED_RING_COMMAND_CONTRACT',contract=pin(C),integration_audit=pin(A),findings=[],method=pin(Path(__file__)),verified_inputs=checked,exact_contract01_to02_wording_delta=True,checks=checks,scope='Full temporal contract and relevant baseline parser/capacity/retire/writer/cache/control paths read; current named integration wrappers verified. This is permission to develop the separately reviewed experimental stage, not evidence of implemented function, universal cycle equivalence, timing gain, integration or adoption. No RTL or test generation, simulation, native mapping or source edit.',functional_acceptance=False,timing_acceptance=False,physical_acceptance=False)
(B/'architecture-source-peer-vco01.json').write_text(json.dumps(r,indent=2)+'\n');print(pin(B/'architecture-source-peer-vco01.json'))
