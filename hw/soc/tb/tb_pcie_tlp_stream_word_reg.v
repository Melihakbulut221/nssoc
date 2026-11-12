// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
`default_nettype none
// Random co-simulation of soc_pcie_tlp_stream with SOC_PCIE_TX_WORD_REG
// (candidate) against the default build (reference, renamed
// soc_pcie_tlp_stream_ref), docs/combined-timing.md section 17. Both get
// the same receive words, transmit back-pressure, APB responses and
// resets; every output of both is compared in every cycle, whether or not
// it is valid. scripts/check_pcie_tlp_stream_word_reg.sh builds and runs it.
//   +seed=N +cycles=N
module tb_pcie_tlp_stream_word_reg;
    localparam [15:0] VENDOR_ID=16'h1234, DEVICE_ID=16'h5678;
    localparam integer APB_TIMEOUT=8;
    localparam [15:0] CID=16'h0200;
    localparam [31:0] BAR=32'h82345000;
    localparam integer MAXW=1100;

    reg clk=0;
    always #5 clk=~clk;
    reg rst_ni=0;
    reg [31:0] rx_data=0;
    reg rx_sop=0, rx_eop=0, rx_error=0, rx_valid=0;
    reg tx_ready=0, pready=0, pslverr=0;
    reg [31:0] prdata=0;

    wire r_rx_ready, r_tx_sop, r_tx_eop, r_tx_valid, r_psel, r_penable, r_pwrite, r_error, r_men;
    wire [31:0] r_tx_data, r_pwdata, r_bar0;
    wire [11:0] r_paddr;
    wire [3:0] r_pstrb;
    wire c_rx_ready, c_tx_sop, c_tx_eop, c_tx_valid, c_psel, c_penable, c_pwrite, c_error, c_men;
    wire [31:0] c_tx_data, c_pwdata, c_bar0;
    wire [11:0] c_paddr;
    wire [3:0] c_pstrb;

    soc_pcie_tlp_stream_ref #(.VENDOR_ID(VENDOR_ID), .DEVICE_ID(DEVICE_ID), .APB_TIMEOUT(APB_TIMEOUT)) reference (
        .clk_i(clk), .rst_ni(rst_ni), .function_id_i(CID),
        .rx_data_i(rx_data), .rx_sop_i(rx_sop), .rx_eop_i(rx_eop), .rx_error_i(rx_error), .rx_valid_i(rx_valid),
        .rx_ready_o(r_rx_ready), .tx_data_o(r_tx_data), .tx_sop_o(r_tx_sop), .tx_eop_o(r_tx_eop),
        .tx_valid_o(r_tx_valid), .tx_ready_i(tx_ready), .psel_o(r_psel), .penable_o(r_penable),
        .paddr_o(r_paddr), .pwrite_o(r_pwrite), .pstrb_o(r_pstrb), .pwdata_o(r_pwdata),
        .pready_i(pready), .pslverr_i(pslverr), .prdata_i(prdata), .error_o(r_error),
        .memory_enable_o(r_men), .bar0_o(r_bar0));
    soc_pcie_tlp_stream #(.VENDOR_ID(VENDOR_ID), .DEVICE_ID(DEVICE_ID), .APB_TIMEOUT(APB_TIMEOUT)) candidate (
        .clk_i(clk), .rst_ni(rst_ni), .function_id_i(CID),
        .rx_data_i(rx_data), .rx_sop_i(rx_sop), .rx_eop_i(rx_eop), .rx_error_i(rx_error), .rx_valid_i(rx_valid),
        .rx_ready_o(c_rx_ready), .tx_data_o(c_tx_data), .tx_sop_o(c_tx_sop), .tx_eop_o(c_tx_eop),
        .tx_valid_o(c_tx_valid), .tx_ready_i(tx_ready), .psel_o(c_psel), .penable_o(c_penable),
        .paddr_o(c_paddr), .pwrite_o(c_pwrite), .pstrb_o(c_pstrb), .pwdata_o(c_pwdata),
        .pready_i(pready), .pslverr_i(pslverr), .prdata_i(prdata), .error_o(c_error),
        .memory_enable_o(c_men), .bar0_o(c_bar0));

    wire [127:0] r_out={r_rx_ready, r_tx_data, r_tx_sop, r_tx_eop, r_tx_valid, r_psel, r_penable, r_paddr,
                        r_pwrite, r_pstrb, r_pwdata, r_error, r_men, r_bar0};
    wire [127:0] c_out={c_rx_ready, c_tx_data, c_tx_sop, c_tx_eop, c_tx_valid, c_psel, c_penable, c_paddr,
                        c_pwrite, c_pstrb, c_pwdata, c_error, c_men, c_bar0};

    integer seed, cycles, cycle=0;
    integer mismatches=0, completions=0, data_completions=0, stalls=0, resets=0, packets=0, apb=0, enables=0;
    reg [31:0] pkt [0:MAXW-1];
    reg pkt_sop [0:MAXW-1];
    reg pkt_eop [0:MAXW-1];
    reg pkt_err [0:MAXW-1];
    integer plen=0, ppos=0, gap=0, rst_hold=0, k;

    function integer rnd(input integer n);
        begin rnd=$unsigned($random(seed))%n; end
    endfunction

    // One request (or malformed beat sequence) into pkt[0..plen-1].
    task build;
        integer r, words, n, payload, be, i, cut;
        reg [7:0] kind;
        reg [31:0] address;
        reg [15:0] requester;
        reg [7:0] tag;
        begin
            r=rnd(100); requester=$random(seed); tag=$random(seed);
            be=rnd(8)==0 ? 0 : (rnd(4)==0 ? rnd(16) : 15);
            address=rnd(4)==0 ? $random(seed) : BAR+4*rnd(64);
            payload=0;
            if (r<14) begin kind=8'h04; address={CID,4'h0,rnd(4)==0 ? 12'($random(seed)) & 12'hffc : 12'(4*rnd(16))}; end
            else if (r<24) begin
                kind=8'h44; payload=1;
                address={CID,16'(rnd(2)==0 ? 16'h0010 : (rnd(2)==0 ? 16'h0004 : 16'(4*rnd(16))))};
            end else if (r<46) kind=8'h00;
            else if (r<62) begin kind=8'h40; payload=1; end
            else if (r<69) kind=8'h20;
            else if (r<75) begin kind=8'h60; payload=1; end
            else kind=$random(seed);
            words=(kind & 8'h20) ? 4 : 3;
            pkt[0]={kind,14'd0,10'd1}; pkt[1]={requester,tag,4'd0,4'(be)};
            if (kind & 8'h20) begin pkt[2]=rnd(8)==0 ? $random(seed) : 0; pkt[3]=address; end
            else pkt[2]=address;
            if (r>=75 && r<85) payload=rnd(4);
            else if (r>=85 && r<89) payload=rnd(2)==0 ? 0 : 2;
            else if (r>=89 && r<90) payload=1030;
            n=words+payload;
            if (n>MAXW) n=MAXW;
            for (i=words; i<n; i=i+1) pkt[i]=(kind==8'h44 && address[15:0]==16'h0010) ? BAR : $random(seed);
            if (kind==8'h44 && address[15:0]==16'h0004) pkt[words]={30'd0,rnd(8)!=0,1'b0};
            for (i=0; i<n; i=i+1) begin pkt_sop[i]=i==0; pkt_eop[i]=i==n-1; pkt_err[i]=0; end
            if (r>=90 && r<93) pkt_err[rnd(n)]=1;                  // integrity failure at a beat
            else if (r>=93 && r<95) pkt_sop[0]=0;                  // missing start
            else if (r>=95 && r<97) begin cut=1+rnd(n); n=cut; pkt_eop[n-1]=0; end // abandoned by the next SOP
            else if (r>=97) begin                                  // orphan or random framing
                for (i=0; i<n; i=i+1) begin pkt_sop[i]=rnd(6)==0; pkt_eop[i]=rnd(5)==0; end
                pkt_eop[n-1]=1;
            end
            plen=n; ppos=0; packets=packets+1;
        end
    endtask

    // The register backend is enabled early (BAR0, memory enable), so most
    // memory requests reach the APB side; later configuration writes may
    // disable and re-enable it.
    task build_enable(input integer step);
        begin
            pkt[0]={8'h44,14'd0,10'd1}; pkt[1]={16'h0138,8'h11,8'h0f};
            pkt[2]={CID,16'(step==0 ? 16'h0010 : 16'h0004)}; pkt[3]=step==0 ? BAR : 32'd2;
            for (k=0; k<4; k=k+1) begin pkt_sop[k]=k==0; pkt_eop[k]=k==3; pkt_err[k]=0; end
            plen=4; ppos=0; packets=packets+1;
        end
    endtask

    always @(posedge clk) begin
        cycle=cycle+1;
        // Back-pressure and APB responses: random, with long stalls.
        tx_ready<=rnd(16)<(cycle%4096<1024 ? 4 : 12);
        pready<=rnd(16)<(cycle%2048<256 ? 1 : 10);
        pslverr<=rnd(20)==0;
        prdata<=$random(seed);
        if (rst_hold>0) begin
            rst_hold=rst_hold-1;
            if (rst_hold==0) begin rst_ni<=1; enables=0; end
        end else if (cycle>20 && rnd(20000)==0) begin
            rst_ni<=0; rst_hold=1+rnd(5); resets=resets+1;
            plen=0; ppos=0; rx_valid<=0; gap=0;
        end else begin
            if (rx_valid && r_rx_ready) begin
                ppos=ppos+1;
                rx_valid<=0;
                if (ppos>=plen) begin plen=0; gap=rnd(4)==0 ? rnd(12) : 0; end
            end
            if (plen==0 && gap>0) gap=gap-1;
            else begin
                if (plen==0) begin
                    if (enables<2) begin build_enable(enables); enables=enables+1; end
                    else build;
                end
                if (rnd(8)==0) rx_valid<=0;
                else begin
                    rx_valid<=1; rx_data<=pkt[ppos]; rx_sop<=pkt_sop[ppos];
                    rx_eop<=pkt_eop[ppos]; rx_error<=pkt_err[ppos];
                end
            end
        end
    end
    // While rx_valid is high and not accepted the word must not change.
    // The block above only presents pkt[ppos], and ppos moves only on an
    // accepted word, so a word dropped by the random gap is presented again.

    always @(negedge clk) if (cycle>2) begin
        if (r_out!==c_out) begin
            mismatches=mismatches+1;
            if (mismatches<=10)
                $display("MISMATCH t=%0t cycle=%0d reference=%h candidate=%h", $time, cycle, r_out, c_out);
        end
        if (rst_ni && r_tx_valid && tx_ready && r_tx_eop) begin
            completions=completions+1;
            if (reference.tx_payload) data_completions=data_completions+1;
        end
        if (rst_ni && r_tx_valid && !tx_ready) stalls=stalls+1;
        if (r_psel && r_penable && pready) apb=apb+1;
    end

    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed=1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles=300000;
        repeat (4) @(posedge clk);
        rst_ni<=1;
        wait (cycle>=cycles);
        @(negedge clk);
        $display("SUMMARY seed=%0d cycles=%0d packets=%0d completions=%0d with_data=%0d stalls=%0d apb=%0d resets=%0d mismatches=%0d",
                 seed, cycle, packets, completions, data_completions, stalls, apb, resets, mismatches);
        if (mismatches==0 && completions>1000 && data_completions>300 && completions-data_completions>300 &&
            stalls>1000 && apb>300 && (cycles<100000 || resets>=2))
            $display("RESULT PASS");
        else
            $display("RESULT FAIL");
        $finish;
    end
endmodule
`default_nettype wire
