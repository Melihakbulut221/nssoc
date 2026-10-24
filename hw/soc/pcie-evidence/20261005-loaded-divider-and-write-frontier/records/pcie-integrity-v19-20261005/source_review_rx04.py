# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only supplemental review of actual-failure stimulus repair."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze04.json').read_text());old=json.loads((B/'source-freeze03.json').read_text());assert f['previous_freeze']==pin(B/'source-freeze03.json')
for p,v in f['files'].items():assert pin(R/p)==v
changed=[p for p in f['files'] if f['files'][p]!=old['files'][p]]
name='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py';assert changed==[name]
before=(B/'freeze03-sources'/name).read_text();after=(R/name).read_text();assert pin(B/'freeze03-sources'/name)==old['files'][name]
addition='''            # Fill through an actual public overflow before resetting controls.
            # Every physical slot then contains a nonzero DLLP keep mask, so
            # the later fault's speculative zero/metadata writes must cause an
            # observed invalid-content difference, independent of prior tests.
            preload = wire_dllp(dllp(bytes.fromhex("a35c96e1"))) * (RING + 16)
            for preload_word in serial_words(preload + bytes(2048)):
                await p.cycle(preload_word, ready=False)
                if int(d.overflow_o.value):
                    break
            assert int(d.overflow_o.value) and int(d.halted_o.value)
            await p.begin()
'''
assert after.count(addition)==1 and after.replace(addition,'')==before
olddefs={x.name:ast.dump(x) for x in ast.parse(before).body if isinstance(x,(ast.AsyncFunctionDef,ast.FunctionDef,ast.ClassDef))};newdefs={x.name:ast.dump(x) for x in ast.parse(after).body if isinstance(x,(ast.AsyncFunctionDef,ast.FunctionDef,ast.ClassDef))};assert [n for n in olddefs if olddefs[n]!=newdefs[n]]==['fault_quarantine_restart_wrap_and_backpressure']
for literal in ['assert int(d.v19_invalid_difference_events.value) > before_diff','assert int(d.v19_fault_step_events.value) > before_fault','assert not int(d.overflow_o.value)','assert p.errors == before_errors + 1']:
 assert literal in before and literal in after
r=dict(status='PASS_SOURCE_ONLY_V19_QUARANTINED_SLOTS',freeze=pin(B/'source-freeze04.json'),findings=[],method=pin(__file__),source_pins=f['files'],prior_peer=pin(B/'source-only-peer-rx.json'),review=['Exact inverse removes only eleven new lines in the four-malformation/four-recovery oracle case. Product and eight other source files, first thirteen oracle cases and all public/occupied/cache miter predicates remain byte-identical.', 'The added stimulus sends valid nonzero DLLPs with ready false until measured public overflow and halt, asserts both and restarts through unchanged Ports.begin reset/start. It never changes DUT arrays or disables comparisons. Fixed RING+16 packet input plus idle tail bounds the prefill.', 'The original strict observed-invalid-difference, actual fault-step, held-output, parser-before-capacity, halted-drain and recovery/wrap assertions remain intact. Prefill is intended to produce a real stored-data difference; whether it does is still an actual functional gate, not assumed by this review.', 'Original source and actual 26-pass/1-failure campaign remain separate. Only affected full miter and changed direct case require a new run; previous successful unrelated controls need not be repeated.'],actual_new_simulation=False,physical_acceptance=False)
p=B/'source-only-peer-rx04.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
