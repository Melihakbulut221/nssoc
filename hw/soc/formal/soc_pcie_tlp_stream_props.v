// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Port-only packet-output and APB safety; inputs are unconstrained.
module soc_pcie_tlp_stream_props (
    input wire clk_i, rst_ni, rx_valid_i, rx_sop_i, rx_eop_i, rx_error_i,
    input wire tx_ready_i, pready_i, pslverr_i,
    input wire [15:0] function_id_i,
    input wire [31:0] rx_data_i, prdata_i
);
    wire rx_ready, tx_valid, tx_sop, tx_eop, psel, penable, pwrite, error, enabled;
    wire [31:0] tx_data, pwdata, bar;
    wire [11:0] paddr;
    wire [3:0] pstrb;
    soc_pcie_tlp_stream #(.APB_TIMEOUT(8)) dut (
        .clk_i(clk_i), .rst_ni(rst_ni), .function_id_i(function_id_i),
        .rx_data_i(rx_data_i), .rx_valid_i(rx_valid_i), .rx_ready_o(rx_ready),
        .rx_sop_i(rx_sop_i), .rx_eop_i(rx_eop_i), .rx_error_i(rx_error_i),
        .tx_data_o(tx_data), .tx_valid_o(tx_valid), .tx_ready_i(tx_ready_i),
        .tx_sop_o(tx_sop), .tx_eop_o(tx_eop),
        .psel_o(psel), .penable_o(penable), .paddr_o(paddr),
        .pwrite_o(pwrite), .pstrb_o(pstrb), .pwdata_o(pwdata),
        .pready_i(pready_i), .pslverr_i(pslverr_i), .prdata_i(prdata_i),
        .error_o(error), .memory_enable_o(enabled), .bar0_o(bar)
    );
    reg valid=0;
    reg [2:0] remaining;
    reg [3:0] waits;
    reg saw_bad, recovered;
    initial assume (!rst_ni);
    always @(posedge clk_i) begin
        valid<=1;
        if (!rst_ni) begin
            remaining<=0; waits<=0; saw_bad<=0; recovered<=0;
        end else begin
            if (tx_valid && tx_ready_i) begin
                if (remaining==0) remaining<=tx_data[30] ? 3 : 2;
                else remaining<=remaining-1'b1;
            end
            if (psel && penable && !pready_i) waits<=waits+1'b1;
            else waits<=0;
            if (rx_valid_i && rx_ready && rx_error_i) saw_bad<=1;
            if (saw_bad && tx_valid && tx_ready_i && tx_eop) recovered<=1;
        end
        if (valid && rst_ni && $past(rst_ni)) begin
            assert (!penable || psel);
            assert (!psel || (enabled && paddr[1:0]==0));
            assert (!psel || pwrite || pstrb==0);
            assert (waits<=8);
            if (tx_valid) begin
                assert (tx_sop==(remaining==0));
                assert (tx_eop==(remaining==1));
                if (tx_sop) assert (tx_data==32'h4a000001 || tx_data==32'h0a000000);
            end
            if ($past(tx_valid && !tx_ready_i)) begin
                assert (tx_valid);
                assert ($stable({tx_data,tx_sop,tx_eop}));
            end
            if ($past(psel && !penable)) begin
                assert (psel && penable);
                assert ($stable({paddr,pwrite,pstrb,pwdata}));
            end
            if ($past(psel && penable && !pready_i) && psel)
                assert ($stable({paddr,pwrite,pstrb,pwdata}));
            cover (tx_valid && tx_ready_i && tx_eop);
            cover (psel && penable && pready_i && !pwrite);
            cover (psel && penable && pready_i && pwrite);
            cover (recovered);
        end
    end
endmodule
