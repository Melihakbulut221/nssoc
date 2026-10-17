// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Common-clock, four-lane DATA ordinal deskew after one qualified SDS cohort.
// The MAC must arm a NEW, reset/empty epoch in an SDS-eligible LTSSM state.
// Inputs are complete, stable ready/valid records from the recovered-lane CDCs.
// A new arm while busy, upstream fault, bad cohort or timeout aborts until reset.
// First block after SDS must be DATA on EACH lane (no Loopback exception here).
// Later SKPs retire independently through lossless sideband handshakes; DATA
// retires atomically in lane order. SKP trailer validation/LFSR compensation is
// owned by the consumer; DATA here remains scrambled. No full LTSSM/rate-closure.
// Deasserted active_o invalidates the epoch immediately; sticky fault_o follows
// on the clock edge. A consumer must discard an aborted buffered prefix.
module soc_pcie_gen3_sds_deskew_v1 #(
    parameter MAX_SKEW_CYCLES = 64
) (
    input wire clk_i, rst_ni,
    input wire arm_i, upstream_fault_i,
    input wire [3:0] valid_i,
    output reg [3:0] ready_o,
    input wire [775:0] block_i,
    input wire [11:0] length_code_i,
    input wire [3:0] skp_i, eieos_i, realign_i,
    output wire stream_start_o,
    output wire active_o,
    output reg fault_o,
    output wire data_valid_o,
    input wire data_ready_i,
    output wire [511:0] data_o,
    output reg [3:0] skp_valid_o,
    input wire [3:0] skp_ready_i,
    output wire [775:0] skp_block_o,
    output wire [11:0] skp_length_code_o
);
    localparam [1:0] IDLE=0, SEEK=1, START=2, RUN=3;
    localparam [129:0] EIEOS={128'hff00ff00ff00ff00ff00ff00ff00ff00,2'b01};
    localparam [129:0] SDS={{15{8'h55}},8'he1,2'b01};
    localparam AGE_BITS=$clog2(MAX_SKEW_CYCLES+1);
    generate if (MAX_SKEW_CYCLES < 2 || MAX_SKEW_CYCLES > 65535) begin: bad_parameter
        initial $fatal(1,"MAX_SKEW_CYCLES must be 2..65535");
    end endgenerate
    reg [1:0] state_q;
    reg [3:0] seen_eieos_q, seen_sds_q;
    reg [AGE_BITS-1:0] age_q;
    wire [3:0] is_data, is_sds, is_eieos, is_skp, record_ok;
    wire all_data = &(valid_i & is_data);
    reg bad_head;
    wire abort_now = upstream_fault_i || (arm_i && state_q != IDLE) || bad_head;
    wire enabled = rst_ni && !fault_o && !abort_now;
    assign stream_start_o = enabled && state_q == START;
    assign active_o = enabled && (state_q == START || state_q == RUN);
    assign data_valid_o = enabled && state_q == RUN && all_data;
    assign skp_block_o = block_i;
    assign skp_length_code_o = length_code_i;
    genvar lane;
    generate for (lane=0; lane<4; lane=lane+1) begin: classify
        wire [193:0] b=block_i[lane*194 +: 194];
        wire [2:0] n=length_code_i[lane*3 +: 3];
        wire fixed_block=n==2 && b[193:130]==0;
        wire exact_eieos=fixed_block && b[129:0]==EIEOS;
        wire exact_sds=fixed_block && b[129:0]==SDS;
        // A SKP has 4*(n+1) AA symbols, E1, then three opaque trailer bytes.
        reg skp_encoding;
        integer j;
        always @* begin
            skp_encoding=n<=4 && b[1:0]==2'b01;
            for (j=0; j<20; j=j+1)
                if (j < 4*(n+1) && b[2+j*8 +: 8]!=8'haa) skp_encoding=0;
            case (n)
                0: if (b[41:34]!=8'he1 || b[193:66]!=0) skp_encoding=0;
                1: if (b[73:66]!=8'he1 || b[193:98]!=0) skp_encoding=0;
                2: if (b[105:98]!=8'he1 || b[193:130]!=0) skp_encoding=0;
                3: if (b[137:130]!=8'he1 || b[193:162]!=0) skp_encoding=0;
                4: if (b[169:162]!=8'he1) skp_encoding=0;
                default: skp_encoding=0;
            endcase
        end
        assign is_data[lane]=fixed_block && b[1:0]==2'b10 && !skp_i[lane] && !eieos_i[lane] && !realign_i[lane];
        assign is_sds[lane]=exact_sds && !skp_i[lane] && !eieos_i[lane] && !realign_i[lane];
        assign is_eieos[lane]=exact_eieos && eieos_i[lane] && !skp_i[lane];
        assign is_skp[lane]=skp_encoding && skp_i[lane] && !eieos_i[lane] && !realign_i[lane];
        assign record_ok[lane]=is_data[lane] || is_eieos[lane] || is_sds[lane] || is_skp[lane] ||
            (fixed_block && b[1:0]==2'b01 && !skp_i[lane] && !eieos_i[lane] && !realign_i[lane] &&
             b[9:2]!=8'he1 && b[9:2]!=8'haa && !exact_eieos);
        assign data_o[lane*128 +: 128]=b[129:2];
    end endgenerate
    integer k;
    integer q;
    always @* begin
        bad_head=0;
        for (k=0; k<4; k=k+1) begin
            if (valid_i[k] && state_q != IDLE) begin
                if (!record_ok[k]) bad_head=1;
                if (state_q==SEEK) begin
                    if (seen_sds_q[k] && !is_data[k]) bad_head=1;
                    if (!seen_sds_q[k] && (is_data[k] || (is_sds[k] && !seen_eieos_q[k]))) bad_head=1;
                end else if (state_q==START ? !is_data[k] : (!is_data[k] && !is_skp[k])) bad_head=1;
            end
        end
    end
    always @* begin
        ready_o=0;
        skp_valid_o=0;
        if (enabled) begin
            if (state_q==SEEK) ready_o=~seen_sds_q;
            if (state_q==RUN) begin
                skp_valid_o=valid_i & is_skp;
                ready_o=(skp_valid_o & skp_ready_i) | ({4{all_data && data_ready_i}});
            end
        end
    end
    always @(posedge clk_i) begin
        if (!rst_ni) begin
            state_q<=IDLE;
            seen_eieos_q<=0;
            seen_sds_q<=0;
            age_q<=0;
            fault_o<=0;
        end else if (abort_now) begin
            fault_o<=1;
        end else if (!fault_o) begin
            case (state_q)
                IDLE: if (arm_i) state_q<=SEEK;
                SEEK: begin
                    for (q=0; q<4; q=q+1) begin
                        if (valid_i[q] && ready_o[q]) begin
                            if (is_eieos[q]) seen_eieos_q[q]<=1;
                            if (is_sds[q]) seen_sds_q[q]<=1;
                        end
                    end
                    if (&seen_sds_q && all_data) state_q<=START;
                    else if (age_q==MAX_SKEW_CYCLES) fault_o<=1;
                    else if ((|seen_sds_q) || (|(valid_i & ready_o & is_sds))) age_q<=age_q+1'b1;
                end
                START: state_q<=RUN;
                RUN: state_q<=RUN;
            endcase
        end
    end
endmodule
`default_nettype wire
