#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit Boolean-prefix control for the frozen four-DWORD integrity parser."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v3.v"
SOURCE_SHA = "ea9c978b14ce0b5d764cb87cdf82ce1e76aa2a83d1ed19eaf97f74aa800b2abb"


def control():
    return """ // BEGIN V4 PARALLEL CONTROL
 // Mode0 TOKEN,1 carried TLP,2 LOOK,3 DLLP,4 newly started TLP.
 // Modes5/6/7 stop while retaining TOKEN/LOOK/TLP respectively. Error and
 // EDS side effects remain in the original parser body. Initial ending
 // masks every word and holds all registered metadata, including state.
 // A newly accepted STP has at least5DWORDs and cannot finish in this slice.
 wire [3:0] control_stp,control_sdp,control_idl,control_eds,control_edb;
 wire [10:0] control_length[0:3];
 wire [12:0] control_encoded[0:3];
 wire [3:0] control_crc[0:3];
 wire [63:0] control_table[0:3];
 wire [63:0] control_prefix2,control_prefix3;
 wire [7:0] control_modes[0:3];
 wire [1:0] control_state[0:3];
 wire [3:0] control_active,control_bad_look,control_carry_end,control_header_first;
 wire [12:0] control_payload0=({crc_word[0][17:16],crc_word[0][31:24]}==0)?
   13'd4096:{1'b0,crc_word[0][17:16],crc_word[0][31:24],2'b00};
 wire [12:0] control_expected0=13'd18+(crc_word[0][5]?13'd4:13'd0)+
   (crc_word[0][6]?control_payload0:13'd0)+(crc_word[0][23]?13'd4:13'd0);
 wire control_carried_header_bad=header_first ?
   (crc_word[0][7] || packet_bytes!=control_expected0) :
   (header_bad || packet_bytes!=expected_bytes);
 function automatic [63:0] control_transition;
   input stp,sdp,idl,eds,edb,carry_end,carry_bad;
   reg [2:0] token_next,destination;
   integer source;
   begin
     token_next=idl?3'd0:eds?3'd5:stp?3'd4:sdp?3'd3:3'd5;
     control_transition=64'b0;
     for(source=0;source<8;source=source+1) begin
       case(source)
         0:destination=token_next;
         1:destination=carry_end?(carry_bad?3'd7:3'd2):3'd1;
         2:destination=edb?3'd0:(stp||sdp||idl||eds)?token_next:3'd6;
         3:destination=3'd0;
         4:destination=3'd4;
         5:destination=3'd5;
         6:destination=3'd6;
         default:destination=3'd7;
       endcase
       control_transition[destination*8+source]=1'b1;
     end
   end
 endfunction
 // Matrix bit[destination*8+source] represents one deterministic transition.
 // Independent composition removes the serial state-selected CRC/header path.
 function automatic [63:0] control_compose;
   input [63:0] later,earlier;
   integer destination,source;
   begin
     for(destination=0;destination<8;destination=destination+1)
       for(source=0;source<8;source=source+1)
         control_compose[destination*8+source]=
           (((later[destination*8+0]&earlier[0*8+source])|(later[destination*8+1]&earlier[1*8+source]))|
            ((later[destination*8+2]&earlier[2*8+source])|(later[destination*8+3]&earlier[3*8+source])))|
           (((later[destination*8+4]&earlier[4*8+source])|(later[destination*8+5]&earlier[5*8+source]))|
            ((later[destination*8+6]&earlier[6*8+source])|(later[destination*8+7]&earlier[7*8+source])));
   end
 endfunction
 function automatic [7:0] control_apply;
   input [63:0] matrix;
   input [7:0] initial_mode;
   integer destination;
   begin
     for(destination=0;destination<8;destination=destination+1)
       control_apply[destination]=
         (((matrix[destination*8+0]&initial_mode[0])|(matrix[destination*8+1]&initial_mode[1]))|
          ((matrix[destination*8+2]&initial_mode[2])|(matrix[destination*8+3]&initial_mode[3])))|
         (((matrix[destination*8+4]&initial_mode[4])|(matrix[destination*8+5]&initial_mode[5]))|
          ((matrix[destination*8+6]&initial_mode[6])|(matrix[destination*8+7]&initial_mode[7])));
   end
 endfunction
 assign control_modes[0]={4'b0,state==DLLP,state==LOOK,state==TLP,state==TOKEN};
 assign control_modes[1]=control_apply(control_table[0],control_modes[0]);
 assign control_prefix2=control_compose(control_table[1],control_table[0]);
 assign control_prefix3=control_compose(control_table[2],control_prefix2);
 assign control_modes[2]=control_apply(control_prefix2,control_modes[0]);
 assign control_modes[3]=control_apply(control_prefix3,control_modes[0]);
 genvar control_word;
 generate for(control_word=0;control_word<4;control_word=control_word+1) begin:control_decode
   assign control_length[control_word]={crc_word[control_word][14:8],crc_word[control_word][7:4]};
   assign control_encoded[control_word]={control_length[control_word],2'b00}-13'd2;
   assign control_crc[control_word][0]=control_length[control_word][10]^control_length[control_word][7]^control_length[control_word][6]^control_length[control_word][4]^control_length[control_word][2]^control_length[control_word][1]^control_length[control_word][0];
   assign control_crc[control_word][1]=control_length[control_word][10]^control_length[control_word][9]^control_length[control_word][7]^control_length[control_word][5]^control_length[control_word][4]^control_length[control_word][3]^control_length[control_word][2];
   assign control_crc[control_word][2]=control_length[control_word][9]^control_length[control_word][8]^control_length[control_word][6]^control_length[control_word][4]^control_length[control_word][3]^control_length[control_word][2]^control_length[control_word][1];
   assign control_crc[control_word][3]=control_length[control_word][8]^control_length[control_word][7]^control_length[control_word][5]^control_length[control_word][3]^control_length[control_word][2]^control_length[control_word][1]^control_length[control_word][0];
   assign control_stp[control_word]=crc_word[control_word][3:0]==4'hf &&
     control_length[control_word]>=5 && control_length[control_word]<1152 &&
     control_encoded[control_word]<=MAX_ENCODED_BYTES && control_crc[control_word]==crc_word[control_word][23:20] &&
     (^{control_length[control_word],crc_word[control_word][23:20],crc_word[control_word][15]})==1'b0;
   assign control_sdp[control_word]=crc_word[control_word][15:0]==16'hacf0;
   assign control_idl[control_word]=crc_word[control_word]==0;
   assign control_eds[control_word]=crc_word[control_word]==32'h0090801f && slice==3 && control_word==3;
   assign control_edb[control_word]=crc_word[control_word]==32'hc0c0c0c0;
   assign control_table[control_word]=control_transition(control_stp[control_word],control_sdp[control_word],
     control_idl[control_word],control_eds[control_word],control_edb[control_word],
     remaining==(control_word+1),control_carried_header_bad);
   assign control_active[control_word]=!ending && (|control_modes[control_word][4:0]);
   assign control_state[control_word]=ending?state:
     (control_modes[control_word][1]||control_modes[control_word][4]||control_modes[control_word][7])?TLP:
     (control_modes[control_word][2]||control_modes[control_word][6])?LOOK:
     control_modes[control_word][3]?DLLP:TOKEN;
   assign control_bad_look[control_word]=control_modes[control_word][2] &&
     !(control_edb[control_word]||control_stp[control_word]||control_sdp[control_word]||control_idl[control_word]||control_eds[control_word]);
   assign control_carry_end[control_word]=control_modes[control_word][1] && remaining==(control_word+1);
   if(control_word==0) begin:first
     assign control_header_first[control_word]=control_modes[control_word][1] && header_first;
   end else begin:following
     assign control_header_first[control_word]=control_modes[control_word][4] &&
       (control_modes[control_word-1][0]||control_modes[control_word-1][2]) && control_stp[control_word-1];
   end
 end endgenerate
 // END V4 PARALLEL CONTROL
"""


CHANGES = (
    (
        "     position=write_ptr+j;",
        "     position=write_ptr+j;state_n=control_state[j];",
    ),
    ("if(!token_failure && !ending_n) begin", "if(control_active[j]) begin"),
    (
        "if(!handled && !token_failure) begin",
        "if(!handled && !control_bad_look[j]) begin",
    ),
    ("if(header_first_n) begin", "if(control_header_first[j]) begin"),
    ("if(remaining_n==0) begin", "if(control_carry_end[j]) begin"),
    (
        "if(header_bad_n || bytes_n!=expected_n) token_failure=1;",
        "if(control_carried_header_bad) token_failure=1;",
    ),
)


def candidate():
    source = SOURCE.read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    for old, new in CHANGES:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    marker = " // END FIXED CRC CANDIDATES\n"
    assert source.count(marker) == 1
    source = source.replace(marker, marker + control())
    source = source.replace(
        "soc_pcie_gen3_framer_rx_integrity_v3", "soc_pcie_gen3_framer_rx_integrity_v4"
    )
    source = source.replace(
        "module soc_pcie_gen3_framer_rx_integrity_v4",
        "`default_nettype none\nmodule soc_pcie_gen3_framer_rx_integrity_v4",
        1,
    )
    return source.rstrip() + "\n`default_nettype wire\n"


if __name__ == "__main__":
    (SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v4.v")).write_text(candidate())
