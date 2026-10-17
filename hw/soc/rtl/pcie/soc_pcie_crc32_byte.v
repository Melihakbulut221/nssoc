// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// One octet of the classic PCIe LCRC, in transmission order, bit 0 first.
// Reflected representation of polynomial 04C11DB7; initialize to FFFFFFFF.
// Complement the final state and transmit its least-significant octet first.
// Including those four LCRC octets produces raw residue DEBB20E3.
// Historical PCI-SIG Base 2.1 section 3.5.2 / Table 3-3, Intel-hosted copy:
// https://www.intel.com/content/dam/support/us/en/programmable/support-resources/fpga-wiki/asset03/pci-express-base-r2.1.pdf
// This combinational primitive has no packet, sequence, retry or link state.
module soc_pcie_crc32_byte (
    input wire [31:0] state_i,
    input wire [7:0] data_i,
    output reg [31:0] state_o
);
    integer bit_index;
    always @* begin
        state_o=state_i;
        for (bit_index=0;bit_index<8;bit_index=bit_index+1)
            state_o=(state_o>>1)^({32{state_o[0]^data_i[bit_index]}} & 32'hedb88320);
    end
endmodule
`default_nettype wire
