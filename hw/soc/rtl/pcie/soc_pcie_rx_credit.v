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
    // Each slot keeps the index of its last byte (length minus one), set from
    // the staged length at commit, so the frame end needs no decrement.
    reg [CW-1:0] lasts[0:SLOTS-1];
    reg [11:0] units[0:SLOTS-1];
    reg errors[0:SLOTS-1];
    reg [SW-1:0] order[0:SLOTS-1];
    reg [SLOTS-1:0] used;
    reg [SW-1:0] qread,qwrite,qcount;
    reg input_active,input_dllp,input_bad,stage_pending,dllp_pending,dllp_bad;
    reg [CW-1:0] input_count,stage_length,stage_last;
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
    // The staged TLP is checked in one cycle and committed in the next. The
    // shape verdict, the chosen free slot and the credit units are taken
    // from registers, so the header decode, length arithmetic and free-slot
    // search no longer drive the write enables of every queue byte. The
    // staging bytes cannot change while a TLP is staged, and between the
    // check and the commit only a removal can change ownership, which frees
    // slots and never takes the chosen one, and lowers the queue count.
    // The commit itself is a register per slot, set by the check cycle,
    // so each slot's byte write enable is a flop output.
    reg stage_checked,stage_shape_ok;
    reg [SW-1:0] stage_slot;
    reg [11:0] stage_units;
    reg [SLOTS-1:0] commit_slot;
    wire commit=|commit_slot;
    wire stage_drop=stage_pending && stage_checked && !stage_shape_ok;
    integer b;
    wire remove=waiting && (packet_accepted_i || packet_duplicate_i || packet_rejected_i);
    // The queue head slot is a register that tracks order[qread] from the
    // next-state values of qread and of the order entry a commit writes.
    // It may differ only while the queue is empty, when no TLP is read.
    reg [SW-1:0] head_slot;
    wire [SW-1:0] qread_plus=qread==SLOTS-1 ? 0 : qread+1'b1;
    wire [SW-1:0] next_qread=remove ? qread_plus : qread;
    // The head slot's last read index, class and credit units are kept in
    // registers from the same next-state head and the commit's writes, so
    // the frame end and the credit release start at registers. Both
    // possible next heads (queue position kept or advanced by a removal)
    // are resolved from registers; the removal only selects one.
    reg [CW-1:0] head_last;
    reg [1:0] head_class;
    reg [11:0] head_units;
    reg [SLOTS-1:0] head_onehot;
    wire [SW-1:0] stay_slot=(commit && qwrite==qread) ? stage_slot : order[qread];
    wire [SW-1:0] advance_slot=(commit && qwrite==qread_plus) ? stage_slot : order[qread_plus];
    wire [CW-1:0] stay_last=commit_slot[stay_slot] ? stage_last : lasts[stay_slot];
    wire [CW-1:0] advance_last=commit_slot[advance_slot] ? stage_last : lasts[advance_slot];
    // Data credit released by the next acceptance: the low half of
    // data_limit+units for the head's class is registered a cycle ahead and
    // the high half finished at the removal. A removal never follows a
    // removal, and while a verdict is awaited the head (its class and units)
    // is fixed, so the registered half is the current one at any removal.
    reg [6:0] release_lo;
    wire [11:0] head_data_limit=data_limit_o[head_class*12 +: 12];
    wire [11:0] released_limit={head_data_limit[11:6]+head_units[11:6]+release_lo[6],release_lo[5:0]};
    wire [11:0] stay_units=commit_slot[stay_slot] ? stage_units : units[stay_slot];
    wire [11:0] advance_units=commit_slot[advance_slot] ? stage_units : units[advance_slot];
    wire [SW-1:0] next_head_slot=remove ? advance_slot : stay_slot;
    wire [CW-1:0] next_head_last=remove ? advance_last : stay_last;
    wire [11:0] next_head_units=remove ? advance_units : stay_units;
    wire select_dllp=output_active ? output_dllp : dllp_pending;
    wire tlp_available=qcount!=0 && !waiting && initialized_i;
    // The frozen consumer's ready depends on frame kind, not valid. Qualifying
    // only the first TLP beat avoids blocking incoming DLLPs behind a TLP that
    // cannot start. Once a beat transfers the entire frame is locked/stable.
    assign out_dllp_o=select_dllp;
    assign out_valid_o=rst_ni && link_up_i &&
        (output_active || (!training_i && (select_dllp ? dllp_pending : tlp_available && out_ready_i)));
    // Read each constant-base bank in parallel. The queue-head decode selects
    // an already-read byte instead of driving a multiply/add and a flat mux.
    // Keep the flat array bounds (including reads across a bank boundary) so
    // this is cycle-exact even outside the valid output-index range.
    // A one-hot read cursor (equal to output_index, updated at the same
    // points) selects each bank's byte as an AND-OR. That byte is registered
    // per bank: bank_byte[b] holds packets[b*CAP+output_index] for the index
    // of the current cycle. It is loaded with the byte at the next index
    // (index+1 on a mid-frame handshake, 0 at an end of frame, link loss or
    // reset, otherwise held), and with staging[0] when the bank is committed.
    // A committed bank cannot be read mid-frame (it was free), and it is
    // first read at index 0, so every byte that leaves equals the array's.
    // The output then needs only the one-hot head select of six registers.
    // Cross-bank addresses of the flat array are included; addresses past
    // its end read as zero.
    localparam integer READ_CHOICES=1<<CW;
    reg [READ_CHOICES-1:0] read_onehot;
    wire [READ_CHOICES-1:0] next_onehot={read_onehot[READ_CHOICES-2:0],read_onehot[READ_CHOICES-1]};
    wire [7:0] bank_byte [0:SLOTS-1];
    wire handshake=out_valid_o && out_ready_i;
    wire restart=!rst_ni || !link_up_i || (handshake && out_eop_o);
    genvar bank,read_bit,read_offset;
    generate for(bank=0;bank<SLOTS;bank=bank+1) begin: read_bank
        wire [7:0] following;
        reg [7:0] registered;
        for(read_bit=0;read_bit<8;read_bit=read_bit+1) begin: read_bit_lane
            wire [READ_CHOICES-1:0] selected;
            for(read_offset=0;read_offset<READ_CHOICES;read_offset=read_offset+1) begin: read_byte
                if(bank*CAP+read_offset<SLOTS*CAP) begin: present
                    assign selected[read_offset]=next_onehot[read_offset] & packets[bank*CAP+read_offset][read_bit];
                end else begin: absent
                    assign selected[read_offset]=1'b0;
                end
            end
            assign following[read_bit]=|selected;
        end
        always @(posedge clk_i)
            registered<=commit_slot[bank] ? staging[0] :
                restart ? packets[bank*CAP] : handshake ? following : registered;
        assign bank_byte[bank]=registered;
    end endgenerate
    reg [7:0] tlp_byte;
    integer h;
    always @* begin
        tlp_byte=0;
        for(h=0;h<SLOTS;h=h+1) if(head_onehot[h]) tlp_byte=tlp_byte|bank_byte[h];
    end
    assign out_data_o=select_dllp ? dllp[output_index] : tlp_byte;
    assign out_sop_o=output_index==0;
    assign out_eop_o=select_dllp ? output_index+1'b1==dllp_length : output_index==head_last;
    assign out_error_o=select_dllp ? dllp_bad : errors[head_slot];
    assign queued_o=qcount;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            used<=0;qread<=0;qwrite<=0;qcount<=0;head_slot<=0;
            head_last<=0;head_class<=0;head_units<=0;head_onehot<=1;read_onehot<=1;
            input_active<=0;input_dllp<=0;input_bad<=0;input_count<=0;
            stage_pending<=0;stage_length<=0;stage_last<=0;stage_bad<=0;release_lo<=0;
            stage_checked<=0;stage_shape_ok<=0;stage_slot<=0;stage_units<=0;commit_slot<=0;
            dllp_pending<=0;dllp_bad<=0;dllp_length<=0;
            output_active<=0;output_dllp<=0;output_index<=0;waiting<=0;
            header_limit_o<={COMPLETER_ONLY ? 8'b0 : H_INIT,H_INIT,H_INIT};
            data_limit_o<={COMPLETER_ONLY ? 12'b0 : D_INIT,D_INIT,D_INIT};
            released_o<=0;released_class_o<=0;released_data_o<=0;
            dropped_o<=0;protocol_error_o<=0;recovery_request_o<=0;
        end else if(!link_up_i) begin
            used<=0;qread<=0;qwrite<=0;qcount<=0;head_slot<=0;input_active<=0;input_count<=0;
            head_last<=0;head_class<=0;head_units<=0;head_onehot<=1;read_onehot<=1;
            stage_pending<=0;dllp_pending<=0;output_active<=0;output_index<=0;waiting<=0;
            stage_checked<=0;commit_slot<=0;
            header_limit_o<={COMPLETER_ONLY ? 8'b0 : H_INIT,H_INIT,H_INIT};
            data_limit_o<={COMPLETER_ONLY ? 12'b0 : D_INIT,D_INIT,D_INIT};
            released_o<=0;dropped_o<=0;protocol_error_o<=0;recovery_request_o<=0;
        end else begin
            released_o<=0;dropped_o<=0;head_slot<=next_head_slot;
            head_last<=next_head_last;head_class<=next_head_slot/SLOTS_PER_CLASS;head_units<=next_head_units;
            release_lo<={1'b0,head_data_limit[5:0]}+{1'b0,head_units[5:0]};
            head_onehot<={{(SLOTS-1){1'b0}},1'b1}<<next_head_slot;
            stage_checked<=stage_pending && !commit && !stage_drop;
            stage_shape_ok<=shape_ok;
            stage_slot<=free_slot;stage_units<=(payload_dw+3)/4;
            for(b=0;b<SLOTS;b=b+1)
                commit_slot[b]<=stage_pending && !commit && !stage_drop && shape_ok &&
                    free_slot==b && qcount<SLOTS;
            if(stage_drop) begin
                stage_pending<=0;dropped_o<=1;protocol_error_o<=1;recovery_request_o<=1;
            end
            if(commit) begin
                for(b=0;b<SLOTS;b=b+1) if(commit_slot[b]) begin
                    for(k=0;k<CAP;k=k+1) packets[b*CAP+k]<=staging[k];
                    lasts[b]<=stage_last;units[b]<=stage_units;
                    errors[b]<=stage_bad;used[b]<=1;
                end
                order[qwrite]<=stage_slot;qwrite<=qwrite==SLOTS-1 ? 0 : qwrite+1'b1;
                stage_pending<=0;
            end
            if(remove) begin
                used[head_slot]<=0;waiting<=0;qread<=qread==SLOTS-1 ? 0 : qread+1'b1;
                if(packet_accepted_i) begin
                    released_o<=1;released_class_o<=head_class;
                    released_data_o<=head_units;
                    header_limit_o[head_class*8 +: 8]<=header_limit_o[head_class*8 +: 8]+1'b1;
                    data_limit_o[head_class*12 +: 12]<=released_limit;
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
                        else begin stage_pending<=1;stage_length<=1;stage_last<=0;stage_bad<=1;end
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
                            stage_pending<=1;stage_length<=input_count+1'b1;stage_last<=input_count;
                            stage_bad<=input_bad || rx_error_i || rx_sop_i || rx_dllp_i;
                        end
                    end
                end
            end
            if(out_valid_o && out_ready_i) begin
                if(out_eop_o) begin
                    output_active<=0;output_index<=0;read_onehot<=1;
                    if(select_dllp) dllp_pending<=0; else waiting<=1;
                end else begin
                    output_active<=1;output_dllp<=select_dllp;output_index<=output_index+1'b1;
                    read_onehot<={read_onehot[READ_CHOICES-2:0],read_onehot[READ_CHOICES-1]};
                end
            end
        end
    end
endmodule
`default_nettype wire
