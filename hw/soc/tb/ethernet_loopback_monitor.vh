// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Included inside the generated CPU Ethernet probe module.
  reg eth_clk=0;
  always #4 eth_clk=~eth_clk;
  wire [7:0] eth_txd;
  wire eth_en,eth_er;
  integer eth_frames=0,eth_bytes=0,eth_total=0;
  reg [31:0] eth_crc=32'hffffffff;
  function integer frame_length;
    input integer f;
    begin case(f)
      0:frame_length=60;1:frame_length=61;2:frame_length=300;
      3:frame_length=511;4:frame_length=127;5:frame_length=512;
      6:frame_length=300;7:frame_length=300;
      default:frame_length=-1;
    endcase end
  endfunction
  function [31:0] crc_byte;
    input [31:0] state;
    input [7:0] data;
    integer k;reg[31:0] x;
    begin
      x=state^data;
      for(k=0;k<8;k=k+1)x=(x>>1)^((x&1)?32'hedb88320:0);
      crc_byte=x;
    end
  endfunction
  always @(negedge eth_clk) begin
    if(!rst_n)begin eth_frames=0;eth_bytes=0;eth_total=0;eth_crc=32'hffffffff;end
    else if(eth_en===1'b1)begin
      if(eth_frames>=8 || eth_er!==1'b0)$fatal(1,"GMII extra frame/error");
      if(eth_bytes<7 && eth_txd!==8'h55)$fatal(1,"GMII preamble mismatch");
      if(eth_bytes==7 && eth_txd!==8'hd5)$fatal(1,"GMII SFD mismatch");
      if(eth_bytes>=8)begin
        if(eth_bytes<8+frame_length(eth_frames))begin
          if(eth_txd!==((eth_frames*29+(eth_bytes-8)*13+7)&255))$fatal(1,"GMII payload mismatch frame=%0d byte=%0d",eth_frames,eth_bytes-8);
          eth_total=eth_total+1;
        end
        eth_crc=crc_byte(eth_crc,eth_txd);
      end
      eth_bytes=eth_bytes+1;
    end else if(eth_bytes!=0)begin
      if(eth_en!==1'b0 || eth_bytes!=frame_length(eth_frames)+12 || eth_crc!==32'hdebb20e3)$fatal(1,"GMII length/CRC mismatch frame=%0d bytes=%0d crc=%x",eth_frames,eth_bytes,eth_crc);
      eth_frames=eth_frames+1;eth_bytes=0;eth_crc=32'hffffffff;
    end
  end
