#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register literal DWORD decode beside the unchanged current/next block banks."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v7.v"
SOURCE_SHA = "0ce36fcd2eb6beb8a4e70b223e949c39b7e2cf566f491728ec1945668956dce1"


def predecode():
    return """ // BEGIN V9 REGISTERED WORD DECODE
 // Companion banks follow every literal current/next block load and shift.
 // Bits0..4 are STP/SDP/IDL/rawEDS/EDB,17:5 expected TLP bytes,
 // bit18 header format fault,31:19 encoded STP bytes. EDS position remains
 // qualified by the original slice/word test after these registers.
 function automatic [31:0] predecode_word;
   input [31:0] value;
   reg [10:0] length;
   reg [12:0] encoded,payload,expected;
   reg [3:0] check_crc;
   reg stp;
   begin
     length={value[14:8],value[7:4]};
     encoded={length,2'b00}-13'd2;
     check_crc[0]=length[10]^length[7]^length[6]^length[4]^length[2]^length[1]^length[0];
     check_crc[1]=length[10]^length[9]^length[7]^length[5]^length[4]^length[3]^length[2];
     check_crc[2]=length[9]^length[8]^length[6]^length[4]^length[3]^length[2]^length[1];
     check_crc[3]=length[8]^length[7]^length[5]^length[3]^length[2]^length[1]^length[0];
     stp=value[3:0]==4'hf && length>=5 && length<1152 &&
       encoded<=MAX_ENCODED_BYTES && check_crc==value[23:20] &&
       (^{length,value[23:20],value[15]})==1'b0;
     payload=({value[17:16],value[31:24]}==0)?13'd4096:{1'b0,value[17:16],value[31:24],2'b00};
     expected=13'd18+(value[5]?13'd4:13'd0)+(value[6]?payload:13'd0)+(value[23]?13'd4:13'd0);
     predecode_word={encoded,value[7],expected,value==32'hc0c0c0c0,
                     value==32'h0090801f,value==0,value[15:0]==16'hacf0,stp};
   end
 endfunction
 function automatic [511:0] predecode_block;
   input [511:0] value;
   integer index;
   begin
     for(index=0;index<16;index=index+1)
       predecode_block[index*32+:32]=predecode_word(
         {value[384+index*8+:8],value[256+index*8+:8],
          value[128+index*8+:8],value[index*8+:8]});
   end
 endfunction
 reg [511:0] current_predecode,next_predecode;
 wire [511:0] input_predecode=predecode_block(payload_i);
 // END V9 REGISTERED WORD DECODE
"""


CHANGES = (
    (
        " wire [12:0] control_expected0=13'd18+(crc_word[0][5]?13'd4:13'd0)+\n"
        "   (crc_word[0][6]?control_payload0:13'd0)+(crc_word[0][23]?13'd4:13'd0);",
        " wire [12:0] control_expected0=current_predecode[5+:13];",
    ),
    (
        "(crc_word[0][7] || packet_bytes!=control_expected0)",
        "(current_predecode[18] || packet_bytes!=control_expected0)",
    ),
    (
        "   assign control_encoded[control_word]={control_length[control_word],2'b00}-13'd2;",
        "   assign control_encoded[control_word]=current_predecode[control_word*32+19+:13];",
    ),
    (
        "   assign control_stp[control_word]=crc_word[control_word][3:0]==4'hf &&\n"
        "     control_length[control_word]>=5 && control_length[control_word]<1152 &&\n"
        "     control_encoded[control_word]<=MAX_ENCODED_BYTES && control_crc[control_word]==crc_word[control_word][23:20] &&\n"
        "     (^{control_length[control_word],crc_word[control_word][23:20],crc_word[control_word][15]})==1'b0;",
        "   assign control_stp[control_word]=current_predecode[control_word*32];",
    ),
    (
        "   assign control_sdp[control_word]=crc_word[control_word][15:0]==16'hacf0;",
        "   assign control_sdp[control_word]=current_predecode[control_word*32+1];",
    ),
    (
        "   assign control_idl[control_word]=crc_word[control_word]==0;",
        "   assign control_idl[control_word]=current_predecode[control_word*32+2];",
    ),
    (
        "   assign control_eds[control_word]=crc_word[control_word]==32'h0090801f && slice==3 && control_word==3;",
        "   assign control_eds[control_word]=current_predecode[control_word*32+3] && slice==3 && control_word==3;",
    ),
    (
        "   assign control_edb[control_word]=crc_word[control_word]==32'hc0c0c0c0;",
        "   assign control_edb[control_word]=current_predecode[control_word*32+4];",
    ),
    (
        "     length_dw={word[14:8],word[7:4]};encoded_bytes={length_dw,2'b00}-13'd2;",
        "     length_dw={word[14:8],word[7:4]};encoded_bytes=control_encoded[j];",
    ),
    (
        "     stp_ok=word[3:0]==4'hf && length_dw>=5 && length_dw<1152 &&\n"
        "       encoded_bytes<=MAX_ENCODED_BYTES && crc==word[23:20] &&\n"
        "       (^{length_dw,word[23:20],word[15]})==1'b0;\n"
        "     sdp_ok=word[15:0]==16'hacf0;idl_ok=word==0;\n"
        "     eds_ok=word==32'h0090801f && slice==3 && j==3;\n"
        "     edb_ok=word==32'hc0c0c0c0;handled=0;",
        "     stp_ok=control_stp[j];sdp_ok=control_sdp[j];idl_ok=control_idl[j];\n"
        "     eds_ok=control_eds[j];edb_ok=control_edb[j];handled=0;",
    ),
    (
        "               expected_n=13'd18+(word[5]?13'd4:13'd0)+(word[6]?tlp_payload:13'd0)+(word[23]?13'd4:13'd0);\n"
        "               header_bad_n=word[7];header_first_n=0;",
        "               expected_n=current_predecode[j*32+5+:13];\n"
        "               header_bad_n=current_predecode[j*32+18];header_first_n=0;",
    ),
    (
        "     state<=TOKEN;current_block<=0;next_block<=0;current_valid<=0;next_valid<=0;slice<=0;",
        "     state<=TOKEN;current_block<=0;next_block<=0;current_valid<=0;next_valid<=0;slice<=0;\n"
        "     current_predecode<=predecode_block(512'b0);next_predecode<=predecode_block(512'b0);",
    ),
    (
        "           if(next_valid) current_block<=next_block;",
        "           if(next_valid) begin current_block<=next_block;current_predecode<=next_predecode;end",
    ),
    (
        "                           32'b0,current_block[255:160],32'b0,current_block[127:32]};",
        "                           32'b0,current_block[255:160],32'b0,current_block[127:32]};\n"
        "           current_predecode<={{4{predecode_word(32'b0)}},current_predecode[511:128]};",
    ),
    (
        "         if(!current_valid || (last_slice && !next_valid)) begin current_block<=payload_i;current_valid<=1;slice<=0;end\n"
        "         else begin next_block<=payload_i;next_valid<=1;end",
        "         if(!current_valid || (last_slice && !next_valid)) begin\n"
        "           current_block<=payload_i;current_predecode<=input_predecode;current_valid<=1;slice<=0;end\n"
        "         else begin next_block<=payload_i;next_predecode<=input_predecode;next_valid<=1;end",
    ),
)


def candidate():
    source = SOURCE.read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    for before, after in CHANGES:
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    anchor = " reg [511:0] current_block,next_block;\n"
    assert source.count(anchor) == 1
    source = source.replace(anchor, anchor + predecode())
    return source.replace("integrity_v7", "integrity_v9")


if __name__ == "__main__":
    (ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v9.v").write_text(
        candidate()
    )
