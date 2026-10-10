# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only architectural argument review; no product HDL or native execution."""
import datetime
import hashlib
import json
from pathlib import Path
import re
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
    p=Path(p)
    with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
contract=B/'architecture-contract01.json';c=json.loads(contract.read_text())
assert pin(contract)=={'bytes':5778,'sha256':'56fbfb6ebb1b0bcd8fffd9d4aa856a89509a6086e46c87b97d8e25f27b42fe04'}
for p,h in c['inputs'].items():assert pin(R/p)==h,p
rtl=(R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
functions={name:re.search(r' function automatic [^\n]* '+name+r';.*? endfunction',rtl,re.S)[0] for name in ('control_transition','control_compose','control_apply')}
transition=functions['control_transition']
assert "token_next=idl?3'd0:eds?3'd5:stp?3'd4:sdp?3'd3:3'd5;" in transition
assert "1:destination=carry_end?(carry_bad?3'd7:3'd2):3'd1;" in transition
assert "2:destination=edb?3'd0:(stp||sdp||idl||eds)?token_next:3'd6;" in transition
assert "control_transition=64'b0;" in transition and "control_transition[destination*8+source]=1'b1;" in transition
assert "assign control_modes[0]={4'b0,state==DLLP,state==LOOK,state==TLP,state==TOKEN};" in rtl
assert 'remaining==(control_word+1),control_carried_header_bad' in rtl
assert 'current_predecode[control_word*32+3] && slice==3 && control_word==3' in rtl
bank=rtl.split('// BEGIN V10 QUARANTINED BANK WRITER',1)[1].split('// END V10 QUARANTINED BANK WRITER',1)[0]
assert bank.index('if(step)')<bank.index('if(block_valid_i && block_ready_o)')
assert 'if(!current_valid || (last_slice && !next_valid))' in bank
assert c['bank_context']['bits_per_beat']==96 and c['bank_context']['bits_per_bank']==384
notes=[
 'Each noncarried transition destination is in {0,3,4,5,6,7}; no other column reaches mode1. A partially unknown ternary destination does not create a known1 in row1: the original indexed write into initializedzero must remain the actual HDL oracle.',
 'T_i fixes carry_end=0, so column1 is e1 and every other column equals M_i. Replacing M by T is exact on any prefix starting in0,2,3 because those prefixes never enter1; mode7 is absorbing.',
 'From initial e1, C0=c01 e1|c02 e2|c07 e7. Applying M1 gives c01 C1|c02 T1e2|c07e7. Applying M2 gives exactly the five terms declared for j3, because row7 absorbs and noncarried suffixes can use T. Bits9/17/57 are precisely destination1/2/7, source1.',
 'Original matrices remain known0/1, even with unknown token/carry inputs, only if actual Verilog unknown-index write suppression is retained. Original equality-derived initial bits are0/1/X and the upperfour bits are0. On this domain the bitwise AND/OR distributive expansion is valid; it does not permit direct ternary-to-boolean replacement or two-state-only validation.',
 'The context is attached to each accepted512bit bank, with four96bit beat records and no extra public latency. Context must shift96 when payload/predecode shift128, promote with next_valid, and preserve later same-edge acceptance override. Context capture belongs to the same quarantined contents writer, never a new validity/fault gate.',
 'Zero-filled reset/shift context must be computed from exact zero-word predecode semantics, not allzero context. Absolute EDS qualification stays only word15; the pre-word1/2/3 prefixes consume words0/1/2 of each beat, while original word3 decode and EDS processing remain unchanged.',
 'Review passes only this architecture contract. Actual literal HDL alphabet including X/Z indexed writes, all initial modes, context bank/shift/promotion/accept/reset/stall/EDS witnesses and meaningful negative controls remain implementation gates; no functional/native/timing result is asserted.'
]
r={'status':'PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_CONTRACT','contract':pin(contract),'findings':[],'inputs':c['inputs'],'exact_frozen_function_pins':{n:{'bytes':len(t.encode()),'sha256':hashlib.sha256(t.encode()).hexdigest()} for n,t in functions.items()},'bank_writer_scope_pin':{'bytes':len(bank.encode()),'sha256':hashlib.sha256(bank.encode()).hexdigest()},'reasoning':notes,'implementation_approved_as_proven':False,'HDL_or_native_executed':False,'timing_or_adoption_accepted':False,'method':pin(__file__),'utc':datetime.datetime.now(datetime.UTC).isoformat()}
with (B/'architecture-source-peer-rx01.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps({'status':r['status'],'peer':pin(B/'architecture-source-peer-rx01.json')}))
