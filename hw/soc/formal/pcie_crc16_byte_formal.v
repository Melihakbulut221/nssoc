// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Exhaustive combinational relation only, not a packet/protocol proof.
module pcie_crc16_byte_formal (
    input wire [15:0] state_i,
    input wire [7:0] data_i
);
    wire [15:0] observed;
    reg [15:0] normal,expected;
    integer i;
    soc_pcie_crc16_byte dut(.state_i(state_i),.data_i(data_i),.state_o(observed));
    always @* begin
        for(i=0;i<16;i=i+1) normal[i]=state_i[15-i];
        for(i=0;i<8;i=i+1) begin
            if(normal[15]^data_i[i]) normal=(normal<<1)^16'h100b;
            else normal=normal<<1;
        end
        for(i=0;i<16;i=i+1) expected[i]=normal[15-i];
        assert(observed==expected);
    end
endmodule
`default_nettype wire
