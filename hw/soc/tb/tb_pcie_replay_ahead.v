// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
`default_nettype none
// Random co-simulation of soc_pcie_replay_tx with SOC_PCIE_REPLAY_AHEAD
// (candidate, optionally with SOC_PCIE_REPLAY_INBANK and
// SOC_PCIE_RESET_COPIES) against the default build (reference, renamed
// soc_pcie_replay_tx_ref), docs/combined-timing.md section 18. Both get the
// same captured frames, ACK/NAKs, reservation handshakes, transmit
// back-pressure, training, link losses and resets; every output of both is
// compared in every cycle, whether or not it is valid.
// scripts/check_pcie_replay_ahead.sh builds and runs it.
//   +seed=N +cycles=N
module tb_pcie_replay_ahead;
    parameter integer DEPTH=4, MAX_BYTES=38, TIMEOUT_CYCLES=256, MAX_REPLAYS=3;

    reg clk=0;
    always #5 clk=~clk;
    reg rst_ni=0, link_up=0, training=0, retrain_done=0;
    reg [7:0] in_data=0;
    reg in_sop=0, in_eop=0, in_valid=0;
    reg ack_valid=0, ack_nak=0;
    reg [11:0] ack_seq=0;
    reg reserve_ready=0, tx_ready=0;

    wire r_in_ready, r_ack_ready, r_reserve_valid, r_reserve_replay;
    wire [1:0] r_reserve_class;
    wire [10:0] r_reserve_dw;
    wire [7:0] r_tx_data;
    wire r_tx_sop, r_tx_eop, r_tx_valid, r_tx_replay;
    wire [4:0] r_buffered, r_outstanding;
    wire [11:0] r_acked;
    wire r_replay_started, r_timeout, r_protocol_error, r_retry_exhausted, r_source_error, r_retrain_request;
    wire c_in_ready, c_ack_ready, c_reserve_valid, c_reserve_replay;
    wire [1:0] c_reserve_class;
    wire [10:0] c_reserve_dw;
    wire [7:0] c_tx_data;
    wire c_tx_sop, c_tx_eop, c_tx_valid, c_tx_replay;
    wire [4:0] c_buffered, c_outstanding;
    wire [11:0] c_acked;
    wire c_replay_started, c_timeout, c_protocol_error, c_retry_exhausted, c_source_error, c_retrain_request;

    soc_pcie_replay_tx_ref #(.DEPTH(DEPTH), .MAX_BYTES(MAX_BYTES), .TIMEOUT_CYCLES(TIMEOUT_CYCLES),
                             .MAX_REPLAYS(MAX_REPLAYS)) reference (
        .clk_i(clk), .rst_ni(rst_ni), .link_up_i(link_up), .training_i(training), .retrain_done_i(retrain_done),
        .in_data_i(in_data), .in_sop_i(in_sop), .in_eop_i(in_eop), .in_valid_i(in_valid), .in_ready_o(r_in_ready),
        .ack_valid_i(ack_valid), .ack_nak_i(ack_nak), .ack_sequence_i(ack_seq), .ack_ready_o(r_ack_ready),
        .reserve_valid_o(r_reserve_valid), .reserve_ready_i(reserve_ready), .reserve_class_o(r_reserve_class),
        .reserve_payload_dw_o(r_reserve_dw), .reserve_replay_o(r_reserve_replay),
        .tx_data_o(r_tx_data), .tx_sop_o(r_tx_sop), .tx_eop_o(r_tx_eop), .tx_valid_o(r_tx_valid),
        .tx_replay_o(r_tx_replay), .tx_ready_i(tx_ready), .buffered_o(r_buffered), .outstanding_o(r_outstanding),
        .acknowledged_sequence_o(r_acked), .replay_started_o(r_replay_started), .timeout_o(r_timeout),
        .protocol_error_o(r_protocol_error), .retry_exhausted_o(r_retry_exhausted),
        .source_error_o(r_source_error), .retrain_request_o(r_retrain_request));
    soc_pcie_replay_tx #(.DEPTH(DEPTH), .MAX_BYTES(MAX_BYTES), .TIMEOUT_CYCLES(TIMEOUT_CYCLES),
                         .MAX_REPLAYS(MAX_REPLAYS)) candidate (
        .clk_i(clk), .rst_ni(rst_ni), .link_up_i(link_up), .training_i(training), .retrain_done_i(retrain_done),
`ifdef COSIM_RESET_COPIES
        // SOC_PCIE_RESET_COPIES: the reset copy is equal to rst_ni at all times.
        .rst_copy_ni(rst_ni),
`endif
        .in_data_i(in_data), .in_sop_i(in_sop), .in_eop_i(in_eop), .in_valid_i(in_valid), .in_ready_o(c_in_ready),
        .ack_valid_i(ack_valid), .ack_nak_i(ack_nak), .ack_sequence_i(ack_seq), .ack_ready_o(c_ack_ready),
        .reserve_valid_o(c_reserve_valid), .reserve_ready_i(reserve_ready), .reserve_class_o(c_reserve_class),
        .reserve_payload_dw_o(c_reserve_dw), .reserve_replay_o(c_reserve_replay),
        .tx_data_o(c_tx_data), .tx_sop_o(c_tx_sop), .tx_eop_o(c_tx_eop), .tx_valid_o(c_tx_valid),
        .tx_replay_o(c_tx_replay), .tx_ready_i(tx_ready), .buffered_o(c_buffered), .outstanding_o(c_outstanding),
        .acknowledged_sequence_o(c_acked), .replay_started_o(c_replay_started), .timeout_o(c_timeout),
        .protocol_error_o(c_protocol_error), .retry_exhausted_o(c_retry_exhausted),
        .source_error_o(c_source_error), .retrain_request_o(c_retrain_request));

    wire [56:0] r_out={r_in_ready, r_ack_ready, r_reserve_valid, r_reserve_class, r_reserve_dw, r_reserve_replay,
                       r_tx_data, r_tx_sop, r_tx_eop, r_tx_valid, r_tx_replay, r_buffered, r_outstanding, r_acked,
                       r_replay_started, r_timeout, r_protocol_error, r_retry_exhausted, r_source_error, r_retrain_request};
    wire [56:0] c_out={c_in_ready, c_ack_ready, c_reserve_valid, c_reserve_class, c_reserve_dw, c_reserve_replay,
                       c_tx_data, c_tx_sop, c_tx_eop, c_tx_valid, c_tx_replay, c_buffered, c_outstanding, c_acked,
                       c_replay_started, c_timeout, c_protocol_error, c_retry_exhausted, c_source_error, c_retrain_request};

    integer seed, cycles, cycle=0;
    integer mismatches=0, frames_in=0, bad_in=0, frames_out=0, replayed_out=0, stalls=0, take_pairs=0;
    integer take_gaps=0, replays=0, resets=0, losses=0, source_errors=0, acks=0;
    reg [7:0] frame [0:63];
    integer flen=0, fpos=0, gap=0, rst_hold=0, link_hold=0, train_hold=0, error_wait=0;
    reg frame_bad=0;
    reg [11:0] tb_seq=0;
    reg took_prev=0, held_prev=0;

    function integer rnd(input integer n);
        begin rnd=$unsigned($random(seed))%n; end
    endfunction

    // One LCRC octet, as soc_pcie_crc32_byte (reflected 04C11DB7).
    function [31:0] crc_step(input [31:0] s, input [7:0] d);
        integer i;
        begin
            crc_step=s;
            for (i=0; i<8; i=i+1) crc_step=(crc_step>>1)^({32{crc_step[0]^d[i]}} & 32'hedb88320);
        end
    endfunction

    // One encoded TLP (sequence, header and payload bytes, LCRC) into
    // frame[0..flen-1]; about one in fifty is malformed.
    task build;
        integer r, body, i, n;
        reg [31:0] c;
        reg [7:0] kind;
        begin
            r=rnd(1000);
            body=12+rnd(MAX_BYTES-18+1);
            case (rnd(6))
                0: kind=8'h00; 1: kind=8'h40; 2: kind=8'h0a; 3: kind=8'h4a; 4: kind=8'h04;
                default: kind=$random(seed);
            endcase
            frame[0]={4'h0,tb_seq[11:8]}; frame[1]=tb_seq[7:0];
            for (i=0; i<body; i=i+1) frame[2+i]=$random(seed);
            frame[2]=kind;
            c=32'hffffffff;
            for (i=0; i<2+body; i=i+1) c=crc_step(c,frame[i]);
            c=~c;
            frame[2+body]=c[7:0]; frame[3+body]=c[15:8]; frame[4+body]=c[23:16]; frame[5+body]=c[31:24];
            flen=body+6; frame_bad=0;
            if (r<4) begin i=2+rnd(flen-2); frame[i]=frame[i]^(8'h01<<rnd(8)); frame_bad=1; end // LCRC
            else if (r<7) begin frame[1]=frame[1]^8'h01; frame_bad=1; end                // sequence
            else if (r<9) begin flen=3+rnd(15); frame_bad=1; end                        // too short
            else if (r<10) begin                                                         // too long
                n=MAX_BYTES+1+rnd(8);
                for (i=flen; i<n; i=i+1) frame[i]=$random(seed);
                flen=n; frame_bad=1;
            end else if (r<11) begin frame[0]=frame[0] | 8'h40; frame_bad=1; end         // reserved bits
            fpos=0;
        end
    endtask

    always @(posedge clk) begin
        cycle=cycle+1;
        tx_ready<=rnd(16)<(cycle%4096<1024 ? 5 : 13);
        reserve_ready<=rnd(4)!=0;
        retrain_done<=0;
        if (rst_hold>0) begin
            rst_hold=rst_hold-1;
            if (rst_hold==0) rst_ni<=1;
        end else if (cycle>20 && rnd(40000)==0) begin
            rst_ni<=0; rst_hold=1+rnd(5); resets=resets+1;
            flen=0; in_valid<=0; ack_valid<=0; tb_seq=0; error_wait=0;
        end else if (link_hold>0) begin
            link_hold=link_hold-1;
            if (link_hold==0) link_up<=1;
        end else if (rst_ni && (rnd(6000)==0 || error_wait==1)) begin
            link_up<=0; link_hold=1+rnd(20); losses=losses+1;
            flen=0; in_valid<=0; ack_valid<=0; tb_seq=0; error_wait=0;
        end else begin
            if (error_wait>1) error_wait=error_wait-1;
            // Training: a few cycles, with retrain_done at the end (clears a
            // halt after retry exhaustion; a source error waits for link loss).
            if (train_hold>0) begin
                train_hold=train_hold-1;
                if (train_hold==0) begin training<=0; retrain_done<=1; end
            end else if (rnd(r_retrain_request ? 40 : 3000)==0) begin
                training<=1; train_hold=1+rnd(30);
            end
            // Captured frames: a byte stays presented until accepted.
            if (in_valid && r_in_ready) begin
                if (in_eop) begin
                    frames_in=frames_in+1;
                    if (frame_bad) bad_in=bad_in+1; else tb_seq=tb_seq+1'b1;
                    flen=0; gap=rnd(3)==0 ? rnd(40) : 0;
                end else fpos=fpos+1;
                in_valid<=0;
            end
            if (flen==0 && gap>0) gap=gap-1;
            else begin
                if (flen==0) build;
                if (rnd(6)==0) in_valid<=0;
                else begin
                    in_valid<=1; in_data<=frame[fpos]; in_sop<=fpos==0; in_eop<=fpos==flen-1;
                end
            end
            // ACK/NAK: held until consumed; mostly within the window.
            if (ack_valid && r_ack_ready) begin ack_valid<=0; acks=acks+1; end
            else if (!ack_valid && rnd(48)==0) begin
                ack_valid<=1; ack_nak<=rnd(5)==0;
                ack_seq<=rnd(20)==0 ? 12'($random(seed)) : r_acked+12'(rnd(r_outstanding+1));
            end
        end
        // A source error halts until link loss: drop the link a little later.
        if (r_source_error && link_up && link_hold==0 && error_wait==0) error_wait=2+rnd(200);
    end

`ifdef COSIM_WRITE_PREDECODE
    // Inspect actual memory write strobes and all stored bytes, including
    // bytes in malformed frames that never reach an output scoreboard.
    integer write_check;
    always @(negedge clk) if(cycle>2) begin
        for(write_check=0;write_check<DEPTH*MAX_BYTES;write_check=write_check+1) begin
            if((reference.write_valid && reference.write_address==write_check) !==
               (candidate.write_group[write_check/16] && candidate.write_low[write_check%16])) begin
                $display("MISMATCH byte write strobe cycle=%0d byte=%0d",cycle,write_check);
                $fatal(1,"write strobe differs");
            end
            if(reference.bytes[write_check] !== candidate.bytes[write_check]) begin
                $display("MISMATCH stored byte cycle=%0d byte=%0d",cycle,write_check);
                $fatal(1,"stored byte differs");
            end
        end
    end
`endif

    always @(negedge clk) if (cycle>2) begin
        if (r_out!==c_out) begin
            mismatches=mismatches+1;
            if (mismatches<=10)
                $display("MISMATCH t=%0t cycle=%0d reference=%h candidate=%h", $time, cycle, r_out, c_out);
        end
        if (rst_ni && link_up && r_tx_valid && tx_ready && r_tx_eop) begin
            frames_out=frames_out+1;
            if (r_tx_replay) replayed_out=replayed_out+1;
        end
        if (rst_ni && link_up && r_tx_valid && !tx_ready && !r_tx_sop) stalls=stalls+1;
        if (r_replay_started) replays=replays+1;
        if (r_source_error && !held_prev) source_errors=source_errors+1;
        held_prev=r_source_error;
        // The store read's cases: a byte taken in consecutive cycles, and a
        // byte taken after a cycle without one in the same frame.
        if (reference.core_taken && took_prev) take_pairs=take_pairs+1;
        if (reference.core_taken && !took_prev && reference.read_pos!=0) take_gaps=take_gaps+1;
        took_prev=reference.core_taken;
    end

    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed=1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles=300000;
        repeat (4) @(posedge clk);
        rst_ni<=1; link_up<=1;
        wait (cycle>=cycles);
        @(negedge clk);
        $display("SUMMARY seed=%0d cycles=%0d frames_in=%0d bad_in=%0d frames_out=%0d replayed_out=%0d replays=%0d stalls=%0d take_pairs=%0d take_gaps=%0d acks=%0d losses=%0d source_errors=%0d resets=%0d mismatches=%0d",
                 seed, cycle, frames_in, bad_in, frames_out, replayed_out, replays, stalls, take_pairs, take_gaps,
                 acks, losses, source_errors, resets, mismatches);
        if (mismatches==0 && frames_out>1000 && replayed_out>200 && replays>50 && stalls>1000 &&
            take_pairs>10000 && take_gaps>1000 && losses>10 && source_errors>5 && (cycles<100000 || resets>=2))
            $display("RESULT PASS");
        else
            $display("RESULT FAIL");
        $finish;
    end
endmodule
`default_nettype wire
