// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Random co-simulation of soc_pcie_rx_credit with SOC_PCIE_RX_READ_AHEAD
// (module soc_pcie_rx_credit) against the default build of the same file
// (module soc_pcie_rx_credit_ref); scripts/check_pcie_rx_read_ahead.sh
// prepares both. docs/combined-timing.md section 12.
//
// Every output is compared in every cycle, and out_data_o/out_error_o
// while out_valid_o. The stimulus mixes legal TLPs of every class (posted,
// non-posted, completions, messages), malformed TLPs (length, traffic
// class, digest, oversize, undersize, missing start, error beats), good
// and bad DLLPs, input gaps, output back-pressure, random verdicts, link
// loss, training, FC initialization gaps and resets. It also checks the
// claim the read-ahead registers rely on: the read cursor never passes
// CAP-1.
`timescale 1ns/1ps
`default_nettype none
module tb_pcie_rx_credit_read_ahead;
    parameter integer MAX_TLP_DWORDS=8,SLOTS_PER_CLASS=2,COMPLETER_ONLY=1;
    localparam integer CAP=MAX_TLP_DWORDS*4+6;
    integer seed,cycles,cycle,mismatches,beats,frames,commits,commit_mid,commit_shake,max_index;
    reg clk=1'b0;
    always #2 clk=!clk;
    reg rst_ni=1'b0,link_up_i=1'b0,training_i=1'b0,initialized_i=1'b0;
    reg [7:0] rx_data_i=8'd0;
    reg rx_sop_i=1'b0,rx_eop_i=1'b0,rx_valid_i=1'b0,rx_dllp_i=1'b0,rx_error_i=1'b0;
    reg out_ready_i=1'b0,accepted=1'b0,duplicate=1'b0,rejected=1'b0;
    wire r_ready,c_ready,r_sop,c_sop,r_eop,c_eop,r_valid,c_valid,r_dllp,c_dllp,r_err,c_err;
    wire [7:0] r_data,c_data,r_queued,c_queued;
    wire [23:0] r_hl,c_hl,r_occ,c_occ;
    wire [35:0] r_dl,c_dl;
    wire r_rel,c_rel,r_drop,c_drop,r_perr,c_perr,r_rec,c_rec;
    wire [1:0] r_relc,c_relc;
    wire [11:0] r_reld,c_reld;
    soc_pcie_rx_credit_ref #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS),.SLOTS_PER_CLASS(SLOTS_PER_CLASS),
        .COMPLETER_ONLY(COMPLETER_ONLY)) reference(
        .clk_i(clk),.rst_ni(rst_ni),.link_up_i(link_up_i),.training_i(training_i),.initialized_i(initialized_i),
        .rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),.rx_eop_i(rx_eop_i),.rx_valid_i(rx_valid_i),
        .rx_dllp_i(rx_dllp_i),.rx_error_i(rx_error_i),.rx_ready_o(r_ready),
        .out_data_o(r_data),.out_sop_o(r_sop),.out_eop_o(r_eop),.out_valid_o(r_valid),
        .out_dllp_o(r_dllp),.out_error_o(r_err),.out_ready_i(out_ready_i),
        .packet_accepted_i(accepted),.packet_duplicate_i(duplicate),.packet_rejected_i(rejected),
        .header_limit_o(r_hl),.data_limit_o(r_dl),.occupied_o(r_occ),.queued_o(r_queued),
        .released_o(r_rel),.released_class_o(r_relc),.released_data_o(r_reld),
        .dropped_o(r_drop),.protocol_error_o(r_perr),.recovery_request_o(r_rec));
    soc_pcie_rx_credit #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS),.SLOTS_PER_CLASS(SLOTS_PER_CLASS),
        .COMPLETER_ONLY(COMPLETER_ONLY)) candidate(
        .clk_i(clk),.rst_ni(rst_ni),.link_up_i(link_up_i),.training_i(training_i),.initialized_i(initialized_i),
        .rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),.rx_eop_i(rx_eop_i),.rx_valid_i(rx_valid_i),
        .rx_dllp_i(rx_dllp_i),.rx_error_i(rx_error_i),.rx_ready_o(c_ready),
        .out_data_o(c_data),.out_sop_o(c_sop),.out_eop_o(c_eop),.out_valid_o(c_valid),
        .out_dllp_o(c_dllp),.out_error_o(c_err),.out_ready_i(out_ready_i),
        .packet_accepted_i(accepted),.packet_duplicate_i(duplicate),.packet_rejected_i(rejected),
        .header_limit_o(c_hl),.data_limit_o(c_dl),.occupied_o(c_occ),.queued_o(c_queued),
        .released_o(c_rel),.released_class_o(c_relc),.released_data_o(c_reld),
        .dropped_o(c_drop),.protocol_error_o(c_perr),.recovery_request_o(c_rec));

    function integer pick(input integer n);
        begin pick=n>0 ? $unsigned($random(seed))%n : 0; end
    endfunction

    // The frame being presented.
    reg [7:0] frame[0:CAP+7];
    reg frame_error[0:CAP+7];
    integer frame_length,frame_position;
    reg frame_dllp,frame_nosop,fmt4;
    reg [2:0] type_low,tc;
    reg [4:0] type_any;
    reg [3:0] tc_low;
    integer kind,payload,header,length,b,stall,link_timer,idle;
    task build_frame;
        begin
            frame_dllp=pick(5)==0;
            frame_nosop=pick(64)==0;
            for(b=0;b<CAP+8;b=b+1) begin frame[b]=pick(256);frame_error[b]=pick(256)==0; end
            if(frame_dllp) begin
                frame_length=pick(12)==0 ? 1+pick(9) : 6;
            end else begin
                kind=pick(9);
                header=pick(2) ? 16 : 12;
                payload=0;
                fmt4=header==16;
                type_low=pick(8);
                type_any=pick(32);
                tc=1+pick(7);
                tc_low=pick(16);
                case(kind)
                    0,1: begin frame[2]={2'b01,fmt4,5'h00}; payload=1+pick((CAP-header-6)/4); end // MWr
                    2: frame[2]={2'b00,fmt4,5'h00};                                                  // MRd
                    3: begin frame[2]={2'b01,1'b0,5'h04}; header=12; payload=1; end                // CfgWr0
                    4: begin frame[2]={2'b00,1'b0,5'h05}; header=12; end                           // CfgRd1
                    5: begin frame[2]={2'b00,1'b1,2'b10,type_low}; header=16; end                  // Msg
                    6: begin frame[2]={2'b01,1'b0,5'h0a}; header=12; payload=1+pick(2); end        // CplD
                    7: begin frame[2]={2'b00,1'b0,5'h0b}; header=12; end                           // CplLk
                    default: begin
                        frame[2]={pick(4)==0,pick(2)==0,fmt4,type_any}; payload=pick(3);
                    end
                endcase
                frame[3]=pick(16)==0 ? {1'b0,tc,4'h0} : {4'b0000,tc_low};
                frame[4]={pick(16)==0,7'b0000000};
                frame[5]=frame[2][6] ? payload : pick(256);
                if(frame[2][6] && payload==0) frame[5]=1;
                length=2+header+(frame[2][6] ? (payload==0 ? 1 : payload)*4 : 0)+4;
                case(pick(16))
                    0: length=length+1+pick(4);
                    1: length=length>18 ? length-1-pick(3) : length;
                    2: length=CAP+1+pick(6);
                    3: length=1+pick(17);
                    default: ;
                endcase
                if(length>CAP+8) length=CAP+8;
                frame_length=length;
            end
            frame_position=0;
        end
    endtask

    integer seed0;
    initial begin
        if(!$value$plusargs("seed=%d",seed)) seed=1;
        if(!$value$plusargs("cycles=%d",cycles)) cycles=300000;
        seed0=seed;
        mismatches=0;beats=0;frames=0;commits=0;commit_mid=0;commit_shake=0;max_index=0;
        frame_length=0;frame_position=0;stall=0;link_timer=200;idle=0;
        for(cycle=0;cycle<cycles;cycle=cycle+1) @(posedge clk);
        $display("SUMMARY seed=%0d cycles=%0d beats=%0d frames=%0d commits=%0d commits_mid_frame=%0d commits_with_handshake=%0d max_index=%0d mismatches=%0d",
            seed0,cycles,beats,frames,commits,commit_mid,commit_shake,max_index,mismatches);
        if(mismatches==0 && max_index<CAP && frames>1000 && commit_mid>100) $display("RESULT PASS");
        else $display("RESULT FAIL");
        $finish;
    end

    // Stimulus: inputs change after each rising edge (non-blocking), the
    // handshakes are sampled from the values before it.
    always @(posedge clk) begin
        // Input stream.
        if(rx_valid_i && r_ready) frame_position=frame_position+1;
        if(frame_position>=frame_length) begin
            if(idle>0) idle=idle-1;
            else begin build_frame; idle=pick(4)==0 ? pick(40) : 0; end
        end
        if(frame_position<frame_length && pick(8)!=0) begin
            rx_valid_i<=1'b1;
            rx_data_i<=frame[frame_position];
            rx_sop_i<=frame_position==0 && !frame_nosop;
            rx_eop_i<=frame_position==frame_length-1;
            rx_dllp_i<=frame_dllp ^ (pick(512)==0);
            rx_error_i<=frame_error[frame_position];
        end else begin
            // A beat is withdrawn only before it was taken (the bench may
            // also leave a gap between beats); the queue sees the same.
            rx_valid_i<=1'b0;rx_data_i<=pick(256);rx_sop_i<=pick(2);rx_eop_i<=pick(2);
            rx_dllp_i<=pick(2);rx_error_i<=pick(2);
        end
        // Output back-pressure, in runs.
        if(stall>0) begin stall=stall-1; out_ready_i<=1'b0; end
        else if(pick(64)==0) begin stall=pick(30); out_ready_i<=1'b0; end
        else out_ready_i<=pick(4)!=0;
        // Verdicts.
        case(pick(8))
            0: begin accepted<=1'b1;duplicate<=1'b0;rejected<=1'b0; end
            1: begin accepted<=1'b0;duplicate<=pick(3)==0;rejected<=pick(3)==0; end
            2: begin accepted<=1'b1;duplicate<=1'b0;rejected<=pick(2); end
            default: begin accepted<=1'b0;duplicate<=1'b0;rejected<=1'b0; end
        endcase
        // Link state, FC initialization and reset.
        if(link_timer>0) link_timer=link_timer-1;
        else begin
            case(pick(6))
                0: begin link_up_i<=1'b0; frame_length=0; link_timer=1+pick(20); end
                1: begin training_i<=!training_i; link_timer=1+pick(40); end
                2: begin initialized_i<=pick(4)!=0; link_timer=pick(200); end
                3: begin rst_ni<=pick(4)!=0; frame_length=0; link_timer=1+pick(10); end
                default: begin
                    rst_ni<=1'b1;link_up_i<=1'b1;
                    if(pick(2)) training_i<=1'b0;
                    if(pick(2)) initialized_i<=1'b1;
                    link_timer=32+pick(8192);
                end
            endcase
        end
    end

    // Coverage of the cases the read-ahead registers must get right.
    always @(posedge clk) if(rst_ni) begin
        if(reference.output_index>max_index) max_index=reference.output_index;
        if(reference.commit) begin
            commits=commits+1;
            if(reference.output_active) commit_mid=commit_mid+1;
            if(reference.handshake) commit_shake=commit_shake+1;
        end
        if(r_valid && out_ready_i) begin
            beats=beats+1;
            if(r_eop) frames=frames+1;
        end
    end

    always @(negedge clk) begin
        if(r_ready!==c_ready || r_valid!==c_valid || r_sop!==c_sop || r_eop!==c_eop ||
           r_dllp!==c_dllp || (r_valid && (r_data!==c_data || r_err!==c_err)) ||
           r_hl!==c_hl || r_dl!==c_dl || r_occ!==c_occ || r_queued!==c_queued ||
           r_rel!==c_rel || r_relc!==c_relc || r_reld!==c_reld || r_drop!==c_drop ||
           r_perr!==c_perr || r_rec!==c_rec) begin
            mismatches=mismatches+1;
            if(mismatches<=10)
                $display("MISMATCH t=%0t valid %b/%b data %h/%h eop %b/%b ready %b/%b index %0d",
                    $time,r_valid,c_valid,r_data,c_data,r_eop,c_eop,r_ready,c_ready,reference.output_index);
        end
    end
endmodule
`default_nettype wire
