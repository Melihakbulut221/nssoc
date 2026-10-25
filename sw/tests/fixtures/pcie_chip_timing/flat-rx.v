// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Bounded VC0 packet ownership at a ready/valid byte-frame boundary. A separate
// six-byte DLLP buffer can bypass queued TLPs. TLP arrival order is preserved.
// Only a NEW sequence-accepted packet releases advertised credits; duplicate,
// corrupt and out-of-order copies release storage without minting credits.
// Completer-only mode has no requester admission: unexpected Cpl requests link
// recovery. Its zero Cpl advertisement means infinity, not zero physical space.
module soc_pcie_rx_credit #(
    parameter integer MAX_TLP_DWORDS=8,SLOTS_PER_CLASS=2,COMPLETER_ONLY=0
)(
    input wire clk_i,rst_ni,link_up_i,training_i,initialized_i,
    input wire [7:0] rx_data_i,
    input wire rx_sop_i,rx_eop_i,rx_valid_i,rx_dllp_i,rx_error_i,
    output wire rx_ready_o,
    output wire [7:0] out_data_o,
    output wire out_sop_o,out_eop_o,out_valid_o,out_dllp_o,out_error_o,
    input wire out_ready_i,
    input wire packet_accepted_i,packet_duplicate_i,packet_rejected_i,
    output reg [23:0] header_limit_o,
    output reg [35:0] data_limit_o,
    output reg [23:0] occupied_o,
    output wire [7:0] queued_o,
    output reg released_o,
    output reg [1:0] released_class_o,
    output reg [11:0] released_data_o,
    output reg dropped_o,protocol_error_o,recovery_request_o
);
    localparam integer CAP=MAX_TLP_DWORDS*4+6;
    localparam integer SLOTS=3*SLOTS_PER_CLASS;
    localparam integer CW=$clog2(CAP+2),SW=$clog2(SLOTS+1);
    localparam integer DATA_PER_SLOT=(MAX_TLP_DWORDS-3+3)/4;
    localparam [7:0] H_INIT=SLOTS_PER_CLASS;
    localparam [11:0] D_INIT=SLOTS_PER_CLASS*DATA_PER_SLOT;
    reg [7:0] staging[0:CAP-1];
    reg [7:0] dllp[0:5];
    reg [7:0] packets[0:SLOTS*CAP-1];
    reg [CW-1:0] lengths[0:SLOTS-1];
    reg [11:0] units[0:SLOTS-1];
    reg errors[0:SLOTS-1];
    reg [SW-1:0] order[0:SLOTS-1];
    reg [SLOTS-1:0] used;
    reg [SW-1:0] qread,qwrite,qcount;
    reg input_active,input_dllp,input_bad,stage_pending,dllp_pending,dllp_bad;
    reg [CW-1:0] input_count,stage_length;
    reg stage_bad;
    reg [2:0] dllp_length;
    reg output_active,output_dllp,waiting;
    reg [CW-1:0] output_index;
    integer i,j,k,classification,payload_dw,expected_length,free_slot;
    reg shape_ok;
    wire incoming_kind=input_active ? input_dllp : rx_dllp_i;
    assign rx_ready_o=rst_ni && link_up_i &&
        (input_active || (!training_i && (incoming_kind ? !dllp_pending :
                                            initialized_i && !stage_pending)));
    always @* begin
        classification=-1;
        if(staging[2][4:0]==5'h00) classification=staging[2][6] ? 0 : 1;
        else if(staging[2][4:0]==5'h01 || staging[2][4:0]==5'h02 ||
                staging[2][4:0]==5'h04 || staging[2][4:0]==5'h05) classification=1;
        else if(staging[2][4:0]==5'h0a || staging[2][4:0]==5'h0b) classification=2;
        else if(staging[2][4:3]==2'b10) classification=0;
        payload_dw=staging[2][6] ? {staging[4][1:0],staging[5]} : 0;
        if(staging[2][6] && payload_dw==0) payload_dw=1024;
        expected_length=2+(staging[2][5] ? 16 : 12)+payload_dw*4+4;
        // TD/ECRC, TLP prefixes and non-VC0 traffic are outside this endpoint.
        shape_ok=stage_length>=18 && stage_length<=CAP && classification>=0 &&
                 !staging[2][7] && staging[3][6:4]==0 && !staging[4][7] &&
                 stage_length==expected_length && !(COMPLETER_ONLY && classification==2);
        free_slot=-1;
        for(i=SLOTS-1;i>=0;i=i-1)
            if(!used[i] && i/SLOTS_PER_CLASS==classification) free_slot=i;
        occupied_o=0;
        for(j=0;j<SLOTS;j=j+1)
            if(used[j]) occupied_o[(j/SLOTS_PER_CLASS)*8 +: 8]=
                occupied_o[(j/SLOTS_PER_CLASS)*8 +: 8]+1'b1;
    end
    wire commit=stage_pending && shape_ok && free_slot>=0 && qcount<SLOTS;
    wire remove=waiting && (packet_accepted_i || packet_duplicate_i || packet_rejected_i);
    wire [SW-1:0] head_slot=order[qread];
    wire select_dllp=output_active ? output_dllp : dllp_pending;
    wire tlp_available=qcount!=0 && !waiting && initialized_i;
    // The frozen consumer's ready depends on frame kind, not valid. Qualifying
    // only the first TLP beat avoids blocking incoming DLLPs behind a TLP that
    // cannot start. Once a beat transfers the entire frame is locked/stable.
    assign out_dllp_o=select_dllp;
    assign out_valid_o=rst_ni && link_up_i &&
        (output_active || (!training_i && (select_dllp ? dllp_pending : tlp_available && out_ready_i)));
    assign out_data_o=select_dllp ? dllp[output_index] : packets[head_slot*CAP+output_index];
    assign out_sop_o=output_index==0;
    assign out_eop_o=select_dllp ? output_index+1'b1==dllp_length :
                                  output_index+1'b1==lengths[head_slot];
    assign out_error_o=select_dllp ? dllp_bad : errors[head_slot];
    assign queued_o=qcount;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            used<=0;qread<=0;qwrite<=0;qcount<=0;
            input_active<=0;input_dllp<=0;input_bad<=0;input_count<=0;
            stage_pending<=0;stage_length<=0;stage_bad<=0;
            dllp_pending<=0;dllp_bad<=0;dllp_length<=0;
            output_active<=0;output_dllp<=0;output_index<=0;waiting<=0;
            header_limit_o<={COMPLETER_ONLY ? 8'b0 : H_INIT,H_INIT,H_INIT};
            data_limit_o<={COMPLETER_ONLY ? 12'b0 : D_INIT,D_INIT,D_INIT};
            released_o<=0;released_class_o<=0;released_data_o<=0;
            dropped_o<=0;protocol_error_o<=0;recovery_request_o<=0;
        end else if(!link_up_i) begin
            used<=0;qread<=0;qwrite<=0;qcount<=0;input_active<=0;input_count<=0;
            stage_pending<=0;dllp_pending<=0;output_active<=0;output_index<=0;waiting<=0;
            header_limit_o<={COMPLETER_ONLY ? 8'b0 : H_INIT,H_INIT,H_INIT};
            data_limit_o<={COMPLETER_ONLY ? 12'b0 : D_INIT,D_INIT,D_INIT};
            released_o<=0;dropped_o<=0;protocol_error_o<=0;recovery_request_o<=0;
        end else begin
            released_o<=0;dropped_o<=0;
            if(stage_pending && !shape_ok) begin
                stage_pending<=0;dropped_o<=1;protocol_error_o<=1;recovery_request_o<=1;
            end
            if(commit) begin
                for(k=0;k<CAP;k=k+1) packets[free_slot*CAP+k]<=staging[k];
                lengths[free_slot]<=stage_length;units[free_slot]<=(payload_dw+3)/4;
                errors[free_slot]<=stage_bad;used[free_slot]<=1;
                order[qwrite]<=free_slot;qwrite<=qwrite==SLOTS-1 ? 0 : qwrite+1'b1;
                stage_pending<=0;
            end
            if(remove) begin
                used[head_slot]<=0;waiting<=0;qread<=qread==SLOTS-1 ? 0 : qread+1'b1;
                if(packet_accepted_i) begin
                    released_o<=1;released_class_o<=head_slot/SLOTS_PER_CLASS;
                    released_data_o<=units[head_slot];
                    header_limit_o[(head_slot/SLOTS_PER_CLASS)*8 +: 8]<=
                        header_limit_o[(head_slot/SLOTS_PER_CLASS)*8 +: 8]+1'b1;
                    data_limit_o[(head_slot/SLOTS_PER_CLASS)*12 +: 12]<=
                        data_limit_o[(head_slot/SLOTS_PER_CLASS)*12 +: 12]+units[head_slot];
                end
            end
            case({commit,remove})
                2'b10:qcount<=qcount+1'b1;
                2'b01:qcount<=qcount-1'b1;
                default:qcount<=qcount;
            endcase
            if(rx_valid_i && rx_ready_o) begin
                if(!input_active) begin
                    input_dllp<=rx_dllp_i;input_bad<=rx_error_i || !rx_sop_i;
                    input_count<=1;input_active<=!rx_eop_i;
                    if(rx_dllp_i) dllp[0]<=rx_data_i; else staging[0]<=rx_data_i;
                    if(rx_eop_i) begin
                        if(rx_dllp_i) begin dllp_pending<=1;dllp_length<=1;dllp_bad<=1;end
                        else begin stage_pending<=1;stage_length<=1;stage_bad<=1;end
                    end
                end else begin
                    input_bad<=input_bad || rx_error_i || rx_sop_i || rx_dllp_i!=input_dllp;
                    if(input_dllp) begin
                        if(input_count<6) dllp[input_count]<=rx_data_i;
                    end else if(input_count<CAP) staging[input_count]<=rx_data_i;
                    if(input_count<CAP+1) input_count<=input_count+1'b1;
                    if(rx_eop_i) begin
                        input_active<=0;
                        if(input_dllp) begin
                            dllp_pending<=1;dllp_length<=input_count>=6 ? 6 : input_count+1'b1;
                            dllp_bad<=input_bad || rx_error_i || rx_sop_i || !rx_dllp_i || input_count!=5;
                        end else begin
                            stage_pending<=1;stage_length<=input_count+1'b1;
                            stage_bad<=input_bad || rx_error_i || rx_sop_i || rx_dllp_i;
                        end
                    end
                end
            end
            if(out_valid_o && out_ready_i) begin
                if(out_eop_o) begin
                    output_active<=0;output_index<=0;
                    if(select_dllp) dllp_pending<=0; else waiting<=1;
                end else begin
                    output_active<=1;output_dllp<=select_dllp;output_index<=output_index+1'b1;
                end
            end
        end
    end
endmodule
`default_nettype wire
