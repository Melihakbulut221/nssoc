# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded independent contract review; no RTL or native execution."""
from pathlib import Path
import json,hashlib,datetime
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
cp=B/'architecture-contract01.json';sp=B/'architecture-contract02-observer.json'
assert pin(cp)==dict(bytes=11640,sha256='519f4a54ed675fcdf51af1653ed66a6d66220d3386b8d46adc358c2cff556cbe')
assert pin(sp)==dict(bytes=2053,sha256='cb8a50c42857b19b84306fc810fbbd48c3e5c413ea612750b3f04ba932fa881a')
c=json.loads(cp.read_text());s=json.loads(sp.read_text());assert s['contract']==pin(cp)
for row in [c['baseline'],*c['evidence'].values()]:assert pin(row['path'])=={k:row[k] for k in ('bytes','sha256')}
d=json.loads((B/'measured-cone-diagnosis04.json').read_text())
for p,e in d['inputs'].items():assert pin(p)==e,p
source=Path(c['baseline']['path']).read_text()
for exact in ["encoded={length,2'b00}-13'd2;",'predecode_word={encoded,value[7],expected',
 'current_predecode<={{4{predecode_word(32\'b0)}},current_predecode[511:128]};',
 'if(block_valid_i && block_ready_o)',
 'if(!current_valid || (last_slice && !next_valid))',
 'if(control_header_first[j]) begin',
 'if(control_carry_end[j]) begin',
 'wire control_carried_header_bad=header_first ?',
 '(current_predecode[18] || packet_bytes!=control_expected0) :',
 '(header_bad || packet_bytes!=expected_bytes);']:
 assert exact in source,exact
r=dict(status='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_ARCHITECTURE_CONTRACT',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),contract=pin(cp),observer_supplement=pin(sp),method=pin(__file__),baseline=c['baseline'],measured_diagnosis=pin(B/'measured-cone-diagnosis04.json'),diagnosis_inputs_rehashed=len(d['inputs']),findings=[],full_contract_read=True,baseline_source_scope='Independently read complete predecode functions, carried-header transition network, header/remaining parser branches, V10 bank writer and final state/fault/start/accept priorities. CRC arithmetic unmodified and not re-proved.',resolved_review_point=dict(issue='Global accepted_tail_valid sampled after acceptance is insufficient to prove the first DWORD relation had a valid predecessor.',resolution='Supplement02 records OLD tail-valid and accepted block/word identity in independent companion observer metadata; shifts/promotions/overwrites match actual bank ordering, with a separately classified observer-negative.',product_changed=False),reasoning=[
'Within an accepted block, predecode indexing is interleaved exactly as the baseline; predecessor j-1 encoded field and header j expected/format fields form the same operands that become packet_bytes/expected/header_bad.',
'Across blocks, previous accepted block tail is the required predecessor even when parser banks lag acceptance. Same-edge nonblocking semantics must use old tail, while updating to incoming DWORD15 only after that relation has been formed.',
'At carried first header in parser lane0, current relation0 can feed the original shared carry-bad control through the same beat, including minimum packet end at lane3. Subsequent beats use the captured packet mismatch. A new STP in lanes0..2 captures its header relation in that beat; lane3 captures next beat. Original minimum length prevents a new STP from completing its entire TLP within the remaining lanes of the same beat.',
'Ordinary payload values resembling STP do not create ownership. Only the unchanged control_header_first branch captures mismatch; valid packet relation remains stable until the next real owned header.',
'Current/next companion shifts and simultaneous promotion plus new acceptance must preserve the two original if-block priorities, including the incoming-current overwrite case. Fault-edge data copies may be invalid, but no next epoch owner may use stale tail or incomplete companion contents.',
'Original !=, logical|| and conditional mux preserve the selected four-state result; source peer and actual literal X/Z tests are still required. There is no claim for arbitrary corrupt internal state.',
'The measured203-load control network and four verdict priority muxes remain; input-to-relation-register path can become critical. This plan supports a measured experiment, not a promised timing gain.'],mandatory_followup=['Full generated-source inverse and independent implementation peer before controls/native.','Exact public V22 cycle miter with all17 existing cases plus every DWORD-position/bank/stall/reset/fault boundary; counted predecessor and mismatch witnesses.','All declared meaningful product mutants and separately classified observer negative must fail named semantic assertions.','Unchanged CPU6/2GiB profile, original4ns all-corner timing and optimized graph attribution before any acceptance.'],not_claimed=['RTL implemented','actual controls passed','new native graph analyzed','timing improvement','production adoption','full PHY or final-chip closure'])
p=B/'architecture-source-only-peer-rx01.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
