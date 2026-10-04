// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Classic DLLP CRC: normal polynomial 0x100b, reflected 0xd008, bit 0 first.
// This recurrence has no framing, initialization or final-complement policy.
module soc_pcie_crc16_byte (
    input wire [15:0] state_i,
    input wire [7:0] data_i,
    output reg [15:0] state_o
);
    integer bit_index;
    always @* begin
        state_o=state_i;
        for (bit_index=0;bit_index<8;bit_index=bit_index+1)
            state_o=(state_o>>1) ^
                ({16{state_o[0]^data_i[bit_index]}} & 16'hd008);
    end
endmodule
`default_nettype wire
