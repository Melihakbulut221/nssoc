#!/usr/bin/env python3
"""Static independent diagnosis of the closed V25 literal component failure."""
import ast
import hashlib
import json
import re
from pathlib import Path

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = R / 'hw/soc/out/pcie-integrity-v25-20261006'
D = Path('/dev/shm/nssoc-integrity-v25-full-controls01/test_actual_command_temporal_r0')


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())


def section(text, a, z):
    start = text.index(a)
    return text[start:text.index(z,start)+len(z)]


def main():
    source = D / 'command.v'
    text = source.read_text()
    tb = text.split('module tb;',1)[1]
    candidate = text.split('module candidate(',1)[1].split('endmodule',1)[0]
    log = (D / 'simulation.log').read_text()
    assert 'command.v:387: V25_COMMAND_UNKNOWN_CONTROL_WRITES' in log
    assert 'Time: 12414 ' in log
    assert (D / 'compile.log').stat().st_size == 0
    assert '`timescale' not in text
    binary = (D / 'command.vvp').read_text()
    assert ':vpi_time_precision + 0;' in binary and '.timescale 0 0;' in binary
    test = R / 'sw/tests/test_pcie_gen3_integrity_v25_command.py'
    constants = {n.targets[0].id: n.value.value for n in ast.parse(test.read_text()).body
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)
        and isinstance(n.value,ast.Constant)}
    assert constants['TB'].strip() == ('module tb;' + tb).strip()
    rtl = R / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v'
    for a,z in [(' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP',' // END V25 COMMAND CAPTURE AND EPOCH OWNERSHIP'),
                ('       // BEGIN V25 APPLY OLD COMMAND','       // END V25 APPLY OLD COMMAND'),
                (' // BEGIN V6 SHARED OLD VERDICT READS',' // END V5 SLOT VERDICT CACHE')]:
        assert section(candidate,a,z) == section(rtl.read_text(),a,z)
    # Each tick is exactly three #1 delays. Counts before the unknown loop are
    # one initialization,4096 random,6 directed,then5 epochs*3 ticks.
    tick = section(tb,' task tick;',' endtask')
    assert tick.count('#1;') == 3
    base = (1+4096+6+5*3)*3
    first_hold = base+2*3
    t = (12414-first_hold)//9
    assert base == 12354 and first_hold == 12360 and t == 6
    assert t//2 == 3 and t%2 == 0
    assert "3:rst_ni=(t%2)?1'bz:1'bx;" in tb
    assert 'drive=0;\n   for(i=0;i<16;i=i+1)' in tb
    assert 'always @(posedge clk_i or negedge rst_ni)' in candidate
    assert 'if(enabled && command_valid) begin' in candidate
    assert 'if(enabled) begin\n       command_valid<=0;' in candidate
    assert 'wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;' in tb
    record = dict(status='SAVED_COMPONENT_FAILURE_LOCALIZED_ASYNC_RESET_X_EDGE_PENDING_DIAGNOSTIC',
        inputs={str(p):pin(p) for p in [source,D/'command.vvp',D/'compile.log',D/'simulation.log',test,rtl,
            B/'source-freeze03.json',B/'unknown-control-supplement02.json',B/'architecture-contract02.json']},
        fatal=dict(diagnostic='V25_COMMAND_UNKNOWN_CONTROL_WRITES',line=387,time_ticks=12414,
            declared_timescale=False,compiled_time_precision_exponent=0,kind_index=6,control='rst_ni 1 to X'),
        arithmetic=dict(tick_delay_units=3,pre_unknown_ticks=4118,pre_unknown_time=12354,
            first_unknown_hold_assertion_time=12360,per_kind_ticks=3,per_kind_time=9,kind=6),
        actual_failure_boundary='Both the pending-valid and visible-frontier hold assertions precede the failing slot/cache check and passed. The current fatal does not report which slot, metadata field or cache bit changed.',
        source_relation='Saved candidate CAPTURE/APPLY/cache sections equal exact frozen product. Original and candidate use asynchronous posedge-clock/negedge-reset procedural priority. A1-to-X reset change is itself a negedge, so these blocks can run before a later settled positive edge.',
        hypothesis='The bench changes drive to0, snapshots arrays and sets rst_ni toX without advancing simulation time. Continuous enabled/step update in event deltas; the two asynchronous always blocks can observe prior derived controls on that reset transition. The reported time precisely matches this edge. This is an event-order hypothesis from source and the actual fatal, not a rerun waveform observation.',
        classification='Unresolved asynchronous four-state ownership edge. The existing assertion conflates transition behavior with settled-X positive-edge hold. Do not declare a product pass or simply add a delay to hide the transition: first compare both literal original and candidate edge observations and determine the intended transition-level contract.',
        requested_diagnostic=['Pin an additive print-only derivative of the exact generated HDL.',
            'Record direct reset/flush/start/abort/active plus derived enabled/step at negedge reset, after NBA and at the next settled clock edge.',
            'Record original and candidate slot/cache values, pending command fields/valid and visible commit before/after; include kind and first differing index.',
            'Keep all original assertions, frozen product bytes and actual failure. A later fix needs independent additive source review and meaningful positive/negative retest.'],
        no_native_or_test_rerun=True,method=pin(__file__))
    with (B/'unknown-reset-saved-peer-rx01.json').open('x') as f:
        f.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],time_ticks=12414,kind=t,
        result=pin(B/'unknown-reset-saved-peer-rx01.json')),indent=2))


if __name__ == '__main__':
    main()
