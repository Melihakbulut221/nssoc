// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Exhaustive combinational relation over all 32 state bits and all 8 data
// bits. Independent normal-polynomial representation; no assumptions/cuts.
// This proves the CRC recurrence, not a complete DLL or receive controller.
module pcie_crc32_byte_formal(input wire [31:0] state_i,input wire [7:0] data_i);
    wire [31:0] actual;
    reg [31:0] normal,expected;
    integer i;
    soc_pcie_crc32_byte dut(.state_i(state_i),.data_i(data_i),.state_o(actual));
    always @* begin
        for(i=0;i<32;i=i+1)normal[31-i]=state_i[i];
        for(i=0;i<8;i=i+1)begin
            if(normal[31]^data_i[i])normal={normal[30:0],1'b0}^32'h04c11db7;
            else normal={normal[30:0],1'b0};
        end
        for(i=0;i<32;i=i+1)expected[i]=normal[31-i];
        assert(actual==expected);
    end
endmodule
`default_nettype wire
