#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose parser-context block decisions and separate EDS from stream ending."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v7.v'
SOURCE_SHA='0ce36fcd2eb6beb8a4e70b223e949c39b7e2cf566f491728ec1945668956dce1'
CHANGES=(
 ('input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,',
  'input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,stream_stop_i,\n output wire block_decision_o,block_eds_o,'),
 ('assign block_ready_o=input_ready;',
  '''assign block_ready_o=input_ready && !stream_stop_i;
 // Exact accepted final DWORD slice, after token-context and CRC processing.
 // The PCS allows only one undecided quartet; a decision and next quartet may
 // share this edge. A payload matching EDS never changes this parser decision.
 assign block_decision_o=last_slice && !fault_now;
 assign block_eds_o=block_decision_o && ending_n;'''),
 ('header_first<=header_first_n;header_bad<=header_bad_n;ending<=ending_n;',
  'header_first<=header_first_n;header_bad<=header_bad_n;'),
 ('if(ending || (step && ending_n)) begin current_valid<=0;next_valid<=0;end',
  '''// EDS pauses at the PCS boundary while the ring continues to retire.
       // Only a complete EIOS/EIEOS cohort ends the actual Data Stream.
       if(stream_stop_i) ending<=1;
       if(ending || stream_stop_i) begin current_valid<=0;next_valid<=0;end'''),
)


def candidate():
    text=SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA
    for old,new in CHANGES:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    text=text.replace('integrity_v7','integrity_v8')
    return text


if __name__=='__main__':
    (SOURCE.with_name('soc_pcie_gen3_framer_rx_integrity_v8.v')).write_text(candidate())
