#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve owned packet descriptors while exposing token-context PCS decisions."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_owned_v2.v'
SOURCE_SHA='a0e3dfe6f87d2ac538b44af34793e48813fb0c59692454b31ccff7bdf7ed288c'
CHANGES=(
 ('input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,',
  'input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,stream_stop_i,\n output wire block_decision_o,block_eds_o,'),
 ('assign block_ready_o=input_ready;',
  '''assign block_ready_o=input_ready && !stream_stop_i;
 // The last accepted DWORD slice decides the current DATA quartet. EDS is
 // recognized only in parser context, never by searching packet payload.
 assign block_decision_o=last_slice && !fault_now;
 assign block_eds_o=block_decision_o && ending_n;'''),
 ('header_first<=header_first_n;header_bad<=header_bad_n;ending<=ending_n;',
  'header_first<=header_first_n;header_bad<=header_bad_n;'),
 ('if(ending_n) begin current_valid<=0;next_valid<=0;end',
  '''// An EDS permits SKP and does not retire the ownership epoch. Complete
       // EIOS/EIEOS cohorts explicitly stop input and drain both descriptors
       // and good bodies; ownership is not released until both handshakes.
       if(stream_stop_i) ending<=1;
       if(ending || stream_stop_i) begin current_valid<=0;next_valid<=0;end'''),
)


def candidate():
    text=SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA
    for old,new in CHANGES:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    text=text.replace('owned_v2','owned_v3')
    text=text.replace('// Fixed aligned/deskewed, already descrambled x4 Data Blocks only.',
        '`default_nettype none\n// Owned CRC parser for complete, descrambled DATA quartets from strict PCS.')
    return text+'`default_nettype wire\n'


if __name__=='__main__':
    (SOURCE.with_name('soc_pcie_gen3_framer_rx_owned_v3.v')).write_text(candidate())
