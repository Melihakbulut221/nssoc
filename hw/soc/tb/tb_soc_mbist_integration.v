// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
module tb_soc_mbist_integration;
    reg clk=0, por=0;
    always #10 clk=~clk;
    reg eth_clk=0;
    reg eth_run=1;
    always #4 if(eth_run) eth_clk=~eth_clk;
    wire busy, done, failed;
    wire [12:0] fail_addr;
    wire [63:0] expected, actual;
    wire [2:0] phase;
    wire [7:0] background;
    soc_top #(.MEM_RDREG(1), .REQ_REG(1), .WAKE_GNT(1)) dut (
        .clk_i(clk), .rst_ni(por), .irq_external_i(1'b0), .wdog_dis_i(1'b0),
        .strap_i(4'b0), .uart_rx_i(1'b1), .gpio_i(16'b0), .qspi_io_i(4'hf),
        .eth_rx_clk_i(eth_clk), .eth_tx_clk_i(eth_clk), .eth_rxd_i(8'b0),
        .eth_rx_dv_i(1'b0), .eth_rx_er_i(1'b0), .eth_mdio_i(1'b1),
        .spw_di_i(1'b0), .spw_si_i(1'b0), .i2c_scl_i(1'b1), .i2c_sda_i(1'b1),
        .can_rx_i(1'b1), .spi_miso_i(1'b0),
        .mbist_busy_o(busy), .mbist_done_o(done), .mbist_failed_o(failed),
        .mbist_fail_addr_o(fail_addr), .mbist_fail_expected_o(expected),
        .mbist_fail_actual_o(actual), .mbist_fail_phase_o(phase),
        .mbist_fail_background_o(background));
    integer ethfault=-1, ethstall=0;
    integer fault_bank=-1, restart=0, illegal=0, count=0, cycles=0;
    integer bank_count[0:3];
    integer k;
    reg boot_pass=0;
    wire [63:0] faulty_read = dut.u_ram.g_ram_2048x64_ecc.dsel ^
        ((dut.u_ram.g_ram_2048x64_ecc.row_addr == (fault_bank*2048+17)) ?
         64'h8000000000000000 : 64'b0);
    // The fault is BELOW ECC and in a check bit. A codec-level test could
    // accidentally correct/hide it. Here the raw MBIST comparison must stop.
    initial begin
`ifdef SOC_ETH_MBIST
        if ($value$plusargs("ethfault=%d", ethfault)) begin end
        if ($value$plusargs("ethstall=%d", ethstall)) begin end
        if (ethfault==0) force dut.u_eth.u_mac.tx_fifo.fifo_inst.u_sram.bq=16'h8000;
        if (ethfault==1) force dut.u_eth.u_mac.rx_fifo.fifo_inst.u_sram.bq=16'h8000;
        if (ethstall!=0) eth_run=0;
`endif
        if ($value$plusargs("fault_bank=%d", fault_bank)) begin end
        if ($value$plusargs("restart=%d", restart)) begin end
        if ($value$plusargs("illegal=%d", illegal)) begin end
        for (k=0;k<4;k=k+1) bank_count[k]=0;
        if (fault_bank >= 0) force dut.u_ram.g_ram_2048x64_ecc.row_dout = faulty_read;
        repeat(5) @(negedge clk);
        por=1;
        if (restart != 0) begin
            wait(count==101);
            @(negedge clk); por=0;
            #1;
            if (dut.u_ram.g_ram_2048x64_ecc.row_en !== 0 || done !== 0)
                $fatal(1,"POR did not cancel memory test immediately");
            repeat(5) @(negedge clk);
            count=0;
            for (k=0;k<4;k=k+1) bank_count[k]=0;
            por=1;
        end
        if (illegal != 0) begin
            wait(count==100);
            @(negedge clk); force dut.u_ram.g_ram_2048x64_ecc.u_test_port.u_mbist.state_q=2'b11;
            @(negedge clk); release dut.u_ram.g_ram_2048x64_ecc.u_test_port.u_mbist.state_q;
        end
`ifdef SOC_ETH_MBIST
        if (ethstall!=0) begin
            wait(dut.ram_mbist_done);
            repeat(20) @(negedge clk);
            if(done || dut.rst_sys_n) $fatal(1,"CPU released before Ethernet clocks/test");
            eth_run=1;
        end
`endif
        wait(done===1);
        $display("MBIST completed cycles=%0d accesses=%0d failed=%0d",cycles,count,failed);
        @(negedge clk);
        if (ethfault>=0) begin
`ifdef SOC_ETH_MBIST
            repeat(20) @(negedge clk);
            if (!failed || dut.rst_sys_n || dut.eth_mbist_failed_o != (2'b01 << ethfault))
                $fatal(1,"Ethernet MBIST did not hold chip reset or wrong FIFO diagnosis");
            $display("PASS Ethernet MBIST failure holds CPU reset fifo=%0d",ethfault);
            $finish;
`endif
        end else if (illegal != 0) begin
            repeat(20) @(negedge clk);
            if (!failed || dut.rst_sys_n !== 0 || dut.u_ram.g_ram_2048x64_ecc.row_en !== 0)
                $fatal(1,"abnormal MBIST termination released CPU");
            $display("PASS illegal-state fails closed");
            $finish;
        end else if (fault_bank >= 0) begin
            if (!failed || fail_addr != fault_bank*2048+17 || expected != 0 ||
                actual != 64'h8000000000000000 || phase != 1 || background != 0)
                $fatal(1,"wrong first-failure diagnosis %d %h %h %d %d",fail_addr,expected,actual,phase,background);
            repeat(50) begin
                @(negedge clk);
                if (dut.rst_sys_n !== 0 || dut.u_ram.g_ram_2048x64_ecc.row_en !== 0 || !failed)
                    $fatal(1,"failure did not hold CPU/memory stopped");
            end
            $display("PASS fault bank=%0d address=%0d ECC-check-bit=63",fault_bank,fail_addr);
            $finish;
        end else begin
        if (failed || count != 655360) $fatal(1,"incomplete raw test: %d",count);
        for (k=0;k<4;k=k+1)
            if(bank_count[k] != 163840) $fatal(1,"missing bank %d: %d",k,bank_count[k]);
        wait(boot_pass);
        // A watchdog reset must not trigger a second destructive test or
        // clear the sticky POR-domain result. Observe before boot can write.
        @(negedge clk); force dut.wdog_rst_req = 1'b1;
        repeat(5) @(negedge clk);
        if (!done || failed || busy || dut.rst_sys_n !== 0 || count != 655360)
            $fatal(1,"watchdog reset lost result or restarted MBIST");
        release dut.wdog_rst_req;
        repeat(3) @(negedge clk);
        if (dut.rst_sys_n !== 1 || !done || busy) $fatal(1,"watchdog reset did not recover");
        $display("PASS chip MBIST accesses=%0d banks=4 boot=Ibex_all_rows_ECC_byte_stores restart=%0d watchdog=preserved",count,restart);
        $finish;
        end
    end
    always @(posedge clk) begin
        cycles=cycles+1;
        if(cycles>4000000) $fatal(1,"chip integration timeout count=%0d done=%0d failed=%0d pc=%h reset=%0d",count,done,failed,dut.instr_addr,dut.rst_sys_n);
        if (por && !done) begin
            if(dut.rst_sys_n !== 0 || dut.timer_por_n !== 0)
                $fatal(1,"functional reset released during MBIST");
            if(dut.u_ram.g_ram_2048x64_ecc.u_test_port.func_req_i !== 0)
                $fatal(1,"functional request reached MBIST port during reset");
            if(dut.u_ram.g_ram_2048x64_ecc.row_en) begin
                count=count+1;
                bank_count[dut.u_ram.g_ram_2048x64_ecc.bank]=bank_count[dut.u_ram.g_ram_2048x64_ecc.bank]+1;
                if(dut.u_ram.g_ram_2048x64_ecc.row_we && dut.u_ram.g_ram_2048x64_ecc.row_bm !== 64'hffffffffffffffff)
                    $fatal(1,"partial raw MBIST write");
            end
        end
        if (dut.rst_sys_n && (dut.ram_ded_ev || dut.ram_sec_ev || dut.ram_rd_ev || dut.s_err[0]))
            $fatal(1,"RAM zero/init or functional ECC error after MBIST");
        if (dut.rst_sys_n && dut.s_req[0] && dut.s_we && dut.s_addr==32'h7ffc) begin
            if(dut.s_wdata==32'hbad0bad0) $fatal(1,"real Ibex RAM selfcheck failed");
            if(dut.s_wdata==32'h600dc0de) boot_pass=1;
        end
    end
endmodule
`default_nettype wire
