// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Fixed aligned/deskewed, already descrambled x4 Data Blocks only.
// Four ordered DWORD steps per clock, no per-block load bubble. Packet data
// stays quarantined until CRC and immediate successor/EDB verdict resolve. Retirement
// preserves token slots and supplies per-byte masks, including multiple packet
// boundaries per beat. This is not SKP/OS search, CDC, a PMA or a complete PCS.
module soc_pcie_gen3_framer_rx_integrity_v1 #(
 parameter integer MAX_ENCODED_BYTES=150,
 parameter integer RING_DWORDS=(1 << $clog2((MAX_ENCODED_BYTES+2)/4+16))
)(
 input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input wire block_valid_i,output wire block_ready_o,
 input wire [7:0] headers_i,input wire [511:0] payload_i,
 input wire block_error_i,
 output wire valid_o,input wire ready_i,output wire [127:0] data_o,
 output wire [15:0] keep_o,sop_o,eop_o,dllp_o,
 output wire [47:0] sequence_o,
 output reg [3:0] packet_good_o,packet_nullified_o,packet_crc_bad_o,packet_dllp_o,
 output reg [47:0] packet_sequence_o,
 output wire framing_error_o,overflow_o,
 output reg stream_end_o,active_o,halted_o,
 output wire accepting_o
);
 // BEGIN GENERATED CRC FUNCTIONS -- generate_pcie_crc_parallel_v1.py
 function [31:0] crc32_16;
   input [31:0] state;
   input [15:0] data;
   begin
     crc32_16[0]=state[0]^state[4]^state[6]^state[7]^state[10]^state[16]^data[0]^data[4]^data[6]^data[7]^data[10];
     crc32_16[1]=state[1]^state[5]^state[7]^state[8]^state[11]^state[17]^data[1]^data[5]^data[7]^data[8]^data[11];
     crc32_16[2]=state[2]^state[6]^state[8]^state[9]^state[12]^state[18]^data[2]^data[6]^data[8]^data[9]^data[12];
     crc32_16[3]=state[3]^state[7]^state[9]^state[10]^state[13]^state[19]^data[3]^data[7]^data[9]^data[10]^data[13];
     crc32_16[4]=state[4]^state[8]^state[10]^state[11]^state[14]^state[20]^data[4]^data[8]^data[10]^data[11]^data[14];
     crc32_16[5]=state[5]^state[9]^state[11]^state[12]^state[15]^state[21]^data[5]^data[9]^data[11]^data[12]^data[15];
     crc32_16[6]=state[0]^state[4]^state[7]^state[12]^state[13]^state[22]^data[0]^data[4]^data[7]^data[12]^data[13];
     crc32_16[7]=state[1]^state[5]^state[8]^state[13]^state[14]^state[23]^data[1]^data[5]^data[8]^data[13]^data[14];
     crc32_16[8]=state[0]^state[2]^state[6]^state[9]^state[14]^state[15]^state[24]^data[0]^data[2]^data[6]^data[9]^data[14]^data[15];
     crc32_16[9]=state[1]^state[3]^state[4]^state[6]^state[15]^state[25]^data[1]^data[3]^data[4]^data[6]^data[15];
     crc32_16[10]=state[2]^state[5]^state[6]^state[10]^state[26]^data[2]^data[5]^data[6]^data[10];
     crc32_16[11]=state[3]^state[6]^state[7]^state[11]^state[27]^data[3]^data[6]^data[7]^data[11];
     crc32_16[12]=state[0]^state[4]^state[7]^state[8]^state[12]^state[28]^data[0]^data[4]^data[7]^data[8]^data[12];
     crc32_16[13]=state[0]^state[1]^state[5]^state[8]^state[9]^state[13]^state[29]^data[0]^data[1]^data[5]^data[8]^data[9]^data[13];
     crc32_16[14]=state[1]^state[2]^state[6]^state[9]^state[10]^state[14]^state[30]^data[1]^data[2]^data[6]^data[9]^data[10]^data[14];
     crc32_16[15]=state[2]^state[3]^state[7]^state[10]^state[11]^state[15]^state[31]^data[2]^data[3]^data[7]^data[10]^data[11]^data[15];
     crc32_16[16]=state[0]^state[3]^state[6]^state[7]^state[8]^state[10]^state[11]^state[12]^data[0]^data[3]^data[6]^data[7]^data[8]^data[10]^data[11]^data[12];
     crc32_16[17]=state[0]^state[1]^state[4]^state[7]^state[8]^state[9]^state[11]^state[12]^state[13]^data[0]^data[1]^data[4]^data[7]^data[8]^data[9]^data[11]^data[12]^data[13];
     crc32_16[18]=state[1]^state[2]^state[5]^state[8]^state[9]^state[10]^state[12]^state[13]^state[14]^data[1]^data[2]^data[5]^data[8]^data[9]^data[10]^data[12]^data[13]^data[14];
     crc32_16[19]=state[0]^state[2]^state[3]^state[6]^state[9]^state[10]^state[11]^state[13]^state[14]^state[15]^data[0]^data[2]^data[3]^data[6]^data[9]^data[10]^data[11]^data[13]^data[14]^data[15];
     crc32_16[20]=state[0]^state[1]^state[3]^state[6]^state[11]^state[12]^state[14]^state[15]^data[0]^data[1]^data[3]^data[6]^data[11]^data[12]^data[14]^data[15];
     crc32_16[21]=state[1]^state[2]^state[6]^state[10]^state[12]^state[13]^state[15]^data[1]^data[2]^data[6]^data[10]^data[12]^data[13]^data[15];
     crc32_16[22]=state[2]^state[3]^state[4]^state[6]^state[10]^state[11]^state[13]^state[14]^data[2]^data[3]^data[4]^data[6]^data[10]^data[11]^data[13]^data[14];
     crc32_16[23]=state[3]^state[4]^state[5]^state[7]^state[11]^state[12]^state[14]^state[15]^data[3]^data[4]^data[5]^data[7]^data[11]^data[12]^data[14]^data[15];
     crc32_16[24]=state[0]^state[5]^state[7]^state[8]^state[10]^state[12]^state[13]^state[15]^data[0]^data[5]^data[7]^data[8]^data[10]^data[12]^data[13]^data[15];
     crc32_16[25]=state[1]^state[4]^state[7]^state[8]^state[9]^state[10]^state[11]^state[13]^state[14]^data[1]^data[4]^data[7]^data[8]^data[9]^data[10]^data[11]^data[13]^data[14];
     crc32_16[26]=state[2]^state[5]^state[8]^state[9]^state[10]^state[11]^state[12]^state[14]^state[15]^data[2]^data[5]^data[8]^data[9]^data[10]^data[11]^data[12]^data[14]^data[15];
     crc32_16[27]=state[0]^state[3]^state[4]^state[7]^state[9]^state[11]^state[12]^state[13]^state[15]^data[0]^data[3]^data[4]^data[7]^data[9]^data[11]^data[12]^data[13]^data[15];
     crc32_16[28]=state[0]^state[1]^state[5]^state[6]^state[7]^state[8]^state[12]^state[13]^state[14]^data[0]^data[1]^data[5]^data[6]^data[7]^data[8]^data[12]^data[13]^data[14];
     crc32_16[29]=state[1]^state[2]^state[6]^state[7]^state[8]^state[9]^state[13]^state[14]^state[15]^data[1]^data[2]^data[6]^data[7]^data[8]^data[9]^data[13]^data[14]^data[15];
     crc32_16[30]=state[2]^state[3]^state[4]^state[6]^state[8]^state[9]^state[14]^state[15]^data[2]^data[3]^data[4]^data[6]^data[8]^data[9]^data[14]^data[15];
     crc32_16[31]=state[3]^state[5]^state[6]^state[9]^state[15]^data[3]^data[5]^data[6]^data[9]^data[15];
   end
 endfunction
 function [31:0] crc32_32;
   input [31:0] state;
   input [31:0] data;
   begin
     crc32_32[0]=state[0]^state[1]^state[2]^state[3]^state[4]^state[6]^state[7]^state[8]^state[16]^state[20]^state[22]^state[23]^state[26]^data[0]^data[1]^data[2]^data[3]^data[4]^data[6]^data[7]^data[8]^data[16]^data[20]^data[22]^data[23]^data[26];
     crc32_32[1]=state[1]^state[2]^state[3]^state[4]^state[5]^state[7]^state[8]^state[9]^state[17]^state[21]^state[23]^state[24]^state[27]^data[1]^data[2]^data[3]^data[4]^data[5]^data[7]^data[8]^data[9]^data[17]^data[21]^data[23]^data[24]^data[27];
     crc32_32[2]=state[0]^state[2]^state[3]^state[4]^state[5]^state[6]^state[8]^state[9]^state[10]^state[18]^state[22]^state[24]^state[25]^state[28]^data[0]^data[2]^data[3]^data[4]^data[5]^data[6]^data[8]^data[9]^data[10]^data[18]^data[22]^data[24]^data[25]^data[28];
     crc32_32[3]=state[1]^state[3]^state[4]^state[5]^state[6]^state[7]^state[9]^state[10]^state[11]^state[19]^state[23]^state[25]^state[26]^state[29]^data[1]^data[3]^data[4]^data[5]^data[6]^data[7]^data[9]^data[10]^data[11]^data[19]^data[23]^data[25]^data[26]^data[29];
     crc32_32[4]=state[2]^state[4]^state[5]^state[6]^state[7]^state[8]^state[10]^state[11]^state[12]^state[20]^state[24]^state[26]^state[27]^state[30]^data[2]^data[4]^data[5]^data[6]^data[7]^data[8]^data[10]^data[11]^data[12]^data[20]^data[24]^data[26]^data[27]^data[30];
     crc32_32[5]=state[0]^state[3]^state[5]^state[6]^state[7]^state[8]^state[9]^state[11]^state[12]^state[13]^state[21]^state[25]^state[27]^state[28]^state[31]^data[0]^data[3]^data[5]^data[6]^data[7]^data[8]^data[9]^data[11]^data[12]^data[13]^data[21]^data[25]^data[27]^data[28]^data[31];
     crc32_32[6]=state[0]^state[2]^state[3]^state[9]^state[10]^state[12]^state[13]^state[14]^state[16]^state[20]^state[23]^state[28]^state[29]^data[0]^data[2]^data[3]^data[9]^data[10]^data[12]^data[13]^data[14]^data[16]^data[20]^data[23]^data[28]^data[29];
     crc32_32[7]=state[1]^state[3]^state[4]^state[10]^state[11]^state[13]^state[14]^state[15]^state[17]^state[21]^state[24]^state[29]^state[30]^data[1]^data[3]^data[4]^data[10]^data[11]^data[13]^data[14]^data[15]^data[17]^data[21]^data[24]^data[29]^data[30];
     crc32_32[8]=state[0]^state[2]^state[4]^state[5]^state[11]^state[12]^state[14]^state[15]^state[16]^state[18]^state[22]^state[25]^state[30]^state[31]^data[0]^data[2]^data[4]^data[5]^data[11]^data[12]^data[14]^data[15]^data[16]^data[18]^data[22]^data[25]^data[30]^data[31];
     crc32_32[9]=state[0]^state[2]^state[4]^state[5]^state[7]^state[8]^state[12]^state[13]^state[15]^state[17]^state[19]^state[20]^state[22]^state[31]^data[0]^data[2]^data[4]^data[5]^data[7]^data[8]^data[12]^data[13]^data[15]^data[17]^data[19]^data[20]^data[22]^data[31];
     crc32_32[10]=state[0]^state[2]^state[4]^state[5]^state[7]^state[9]^state[13]^state[14]^state[18]^state[21]^state[22]^state[26]^data[0]^data[2]^data[4]^data[5]^data[7]^data[9]^data[13]^data[14]^data[18]^data[21]^data[22]^data[26];
     crc32_32[11]=state[1]^state[3]^state[5]^state[6]^state[8]^state[10]^state[14]^state[15]^state[19]^state[22]^state[23]^state[27]^data[1]^data[3]^data[5]^data[6]^data[8]^data[10]^data[14]^data[15]^data[19]^data[22]^data[23]^data[27];
     crc32_32[12]=state[2]^state[4]^state[6]^state[7]^state[9]^state[11]^state[15]^state[16]^state[20]^state[23]^state[24]^state[28]^data[2]^data[4]^data[6]^data[7]^data[9]^data[11]^data[15]^data[16]^data[20]^data[23]^data[24]^data[28];
     crc32_32[13]=state[0]^state[3]^state[5]^state[7]^state[8]^state[10]^state[12]^state[16]^state[17]^state[21]^state[24]^state[25]^state[29]^data[0]^data[3]^data[5]^data[7]^data[8]^data[10]^data[12]^data[16]^data[17]^data[21]^data[24]^data[25]^data[29];
     crc32_32[14]=state[0]^state[1]^state[4]^state[6]^state[8]^state[9]^state[11]^state[13]^state[17]^state[18]^state[22]^state[25]^state[26]^state[30]^data[0]^data[1]^data[4]^data[6]^data[8]^data[9]^data[11]^data[13]^data[17]^data[18]^data[22]^data[25]^data[26]^data[30];
     crc32_32[15]=state[1]^state[2]^state[5]^state[7]^state[9]^state[10]^state[12]^state[14]^state[18]^state[19]^state[23]^state[26]^state[27]^state[31]^data[1]^data[2]^data[5]^data[7]^data[9]^data[10]^data[12]^data[14]^data[18]^data[19]^data[23]^data[26]^data[27]^data[31];
     crc32_32[16]=state[1]^state[4]^state[7]^state[10]^state[11]^state[13]^state[15]^state[16]^state[19]^state[22]^state[23]^state[24]^state[26]^state[27]^state[28]^data[1]^data[4]^data[7]^data[10]^data[11]^data[13]^data[15]^data[16]^data[19]^data[22]^data[23]^data[24]^data[26]^data[27]^data[28];
     crc32_32[17]=state[2]^state[5]^state[8]^state[11]^state[12]^state[14]^state[16]^state[17]^state[20]^state[23]^state[24]^state[25]^state[27]^state[28]^state[29]^data[2]^data[5]^data[8]^data[11]^data[12]^data[14]^data[16]^data[17]^data[20]^data[23]^data[24]^data[25]^data[27]^data[28]^data[29];
     crc32_32[18]=state[0]^state[3]^state[6]^state[9]^state[12]^state[13]^state[15]^state[17]^state[18]^state[21]^state[24]^state[25]^state[26]^state[28]^state[29]^state[30]^data[0]^data[3]^data[6]^data[9]^data[12]^data[13]^data[15]^data[17]^data[18]^data[21]^data[24]^data[25]^data[26]^data[28]^data[29]^data[30];
     crc32_32[19]=state[0]^state[1]^state[4]^state[7]^state[10]^state[13]^state[14]^state[16]^state[18]^state[19]^state[22]^state[25]^state[26]^state[27]^state[29]^state[30]^state[31]^data[0]^data[1]^data[4]^data[7]^data[10]^data[13]^data[14]^data[16]^data[18]^data[19]^data[22]^data[25]^data[26]^data[27]^data[29]^data[30]^data[31];
     crc32_32[20]=state[0]^state[3]^state[4]^state[5]^state[6]^state[7]^state[11]^state[14]^state[15]^state[16]^state[17]^state[19]^state[22]^state[27]^state[28]^state[30]^state[31]^data[0]^data[3]^data[4]^data[5]^data[6]^data[7]^data[11]^data[14]^data[15]^data[16]^data[17]^data[19]^data[22]^data[27]^data[28]^data[30]^data[31];
     crc32_32[21]=state[0]^state[2]^state[3]^state[5]^state[12]^state[15]^state[17]^state[18]^state[22]^state[26]^state[28]^state[29]^state[31]^data[0]^data[2]^data[3]^data[5]^data[12]^data[15]^data[17]^data[18]^data[22]^data[26]^data[28]^data[29]^data[31];
     crc32_32[22]=state[2]^state[7]^state[8]^state[13]^state[18]^state[19]^state[20]^state[22]^state[26]^state[27]^state[29]^state[30]^data[2]^data[7]^data[8]^data[13]^data[18]^data[19]^data[20]^data[22]^data[26]^data[27]^data[29]^data[30];
     crc32_32[23]=state[0]^state[3]^state[8]^state[9]^state[14]^state[19]^state[20]^state[21]^state[23]^state[27]^state[28]^state[30]^state[31]^data[0]^data[3]^data[8]^data[9]^data[14]^data[19]^data[20]^data[21]^data[23]^data[27]^data[28]^data[30]^data[31];
     crc32_32[24]=state[2]^state[3]^state[6]^state[7]^state[8]^state[9]^state[10]^state[15]^state[16]^state[21]^state[23]^state[24]^state[26]^state[28]^state[29]^state[31]^data[2]^data[3]^data[6]^data[7]^data[8]^data[9]^data[10]^data[15]^data[16]^data[21]^data[23]^data[24]^data[26]^data[28]^data[29]^data[31];
     crc32_32[25]=state[1]^state[2]^state[6]^state[9]^state[10]^state[11]^state[17]^state[20]^state[23]^state[24]^state[25]^state[26]^state[27]^state[29]^state[30]^data[1]^data[2]^data[6]^data[9]^data[10]^data[11]^data[17]^data[20]^data[23]^data[24]^data[25]^data[26]^data[27]^data[29]^data[30];
     crc32_32[26]=state[2]^state[3]^state[7]^state[10]^state[11]^state[12]^state[18]^state[21]^state[24]^state[25]^state[26]^state[27]^state[28]^state[30]^state[31]^data[2]^data[3]^data[7]^data[10]^data[11]^data[12]^data[18]^data[21]^data[24]^data[25]^data[26]^data[27]^data[28]^data[30]^data[31];
     crc32_32[27]=state[0]^state[1]^state[2]^state[6]^state[7]^state[11]^state[12]^state[13]^state[16]^state[19]^state[20]^state[23]^state[25]^state[27]^state[28]^state[29]^state[31]^data[0]^data[1]^data[2]^data[6]^data[7]^data[11]^data[12]^data[13]^data[16]^data[19]^data[20]^data[23]^data[25]^data[27]^data[28]^data[29]^data[31];
     crc32_32[28]=state[0]^state[4]^state[6]^state[12]^state[13]^state[14]^state[16]^state[17]^state[21]^state[22]^state[23]^state[24]^state[28]^state[29]^state[30]^data[0]^data[4]^data[6]^data[12]^data[13]^data[14]^data[16]^data[17]^data[21]^data[22]^data[23]^data[24]^data[28]^data[29]^data[30];
     crc32_32[29]=state[0]^state[1]^state[5]^state[7]^state[13]^state[14]^state[15]^state[17]^state[18]^state[22]^state[23]^state[24]^state[25]^state[29]^state[30]^state[31]^data[0]^data[1]^data[5]^data[7]^data[13]^data[14]^data[15]^data[17]^data[18]^data[22]^data[23]^data[24]^data[25]^data[29]^data[30]^data[31];
     crc32_32[30]=state[3]^state[4]^state[7]^state[14]^state[15]^state[18]^state[19]^state[20]^state[22]^state[24]^state[25]^state[30]^state[31]^data[3]^data[4]^data[7]^data[14]^data[15]^data[18]^data[19]^data[20]^data[22]^data[24]^data[25]^data[30]^data[31];
     crc32_32[31]=state[0]^state[1]^state[2]^state[3]^state[5]^state[6]^state[7]^state[15]^state[19]^state[21]^state[22]^state[25]^state[31]^data[0]^data[1]^data[2]^data[3]^data[5]^data[6]^data[7]^data[15]^data[19]^data[21]^data[22]^data[25]^data[31];
   end
 endfunction
 function [15:0] crc16_16;
   input [15:0] state;
   input [15:0] data;
   begin
     crc16_16[0]=state[1]^state[3]^state[4]^state[8]^state[12]^data[1]^data[3]^data[4]^data[8]^data[12];
     crc16_16[1]=state[2]^state[4]^state[5]^state[9]^state[13]^data[2]^data[4]^data[5]^data[9]^data[13];
     crc16_16[2]=state[3]^state[5]^state[6]^state[10]^state[14]^data[3]^data[5]^data[6]^data[10]^data[14];
     crc16_16[3]=state[4]^state[6]^state[7]^state[11]^state[15]^data[4]^data[6]^data[7]^data[11]^data[15];
     crc16_16[4]=state[0]^state[1]^state[3]^state[4]^state[5]^state[7]^data[0]^data[1]^data[3]^data[4]^data[5]^data[7];
     crc16_16[5]=state[0]^state[1]^state[2]^state[4]^state[5]^state[6]^state[8]^data[0]^data[1]^data[2]^data[4]^data[5]^data[6]^data[8];
     crc16_16[6]=state[1]^state[2]^state[3]^state[5]^state[6]^state[7]^state[9]^data[1]^data[2]^data[3]^data[5]^data[6]^data[7]^data[9];
     crc16_16[7]=state[0]^state[2]^state[3]^state[4]^state[6]^state[7]^state[8]^state[10]^data[0]^data[2]^data[3]^data[4]^data[6]^data[7]^data[8]^data[10];
     crc16_16[8]=state[0]^state[1]^state[3]^state[4]^state[5]^state[7]^state[8]^state[9]^state[11]^data[0]^data[1]^data[3]^data[4]^data[5]^data[7]^data[8]^data[9]^data[11];
     crc16_16[9]=state[0]^state[1]^state[2]^state[4]^state[5]^state[6]^state[8]^state[9]^state[10]^state[12]^data[0]^data[1]^data[2]^data[4]^data[5]^data[6]^data[8]^data[9]^data[10]^data[12];
     crc16_16[10]=state[0]^state[1]^state[2]^state[3]^state[5]^state[6]^state[7]^state[9]^state[10]^state[11]^state[13]^data[0]^data[1]^data[2]^data[3]^data[5]^data[6]^data[7]^data[9]^data[10]^data[11]^data[13];
     crc16_16[11]=state[0]^state[1]^state[2]^state[3]^state[4]^state[6]^state[7]^state[8]^state[10]^state[11]^state[12]^state[14]^data[0]^data[1]^data[2]^data[3]^data[4]^data[6]^data[7]^data[8]^data[10]^data[11]^data[12]^data[14];
     crc16_16[12]=state[0]^state[1]^state[2]^state[3]^state[4]^state[5]^state[7]^state[8]^state[9]^state[11]^state[12]^state[13]^state[15]^data[0]^data[1]^data[2]^data[3]^data[4]^data[5]^data[7]^data[8]^data[9]^data[11]^data[12]^data[13]^data[15];
     crc16_16[13]=state[0]^state[2]^state[5]^state[6]^state[9]^state[10]^state[13]^state[14]^data[0]^data[2]^data[5]^data[6]^data[9]^data[10]^data[13]^data[14];
     crc16_16[14]=state[0]^state[1]^state[3]^state[6]^state[7]^state[10]^state[11]^state[14]^state[15]^data[0]^data[1]^data[3]^data[6]^data[7]^data[10]^data[11]^data[14]^data[15];
     crc16_16[15]=state[0]^state[2]^state[3]^state[7]^state[11]^state[15]^data[0]^data[2]^data[3]^data[7]^data[11]^data[15];
   end
 endfunction
 function [15:0] crc16_32;
   input [15:0] state;
   input [31:0] data;
   begin
     crc16_32[0]=state[0]^state[1]^state[3]^state[4]^state[6]^state[9]^state[11]^state[12]^data[0]^data[1]^data[3]^data[4]^data[6]^data[9]^data[11]^data[12]^data[17]^data[19]^data[20]^data[24]^data[28];
     crc16_32[1]=state[1]^state[2]^state[4]^state[5]^state[7]^state[10]^state[12]^state[13]^data[1]^data[2]^data[4]^data[5]^data[7]^data[10]^data[12]^data[13]^data[18]^data[20]^data[21]^data[25]^data[29];
     crc16_32[2]=state[0]^state[2]^state[3]^state[5]^state[6]^state[8]^state[11]^state[13]^state[14]^data[0]^data[2]^data[3]^data[5]^data[6]^data[8]^data[11]^data[13]^data[14]^data[19]^data[21]^data[22]^data[26]^data[30];
     crc16_32[3]=state[1]^state[3]^state[4]^state[6]^state[7]^state[9]^state[12]^state[14]^state[15]^data[1]^data[3]^data[4]^data[6]^data[7]^data[9]^data[12]^data[14]^data[15]^data[20]^data[22]^data[23]^data[27]^data[31];
     crc16_32[4]=state[0]^state[1]^state[2]^state[3]^state[5]^state[6]^state[7]^state[8]^state[9]^state[10]^state[11]^state[12]^state[13]^state[15]^data[0]^data[1]^data[2]^data[3]^data[5]^data[6]^data[7]^data[8]^data[9]^data[10]^data[11]^data[12]^data[13]^data[15]^data[16]^data[17]^data[19]^data[20]^data[21]^data[23];
     crc16_32[5]=state[0]^state[1]^state[2]^state[3]^state[4]^state[6]^state[7]^state[8]^state[9]^state[10]^state[11]^state[12]^state[13]^state[14]^data[0]^data[1]^data[2]^data[3]^data[4]^data[6]^data[7]^data[8]^data[9]^data[10]^data[11]^data[12]^data[13]^data[14]^data[16]^data[17]^data[18]^data[20]^data[21]^data[22]^data[24];
     crc16_32[6]=state[0]^state[1]^state[2]^state[3]^state[4]^state[5]^state[7]^state[8]^state[9]^state[10]^state[11]^state[12]^state[13]^state[14]^state[15]^data[0]^data[1]^data[2]^data[3]^data[4]^data[5]^data[7]^data[8]^data[9]^data[10]^data[11]^data[12]^data[13]^data[14]^data[15]^data[17]^data[18]^data[19]^data[21]^data[22]^data[23]^data[25];
     crc16_32[7]=state[1]^state[2]^state[3]^state[4]^state[5]^state[6]^state[8]^state[9]^state[10]^state[11]^state[12]^state[13]^state[14]^state[15]^data[1]^data[2]^data[3]^data[4]^data[5]^data[6]^data[8]^data[9]^data[10]^data[11]^data[12]^data[13]^data[14]^data[15]^data[16]^data[18]^data[19]^data[20]^data[22]^data[23]^data[24]^data[26];
     crc16_32[8]=state[2]^state[3]^state[4]^state[5]^state[6]^state[7]^state[9]^state[10]^state[11]^state[12]^state[13]^state[14]^state[15]^data[2]^data[3]^data[4]^data[5]^data[6]^data[7]^data[9]^data[10]^data[11]^data[12]^data[13]^data[14]^data[15]^data[16]^data[17]^data[19]^data[20]^data[21]^data[23]^data[24]^data[25]^data[27];
     crc16_32[9]=state[3]^state[4]^state[5]^state[6]^state[7]^state[8]^state[10]^state[11]^state[12]^state[13]^state[14]^state[15]^data[3]^data[4]^data[5]^data[6]^data[7]^data[8]^data[10]^data[11]^data[12]^data[13]^data[14]^data[15]^data[16]^data[17]^data[18]^data[20]^data[21]^data[22]^data[24]^data[25]^data[26]^data[28];
     crc16_32[10]=state[4]^state[5]^state[6]^state[7]^state[8]^state[9]^state[11]^state[12]^state[13]^state[14]^state[15]^data[4]^data[5]^data[6]^data[7]^data[8]^data[9]^data[11]^data[12]^data[13]^data[14]^data[15]^data[16]^data[17]^data[18]^data[19]^data[21]^data[22]^data[23]^data[25]^data[26]^data[27]^data[29];
     crc16_32[11]=state[0]^state[5]^state[6]^state[7]^state[8]^state[9]^state[10]^state[12]^state[13]^state[14]^state[15]^data[0]^data[5]^data[6]^data[7]^data[8]^data[9]^data[10]^data[12]^data[13]^data[14]^data[15]^data[16]^data[17]^data[18]^data[19]^data[20]^data[22]^data[23]^data[24]^data[26]^data[27]^data[28]^data[30];
     crc16_32[12]=state[0]^state[1]^state[6]^state[7]^state[8]^state[9]^state[10]^state[11]^state[13]^state[14]^state[15]^data[0]^data[1]^data[6]^data[7]^data[8]^data[9]^data[10]^data[11]^data[13]^data[14]^data[15]^data[16]^data[17]^data[18]^data[19]^data[20]^data[21]^data[23]^data[24]^data[25]^data[27]^data[28]^data[29]^data[31];
     crc16_32[13]=state[0]^state[2]^state[3]^state[4]^state[6]^state[7]^state[8]^state[10]^state[14]^state[15]^data[0]^data[2]^data[3]^data[4]^data[6]^data[7]^data[8]^data[10]^data[14]^data[15]^data[16]^data[18]^data[21]^data[22]^data[25]^data[26]^data[29]^data[30];
     crc16_32[14]=state[0]^state[1]^state[3]^state[4]^state[5]^state[7]^state[8]^state[9]^state[11]^state[15]^data[0]^data[1]^data[3]^data[4]^data[5]^data[7]^data[8]^data[9]^data[11]^data[15]^data[16]^data[17]^data[19]^data[22]^data[23]^data[26]^data[27]^data[30]^data[31];
     crc16_32[15]=state[0]^state[2]^state[3]^state[5]^state[8]^state[10]^state[11]^data[0]^data[2]^data[3]^data[5]^data[8]^data[10]^data[11]^data[16]^data[18]^data[19]^data[23]^data[27]^data[31];
   end
 endfunction
 // END GENERATED CRC FUNCTIONS
 localparam integer AW=$clog2(RING_DWORDS);
 localparam integer PW=AW+1;
 localparam [1:0] TOKEN=0,TLP=1,LOOK=2,DLLP=3;
 reg [1:0] state,state_n;
 reg [31:0] lcrc,lcrc_n;
 reg [15:0] dllp_crc,dllp_crc_n;
 reg [511:0] current_block,next_block;
 reg current_valid,next_valid;
 reg [1:0] slice;
 reg [PW-1:0] write_ptr,read_ptr,commit_ptr,commit_n,packet_tag,tag_n;
 reg [12:0] packet_bytes,bytes_n,expected_bytes,expected_n;
 reg [10:0] remaining,remaining_n;
 reg [11:0] packet_sequence,sequence_n;
 reg header_first,header_first_n,header_bad,header_bad_n,ending,ending_n;
 reg [31:0] slot_data [0:RING_DWORDS-1];
 reg [3:0] slot_keep [0:RING_DWORDS-1];
 reg [3:0] slot_sop [0:RING_DWORDS-1];
 reg [3:0] slot_eop [0:RING_DWORDS-1];
 reg [3:0] slot_dllp [0:RING_DWORDS-1];
 reg [11:0] slot_sequence [0:RING_DWORDS-1];
 reg [PW-1:0] slot_tag [0:RING_DWORDS-1];
 // Tags use the SOP's extended write pointer. Two ring spans prevent reuse
 // while an earlier packet's tail can remain after its SOP slot has retired.
 reg verdict [0:2*RING_DWORDS-1];
 reg output_valid;
 reg [127:0] output_data;
 reg [15:0] output_keep,output_sop,output_eop,output_dllp;
 reg [47:0] output_sequence;
 reg error_pulse,overflow_sticky;
 wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;
 wire [PW-1:0] occupied=write_ptr-read_ptr;
 wire [PW-1:0] committed=commit_ptr-read_ptr;
 reg [2:0] read_count;
 reg [127:0] read_data;
 reg [15:0] read_keep,read_sop,read_eop,read_dllp;
 reg [47:0] read_sequence;
 integer r,read_address;
 always @* begin
   read_count=(committed>=4)?3'd4:committed;
   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;
   for(r=0;r<4;r=r+1) begin
     read_address=(read_ptr+r)&(RING_DWORDS-1);
     if(r<read_count && slot_keep[read_address]!=0 && verdict[slot_tag[read_address]]) begin
       read_data[r*32+:32]=slot_data[read_address];
       read_keep[r*4+:4]=slot_keep[read_address];
       read_sop[r*4+:4]=slot_sop[read_address];
       read_eop[r*4+:4]=slot_eop[read_address];
       read_dllp[r*4+:4]=slot_dllp[read_address];
       read_sequence[r*12+:12]=slot_sequence[read_address];
     end
   end
 end
 wire retire=enabled && active_o && committed!=0 &&
             ((!output_valid || ready_i) || read_keep==0);
 wire [PW:0] space_after_retire=RING_DWORDS-{1'b0,occupied}+(retire?read_count:0);
 wire ring_overflow_now=enabled && active_o && !ending && current_valid && space_after_retire<4;
 wire step=enabled && active_o && !ending && current_valid && !ring_overflow_now;
 wire last_slice=step && slice==3;
 wire input_ready=enabled && active_o && !ending && !ring_overflow_now &&
                  (!next_valid || last_slice);
 wire bad_block_now=block_valid_i && input_ready && (headers_i!=8'haa || block_error_i);
 reg token_failure;
 wire fault_now=ring_overflow_now || bad_block_now || token_failure;
 assign block_ready_o=input_ready;
 // Transport flush must not feed back through the current block's validity.
 // Only registered epoch/end state controls this separate capture boundary.
 assign accepting_o=enabled && active_o && !ending;
 // Faults take effect at the sampling edge. Do not expose a prospective
 // full-ring fault one cycle before the same-edge ready/pop can resolve it.
 assign valid_o=enabled && active_o && output_valid;
 assign data_o=valid_o?output_data:128'b0;
 assign keep_o=valid_o?output_keep:16'b0;
 assign sop_o=valid_o?output_sop:16'b0;
 assign eop_o=valid_o?output_eop:16'b0;
 assign dllp_o=valid_o?output_dllp:16'b0;
 assign sequence_o=valid_o?output_sequence:48'b0;
 assign framing_error_o=error_pulse && rst_ni && !flush_i && !stream_start_i;
 assign overflow_o=overflow_sticky && rst_ni && !flush_i && !stream_start_i;
 reg [127:0] write_data;
 reg [15:0] write_keep,write_sop,write_eop,write_dllp;
 reg [47:0] write_sequence,event_sequence;
 reg [4*PW-1:0] write_tags,verdict_tags;
 reg [3:0] verdict_enable,verdict_value,event_good,event_nullified,event_crc_bad,event_dllp;
 reg [31:0] word;
 reg [10:0] length_dw;
 reg [12:0] encoded_bytes,tlp_payload;
 reg [3:0] crc;
 reg stp_ok,sdp_ok,idl_ok,eds_ok,edb_ok,handled;
 reg [PW-1:0] position;
 integer j;
 always @* begin
   lcrc_n=lcrc;dllp_crc_n=dllp_crc;
   state_n=state;commit_n=commit_ptr;tag_n=packet_tag;bytes_n=packet_bytes;
   expected_n=expected_bytes;remaining_n=remaining;sequence_n=packet_sequence;
   header_first_n=header_first;header_bad_n=header_bad;ending_n=ending;
   write_data=0;write_keep=0;write_sop=0;write_eop=0;write_dllp=0;
   write_sequence=0;write_tags=0;verdict_tags=0;verdict_enable=0;verdict_value=0;
   event_crc_bad=0;event_dllp=0;event_good=0;event_nullified=0;event_sequence=0;token_failure=0;
   word=0;length_dw=0;encoded_bytes=0;tlp_payload=0;crc=0;
   stp_ok=0;sdp_ok=0;idl_ok=0;eds_ok=0;edb_ok=0;handled=0;position=0;
   for(j=0;j<4;j=j+1) begin
     word={current_block[384+j*8+:8],current_block[256+j*8+:8],
           current_block[128+j*8+:8],current_block[j*8+:8]};
     position=write_ptr+j;
     length_dw={word[14:8],word[7:4]};encoded_bytes={length_dw,2'b00}-13'd2;
     crc[0]=length_dw[10]^length_dw[7]^length_dw[6]^length_dw[4]^length_dw[2]^length_dw[1]^length_dw[0];
     crc[1]=length_dw[10]^length_dw[9]^length_dw[7]^length_dw[5]^length_dw[4]^length_dw[3]^length_dw[2];
     crc[2]=length_dw[9]^length_dw[8]^length_dw[6]^length_dw[4]^length_dw[3]^length_dw[2]^length_dw[1];
     crc[3]=length_dw[8]^length_dw[7]^length_dw[5]^length_dw[3]^length_dw[2]^length_dw[1]^length_dw[0];
     stp_ok=word[3:0]==4'hf && length_dw>=5 && length_dw<1152 &&
       encoded_bytes<=MAX_ENCODED_BYTES && crc==word[23:20] &&
       (^{length_dw,word[23:20],word[15]})==1'b0;
     sdp_ok=word[15:0]==16'hacf0;idl_ok=word==0;
     eds_ok=word==32'h0090801f && slice==3 && j==3;
     edb_ok=word==32'hc0c0c0c0;handled=0;
     if(step && !token_failure && !ending_n) begin
       if(state_n==LOOK) begin
         verdict_enable[j]=1;verdict_tags[j*PW+:PW]=tag_n;
         event_sequence[j*12+:12]=sequence_n;
         if(edb_ok) begin
           verdict_value[j]=0;event_nullified[j]=(lcrc_n==32'b0);
           event_crc_bad[j]=(lcrc_n!=32'b0);commit_n=position+1'b1;
           state_n=TOKEN;handled=1;
         end else if(stp_ok || sdp_ok || idl_ok || eds_ok) begin
           verdict_value[j]=(lcrc_n==32'hdebb20e3);event_good[j]=(lcrc_n==32'hdebb20e3);
           event_crc_bad[j]=(lcrc_n!=32'hdebb20e3);commit_n=position;state_n=TOKEN;
         end else token_failure=1;
       end
       if(!handled && !token_failure) begin
         case(state_n)
           TOKEN:begin
             if(idl_ok) commit_n=position+1'b1;
             else if(eds_ok) begin commit_n=position+1'b1;ending_n=1;end
             else if(stp_ok) begin
               tag_n=position;sequence_n={word[19:16],word[31:24]};
               lcrc_n=crc32_16(32'hffffffff,{word[31:24],4'b0,word[19:16]});
               write_data[j*32+:32]={16'b0,word[31:24],4'b0,word[19:16]};
               write_keep[j*4+:4]=4'b0011;write_sop[j*4]=1;
               write_tags[j*PW+:PW]=tag_n;write_sequence[j*12+:12]=sequence_n;
               bytes_n=encoded_bytes;remaining_n=length_dw-1'b1;
               header_first_n=1;header_bad_n=0;expected_n=0;state_n=TLP;
             end else if(sdp_ok) begin
               tag_n=position;sequence_n=0;
               dllp_crc_n=crc16_16(16'hffff,word[31:16]);
               write_data[j*32+:32]={16'b0,word[31:16]};
               write_keep[j*4+:4]=4'b0011;write_sop[j*4]=1;write_dllp[j*4+:4]=4'b0011;
               write_tags[j*PW+:PW]=tag_n;state_n=DLLP;
             end else token_failure=1;
           end
           TLP:begin
             lcrc_n=crc32_32(lcrc_n,word);
             write_data[j*32+:32]=word;write_keep[j*4+:4]=4'b1111;
             write_tags[j*PW+:PW]=tag_n;write_sequence[j*12+:12]=sequence_n;
             if(header_first_n) begin
               tlp_payload=({word[17:16],word[31:24]}==0)?13'd4096:{1'b0,word[17:16],word[31:24],2'b00};
               expected_n=13'd18+(word[5]?13'd4:13'd0)+(word[6]?tlp_payload:13'd0)+(word[23]?13'd4:13'd0);
               header_bad_n=word[7];header_first_n=0;
             end
             remaining_n=remaining_n-1'b1;
             if(remaining_n==0) begin
               write_eop[j*4+3]=1;
               if(header_bad_n || bytes_n!=expected_n) token_failure=1;
               else state_n=LOOK;
             end
           end
           DLLP:begin
             dllp_crc_n=crc16_32(dllp_crc_n,word);
             write_data[j*32+:32]=word;write_keep[j*4+:4]=4'b1111;
             write_eop[j*4+3]=1;write_dllp[j*4+:4]=4'b1111;write_tags[j*PW+:PW]=tag_n;
             verdict_enable[j]=1;verdict_tags[j*PW+:PW]=tag_n;verdict_value[j]=(dllp_crc_n==16'h556f);
             event_good[j]=(dllp_crc_n==16'h556f);event_crc_bad[j]=(dllp_crc_n!=16'h556f);
             event_dllp[j]=1;event_sequence[j*12+:12]=0;
             commit_n=position+1'b1;state_n=TOKEN;
           end
           default:token_failure=1;
         endcase
       end
     end
   end
 end
 integer w;
 initial begin
   if(MAX_ENCODED_BYTES<18 || MAX_ENCODED_BYTES>4118)
     $error("MAX_ENCODED_BYTES must be18..4118");
   if(RING_DWORDS<((MAX_ENCODED_BYTES+2)/4+8) || (RING_DWORDS&(RING_DWORDS-1))!=0)
     $error("Power-of-two ring must exceed one maximum packet plus8slots");
 end
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     lcrc<=32'hffffffff;dllp_crc<=16'hffff;
     state<=TOKEN;current_block<=0;next_block<=0;current_valid<=0;next_valid<=0;slice<=0;
     write_ptr<=0;read_ptr<=0;commit_ptr<=0;packet_tag<=0;packet_bytes<=0;expected_bytes<=0;
     remaining<=0;packet_sequence<=0;header_first<=0;header_bad<=0;ending<=0;
     output_valid<=0;output_data<=0;output_keep<=0;output_sop<=0;output_eop<=0;output_dllp<=0;output_sequence<=0;
     error_pulse<=0;overflow_sticky<=0;stream_end_o<=0;active_o<=0;halted_o<=0;
     packet_good_o<=0;packet_nullified_o<=0;packet_crc_bad_o<=0;packet_dllp_o<=0;packet_sequence_o<=0;
   end else begin
     error_pulse<=0;stream_end_o<=0;packet_good_o<=0;packet_nullified_o<=0;packet_crc_bad_o<=0;packet_dllp_o<=0;packet_sequence_o<=0;
     if(flush_i || stream_start_i) begin
       state<=TOKEN;current_valid<=0;next_valid<=0;slice<=0;write_ptr<=0;read_ptr<=0;commit_ptr<=0;
       output_valid<=0;ending<=0;overflow_sticky<=0;active_o<=stream_start_i && !flush_i;halted_o<=0;
     end else if((stream_abort_i && active_o) || fault_now) begin
       state<=TOKEN;current_valid<=0;next_valid<=0;output_valid<=0;ending<=0;
       write_ptr<=0;read_ptr<=0;commit_ptr<=0;error_pulse<=1;active_o<=0;halted_o<=1;
       if(ring_overflow_now) overflow_sticky<=1;
     end else if(active_o) begin
       if(!output_valid || ready_i) output_valid<=0;
       if(retire) begin
         read_ptr<=read_ptr+read_count;
         if(read_keep!=0) begin
           output_valid<=1;output_data<=read_data;output_keep<=read_keep;
           output_sop<=read_sop;output_eop<=read_eop;output_dllp<=read_dllp;output_sequence<=read_sequence;
         end
       end
       if(step) begin
         lcrc<=lcrc_n;dllp_crc<=dllp_crc_n;
         state<=state_n;commit_ptr<=commit_n;packet_tag<=tag_n;packet_bytes<=bytes_n;
         expected_bytes<=expected_n;remaining<=remaining_n;packet_sequence<=sequence_n;
         header_first<=header_first_n;header_bad<=header_bad_n;ending<=ending_n;
         write_ptr<=write_ptr+4;packet_good_o<=event_good;packet_nullified_o<=event_nullified;packet_crc_bad_o<=event_crc_bad;packet_dllp_o<=event_dllp;packet_sequence_o<=event_sequence;
         for(w=0;w<4;w=w+1) begin
           slot_data[(write_ptr+w)&(RING_DWORDS-1)]<=write_data[w*32+:32];
           slot_keep[(write_ptr+w)&(RING_DWORDS-1)]<=write_keep[w*4+:4];
           slot_sop[(write_ptr+w)&(RING_DWORDS-1)]<=write_sop[w*4+:4];
           slot_eop[(write_ptr+w)&(RING_DWORDS-1)]<=write_eop[w*4+:4];
           slot_dllp[(write_ptr+w)&(RING_DWORDS-1)]<=write_dllp[w*4+:4];
           slot_sequence[(write_ptr+w)&(RING_DWORDS-1)]<=write_sequence[w*12+:12];
           slot_tag[(write_ptr+w)&(RING_DWORDS-1)]<=write_tags[w*PW+:PW];
           if(verdict_enable[w]) verdict[verdict_tags[w*PW+:PW]]<=verdict_value[w];
         end
         if(slice==3) begin
           slice<=0;current_valid<=next_valid;
           if(next_valid) current_block<=next_block;
           next_valid<=0;
         end else begin
           slice<=slice+1'b1;
           current_block<={32'b0,current_block[511:416],32'b0,current_block[383:288],
                           32'b0,current_block[255:160],32'b0,current_block[127:32]};
         end
       end
       if(block_valid_i && block_ready_o) begin
         if(!current_valid || (last_slice && !next_valid)) begin current_block<=payload_i;current_valid<=1;slice<=0;end
         else begin next_block<=payload_i;next_valid<=1;end
       end
       if(ending_n) begin current_valid<=0;next_valid<=0;end
       if(ending && read_ptr==write_ptr && (!output_valid || ready_i)) begin
         stream_end_o<=1;active_o<=0;ending<=0;output_valid<=0;
       end
     end
   end
 end
endmodule
