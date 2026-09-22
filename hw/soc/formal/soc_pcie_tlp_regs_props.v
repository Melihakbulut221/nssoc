// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Port-only safety assertions; packet and bus inputs remain unconstrained.
module soc_pcie_tlp_regs_props (
    input wire clk_i, rst_ni, rx_valid_i, tx_ready_i, pready_i, pslverr_i,
    input wire [15:0] function_id_i,
    input wire [127:0] rx_hdr_i,
    input wire [31:0] rx_data_i, prdata_i,
    input wire [10:0] rx_payload_dw_i
);
    wire rx_ready, tx_valid, tx_has_data, psel, penable, pwrite, error, enabled;
    wire [127:0] tx_hdr;
    wire [31:0] tx_data, pwdata, bar;
    wire [11:0] paddr;
    wire [3:0] pstrb;
    soc_pcie_tlp_regs #(.APB_TIMEOUT(8)) dut (
        .clk_i(clk_i), .rst_ni(rst_ni), .function_id_i(function_id_i),
        .rx_hdr_i(rx_hdr_i), .rx_data_i(rx_data_i), .rx_payload_dw_i(rx_payload_dw_i),
        .rx_valid_i(rx_valid_i), .rx_ready_o(rx_ready),
        .tx_hdr_o(tx_hdr), .tx_data_o(tx_data), .tx_has_data_o(tx_has_data),
        .tx_valid_o(tx_valid), .tx_ready_i(tx_ready_i),
        .psel_o(psel), .penable_o(penable), .paddr_o(paddr),
        .pwrite_o(pwrite), .pstrb_o(pstrb), .pwdata_o(pwdata),
        .pready_i(pready_i), .pslverr_i(pslverr_i), .prdata_i(prdata_i),
        .error_o(error), .memory_enable_o(enabled), .bar0_o(bar)
    );
    reg valid=0;
    reg [15:0] captured_cid, captured_rid;
    reg [7:0] captured_tag;
    reg [3:0] waits;
    initial assume (!rst_ni);
    always @(posedge clk_i) begin
        valid <= 1;
        if (!rst_ni) begin
            captured_cid<=0; captured_rid<=0; captured_tag<=0; waits<=0;
        end else begin
            if (rx_valid_i && rx_ready) begin
                captured_cid<=function_id_i;
                captured_rid<=rx_hdr_i[95:80]; captured_tag<=rx_hdr_i[79:72];
            end
            if (psel && penable && !pready_i) waits<=waits+1'b1;
            else waits<=0;
        end
        if (valid && rst_ni && $past(rst_ni)) begin
            assert (!penable || psel);
            assert (!rx_ready || (!tx_valid && !psel));
            assert (!tx_valid || (!psel && !rx_ready));
            assert (!psel || (enabled && paddr[1:0]==0));
            assert (!psel || pwrite || pstrb==0);
            assert (waits<=8);
            if (tx_valid) begin
                assert (tx_hdr[31:0]==0);
                assert (tx_hdr[95:80]==captured_cid);
                assert (tx_hdr[63:48]==captured_rid);
                assert (tx_hdr[47:40]==captured_tag);
                assert (tx_hdr[127:96]==(tx_has_data ? 32'h4a000001 : 32'h0a000000));
            end
            if ($past(tx_valid && !tx_ready_i)) begin
                assert (tx_valid);
                assert ($stable({tx_hdr,tx_data,tx_has_data}));
            end
            if ($past(psel && !penable)) begin
                assert (psel && penable);
                assert ($stable({paddr,pwrite,pstrb,pwdata}));
            end
            if ($past(psel && penable && !pready_i) && psel)
                assert ($stable({paddr,pwrite,pstrb,pwdata}));
            if (psel && !penable) begin
                assert ($past(rx_valid_i && rx_ready && enabled));
                assert ($past(rx_hdr_i[124:120])==0); // Memory type.
                assert ($past(rx_hdr_i[119:106])==0); // Supported fields only.
                assert ($past(rx_hdr_i[105:96])==1);
                assert ($past(rx_hdr_i[71:68])==0);
                assert ($past(rx_hdr_i[67:64])!=0);
                assert ($past(rx_payload_dw_i)==(pwrite ? 1 : 0));
                assert (pwrite==$past(rx_hdr_i[126]));
                assert (pwdata==$past(rx_data_i));
                assert (pstrb==(pwrite ? $past(rx_hdr_i[67:64]) : 4'b0));
                if ($past(rx_hdr_i[125])) begin
                    assert ($past(rx_hdr_i[63:32])==0);
                    assert ($past(rx_hdr_i[31:12])==$past(bar[31:12]));
                    assert (paddr==$past(rx_hdr_i[11:0]));
                end else begin
                    assert ($past(rx_hdr_i[63:44])==$past(bar[31:12]));
                    assert (paddr==$past(rx_hdr_i[43:32]));
                end
            end
            cover (psel && penable && pwrite && pready_i && !pslverr_i);
            cover (tx_valid && tx_has_data && tx_hdr[79:77]==0);
            cover (tx_valid && tx_hdr[79:77]==4);
            cover (tx_valid && tx_hdr[79:77]==1);
            cover (error && waits==8);
        end
    end
endmodule
