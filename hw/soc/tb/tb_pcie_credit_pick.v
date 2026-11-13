// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Random co-simulation of soc_pcie_credit_tx with SOC_PCIE_CREDIT_PICK
// (module soc_pcie_credit_tx) against the default build of the same file
// (module soc_pcie_credit_tx_ref); scripts/check_pcie_credit_pick.sh
// prepares both. docs/combined-timing.md section 19.
//
// Every output is compared in every cycle. The stimulus runs the flow
// control initialization (InitFC1 and InitFC2 for each class, finite and
// infinite credit), then UpdateFC events that advance the limits by small
// steps (and, now and then, malformed, backward or out-of-phase events),
// reservation requests held for random times (legal and illegal classes
// and sizes, replays), received-TLP indications, the local initialization
// flag, link losses and resets.
`timescale 1ns/1ps
`default_nettype none
module tb_pcie_credit_pick;
    integer seed, cycles, cycle, mismatches;
    integer grants, applied, inits, errors, link_drops, resets, replays;
    reg clk=1'b0;
    always #2 clk=!clk;
    reg rst_ni=1'b0, link_up=1'b0, local_done=1'b0, tlp_seen=1'b0;
    reg fc_valid=1'b0;
    reg [1:0] fc_phase=2'd0, fc_class=2'd0;
    reg [7:0] fc_header=8'd0;
    reg [11:0] fc_data=12'd0;
    reg res_valid=1'b0, res_replay=1'b0;
    reg [1:0] res_class=2'd0;
    reg [10:0] res_dw=11'd0;

    wire r_ready, c_ready, r_init, c_init, r_p1, c_p1, r_p2, c_p2, r_err, c_err;
    wire [23:0] r_hl, c_hl, r_hc, c_hc;
    wire [35:0] r_dl, c_dl, r_dc, c_dc;
    wire [5:0] r_inf, c_inf;
    soc_pcie_credit_tx_ref reference(
        .clk_i(clk), .rst_ni(rst_ni), .link_up_i(link_up), .local_init_done_i(local_done),
        .rx_tlp_seen_i(tlp_seen), .fc_valid_i(fc_valid), .fc_phase_i(fc_phase), .fc_class_i(fc_class),
        .fc_header_i(fc_header), .fc_data_i(fc_data), .reserve_valid_i(res_valid),
        .reserve_replay_i(res_replay), .reserve_class_i(res_class), .reserve_payload_dw_i(res_dw),
        .reserve_ready_o(r_ready), .initialized_o(r_init), .peer_init1_done_o(r_p1),
        .peer_init2_seen_o(r_p2), .protocol_error_o(r_err), .header_limit_o(r_hl),
        .header_consumed_o(r_hc), .data_limit_o(r_dl), .data_consumed_o(r_dc), .infinite_o(r_inf));
    soc_pcie_credit_tx candidate(
        .clk_i(clk), .rst_ni(rst_ni), .link_up_i(link_up), .local_init_done_i(local_done),
        .rx_tlp_seen_i(tlp_seen), .fc_valid_i(fc_valid), .fc_phase_i(fc_phase), .fc_class_i(fc_class),
        .fc_header_i(fc_header), .fc_data_i(fc_data), .reserve_valid_i(res_valid),
        .reserve_replay_i(res_replay), .reserve_class_i(res_class), .reserve_payload_dw_i(res_dw),
        .reserve_ready_o(c_ready), .initialized_o(c_init), .peer_init1_done_o(c_p1),
        .peer_init2_seen_o(c_p2), .protocol_error_o(c_err), .header_limit_o(c_hl),
        .header_consumed_o(c_hc), .data_limit_o(c_dl), .data_consumed_o(c_dc), .infinite_o(c_inf));
    wire [195:0] r_out={r_ready,r_init,r_p1,r_p2,r_err,r_hl,r_hc,r_dl,r_dc,r_inf};
    wire [195:0] c_out={c_ready,c_init,c_p1,c_p2,c_err,c_hl,c_hc,c_dl,c_dc,c_inf};

    function integer rnd(input integer n);
        begin rnd=$unsigned($random(seed))%n; end
    endfunction

    // Flow-control script of one link-up epoch: steps 0..2 send InitFC1
    // for classes 0..2, steps 3..5 InitFC2, then UpdateFC.
    integer step=0, gap=0, hold=0, up_for=0, init_delay=0, rst_hold=4, down_hold=0;
    integer c, room;
    reg [7:0] h_lim, h_used;
    reg [11:0] d_lim, d_used;
    reg [59:0] last_limits;
    reg last_init;

    task new_request;
        integer r;
        begin
            r=rnd(100);
            res_class<=r<2 ? 2'd3 : 2'(rnd(3));
            res_dw<=r<4 ? 11'(1025+rnd(40)) : (r<30 ? 11'd0 : (r<85 ? 11'(1+rnd(16)) : 11'(rnd(1025))));
            res_replay<=rnd(30)==0;
            hold=1+rnd(rnd(4)==0 ? 12 : 4);
        end
    endtask

    always @(posedge clk) begin
        cycle=cycle+1;
        tlp_seen<=rnd(200)==0;
        fc_valid<=0;
        if (rst_hold>0) begin
            rst_hold=rst_hold-1;
            if (rst_hold==0) rst_ni<=1;
        end else if (cycle>20 && rnd(40000)==0) begin
            rst_ni<=0; rst_hold=1+rnd(4); resets=resets+1; step=0; up_for=0;
        end
        if (down_hold>0) begin
            down_hold=down_hold-1;
            if (down_hold==0) link_up<=1;
        end else if (!link_up && cycle>6) begin
            link_up<=1;
        end else if (cycle>40 && rnd(15000)==0) begin
            link_up<=0; down_hold=1+rnd(20); link_drops=link_drops+1; step=0; up_for=0;
        end
        if (!rst_ni || !link_up) begin
            step=0; up_for=0; init_delay=rnd(60);
        end else up_for=up_for+1;
        local_done<=up_for>init_delay && rnd(5000)!=0;
        // Flow-control events.
        if (gap>0) gap=gap-1;
        else if (rst_ni && link_up && up_for>2) begin
            gap=rnd(8);
            fc_valid<=1;
            c=rnd(3);
            if (rnd(60)==0) begin
                // Malformed or out-of-phase event.
                fc_phase<=rnd(4); fc_class<=rnd(4); fc_header<=$random(seed); fc_data<=$random(seed);
            end else if (step<3) begin
                fc_phase<=0; fc_class<=step;
                fc_header<=rnd(6)==0 ? 8'd0 : 8'(1+rnd(100));
                fc_data<=rnd(6)==0 ? 12'd0 : 12'(1+rnd(1500));
                step=step+1;
            end else if (step<6) begin
                fc_phase<=1; fc_class<=step-3; fc_header<=$random(seed); fc_data<=$random(seed);
                step=step+1;
            end else if (rnd(25)==0) begin
                // An InitFC after initialization (ignored), or a backward update.
                fc_phase<=rnd(2); fc_class<=c; fc_header<=$random(seed); fc_data<=$random(seed);
                if (rnd(2)==0) begin
                    fc_phase<=2; fc_header<=r_hl[c*8+:8]-8'(1+rnd(4)); fc_data<=r_dl[c*12+:12]-12'(1+rnd(8));
                end
            end else begin
                // UpdateFC: advance the limit a little, keeping the available
                // credit inside the legal window (otherwise the event is an error).
                h_lim=r_hl[c*8+:8]; h_used=r_hc[c*8+:8];
                d_lim=r_dl[c*12+:12]; d_used=r_dc[c*12+:12];
                room=rnd(5);
                if (8'(h_lim+8'(room)-h_used)>=8'd120) room=0;
                fc_phase<=2; fc_class<=c; fc_header<=h_lim+8'(room);
                room=rnd(24);
                if (12'(d_lim+12'(room)-d_used)>=12'd2000) room=0;
                fc_data<=d_lim+12'(room);
                if (r_inf[2*c]) fc_header<=rnd(4)==0 ? 8'(rnd(4)) : 8'd0;
                if (r_inf[2*c+1]) fc_data<=rnd(4)==0 ? 12'(rnd(4)) : 12'd0;
            end
        end
        // Reservation requests: held for a few cycles, then changed; after a
        // grant the source usually moves to its next request.
        if (res_valid && r_ready) begin
            if (res_replay) replays=replays+1; else grants=grants+1;
            if (rnd(3)!=0) new_request;
        end
        if (hold>0) hold=hold-1;
        else new_request;
        res_valid<=rnd(10)<8;
    end

    always @(negedge clk) if (cycle>2) begin
        if (r_out!==c_out) begin
            mismatches=mismatches+1;
            if (mismatches<=10)
                $display("MISMATCH t=%0t cycle=%0d reference=%h candidate=%h", $time, cycle, r_out, c_out);
        end
        if (r_err===1'b1) errors=errors+1;
        if (r_init===1'b1 && last_init===1'b1 && {r_hl,r_dl}!==last_limits) applied=applied+1;
        last_limits={r_hl,r_dl}; last_init=r_init;
    end
    always @(posedge r_init) inits=inits+1;

    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed=1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles=300000;
        cycle=0; mismatches=0; grants=0; applied=0; inits=0; errors=0; link_drops=0; resets=0; replays=0;
        last_limits=0; last_init=0;
        wait (cycle>=cycles);
        @(negedge clk);
        $display("SUMMARY seed=%0d cycles=%0d grants=%0d replays=%0d limit_updates=%0d inits=%0d errors=%0d link_drops=%0d resets=%0d mismatches=%0d",
                 seed, cycle, grants, replays, applied, inits, errors, link_drops, resets, mismatches);
        if (mismatches==0 && grants>2000 && replays>50 && applied>500 && inits>=3 && errors>20 &&
            (cycles<100000 || (link_drops>=3 && resets>=2)))
            $display("RESULT PASS");
        else
            $display("RESULT FAIL");
        $finish;
    end
endmodule
`default_nettype wire
