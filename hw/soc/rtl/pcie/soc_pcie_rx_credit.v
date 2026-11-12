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
    // Both candidates are formed without a slot-indexed lookup of the
    // commit. A commit never coincides with a full queue, so a commit
    // writes the read position only into an empty queue, and the position
    // after it only when one TLP is queued. Without a removal the head
    // stays (its registers already hold it) unless an empty queue takes the
    // staged TLP. With a removal the next head is the staged TLP if one TLP
    // was queued (the queue is empty otherwise, and the head is then
    // unused), and else the next queued slot, which is occupied and so not
    // the one being committed.
    wire queue_empty=qcount==0;
    wire queue_one=qcount==1;
    wire stay_staged=commit && queue_empty;
    wire [SW-1:0] second_slot=order[qread_plus];
    wire [SW-1:0] stay_slot=stay_staged ? stage_slot : head_slot;
    wire [SW-1:0] advance_slot=queue_one ? stage_slot : second_slot;
    wire [CW-1:0] stay_last=stay_staged ? stage_last : head_last;
    wire [CW-1:0] advance_last=queue_one ? stage_last : lasts[second_slot];
    // Data credit released by the next acceptance: the low half of
    // data_limit+units for the head's class is registered a cycle ahead and
    // the high half finished at the removal. A removal never follows a
    // removal, and while a verdict is awaited the head (its class and units)
    // is fixed, so the registered half is the current one at any removal.
    // The high half is registered the same way, for both carries in, so the
    // removal only selects between registers.
    reg [6:0] release_lo;
    reg [5:0] release_hi,release_hi_carry;
    wire [11:0] head_data_limit=data_limit_o[head_class*12 +: 12];
    wire [11:0] released_limit={release_lo[6] ? release_hi_carry : release_hi,release_lo[5:0]};
    wire [11:0] stay_units=stay_staged ? stage_units : head_units;
    wire [11:0] advance_units=queue_one ? stage_units : units[second_slot];
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
    // its end read as zero. (A copy of the cursor per bank was measured in
    // the eighth round and placed worse at 70% target density.)
    localparam integer READ_CHOICES=1<<CW;
    reg [READ_CHOICES-1:0] read_onehot;
    wire [READ_CHOICES-1:0] next_onehot={read_onehot[READ_CHOICES-2:0],read_onehot[READ_CHOICES-1]};
    wire [7:0] bank_byte [0:SLOTS-1];
    wire handshake=out_valid_o && out_ready_i;
    // A bank's register is reloaded with byte 0 at an end of frame (a
    // DLLP's included, which also moves the cursor). Reset and link loss
    // need no reload: every bank is free afterwards, and its next commit
    // loads it.
    wire restart=handshake && out_eop_o;
`ifdef SOC_PCIE_RX_READ_AHEAD
`ifdef SOC_PCIE_RX_STAGED_COMMIT
    // The read-ahead registers below are loaded from a committed bank's
    // staging bytes in the commit cycle; the staged commit writes the bank
    // later, so the two knobs cannot be combined.
    soc_pcie_rx_read_ahead_excludes_staged_commit unsupported_knob_combination();
`endif
    // docs/combined-timing.md section 12 (SOC_PCIE_RX_READ_AHEAD). The read
    // mux of each bank is split in two levels with a register between them.
    // The bank's bytes are taken in groups of LANES (byte g*LANES+l is lane
    // l of group g), and each group keeps a read-ahead register,
    //     ahead[g] = packets[bank*CAP + g*LANES + (output_index+1)%LANES],
    // so the byte the bank register loads at a mid-frame handshake,
    // packets[bank*CAP+output_index+1], is ahead[(output_index+1)/LANES]:
    // an AND-OR of AHEAD_GROUPS registers selected by a one-hot register.
    // ahead[g] itself is an AND-OR of the LANES bytes of its group, selected
    // by the lane after that, (output_index+2)%LANES, at a mid-frame
    // handshake; with lane 1 at an end of frame (the cursor returns to 0);
    // and is held otherwise, because the bank's bytes and the cursor do not
    // change. A commit rewrites the whole bank from staging in that cycle,
    // so a committed bank's ahead registers load the same selection from
    // staging (one shared selection, the bank's commit register picks it).
    // Reset and link loss do not reload them: every bank is free afterwards
    // and its next commit loads them before any of its bytes is read.
    // Only the bank's own CAP bytes are read. The flat array's reads across
    // a bank boundary (index+1 >= CAP) are never loaded: the cursor passes
    // a TLP's last index (at most CAP-1, the shape check) or a DLLP's (at
    // most 5) only at an end of frame, which reloads byte 0. So every byte
    // that leaves equals the default build's (random co-simulation against
    // it, hw/soc/tb/tb_pcie_rx_credit_read_ahead.v).
    localparam integer LANES=8;
    localparam integer AHEAD_GROUPS=(CAP+LANES-1)/LANES;
    // One-hot (output_index+1)%LANES and (output_index+1)/LANES.
    reg [LANES-1:0] ahead_lane;
    reg [AHEAD_GROUPS-1:0] ahead_group;
    wire [LANES-1:0] ahead_lane_next={ahead_lane[LANES-2:0],ahead_lane[LANES-1]};
    wire [AHEAD_GROUPS-1:0] ahead_group_next=ahead_lane_next[0] ?
        {ahead_group[AHEAD_GROUPS-2:0],ahead_group[AHEAD_GROUPS-1]} : ahead_group;
    wire advance=handshake && !out_eop_o;
    wire [8*AHEAD_GROUPS-1:0] staged_ahead;
    genvar ahead_index,ahead_bit,ahead_offset;
    generate for(ahead_index=0;ahead_index<AHEAD_GROUPS;ahead_index=ahead_index+1) begin: staged_group
        wire [7:0] at_next,at_same,at_first;
        for(ahead_bit=0;ahead_bit<8;ahead_bit=ahead_bit+1) begin: staged_bit
            wire [LANES-1:0] next_pick,same_pick;
            for(ahead_offset=0;ahead_offset<LANES;ahead_offset=ahead_offset+1) begin: staged_lane
                if(ahead_index*LANES+ahead_offset<CAP) begin: present
                    assign next_pick[ahead_offset]=ahead_lane_next[ahead_offset] &
                        staging[ahead_index*LANES+ahead_offset][ahead_bit];
                    assign same_pick[ahead_offset]=ahead_lane[ahead_offset] &
                        staging[ahead_index*LANES+ahead_offset][ahead_bit];
                end else begin: absent
                    assign next_pick[ahead_offset]=1'b0;
                    assign same_pick[ahead_offset]=1'b0;
                end
            end
            assign at_next[ahead_bit]=|next_pick;
            assign at_same[ahead_bit]=|same_pick;
        end
        if(ahead_index*LANES+1<CAP) begin: first_present
            assign at_first=staging[ahead_index*LANES+1];
        end else begin: first_absent
            assign at_first=8'b0;
        end
        assign staged_ahead[ahead_index*8 +: 8]=advance ? at_next : restart ? at_first : at_same;
    end endgenerate
`endif
`ifdef SOC_PCIE_RX_READ2
`ifdef SOC_PCIE_RX_READ_AHEAD
    soc_pcie_rx_read2_excludes_read_ahead unsupported_knob_combination_read2();
`endif
`ifdef SOC_PCIE_RX_STAGED_COMMIT
    // Stage 1 below is loaded from a committed bank's staging bytes in the
    // commit cycle; the staged commit writes the bank later.
    soc_pcie_rx_read2_excludes_staged_commit unsupported_knob_combination_read2();
`endif
    // docs/combined-timing.md section 14 (SOC_PCIE_RX_READ2). The bank read
    // is a two-stage registered multiplexer without a handshake in stage 1.
    // A bank's CAP bytes are taken in R2_GROUPS groups of R2_LANES (byte
    // g*R2_LANES+l is lane l of group g). The cursor c (output_index) moves
    // by at most one per cycle, so the byte a bank register can load at the
    // end of the next cycle is at c+1 (no handshake now), c+2 (a mid-frame
    // handshake now) or 1 (an end of frame, link loss or reset now: c
    // becomes 0). Stage 1 therefore loads, every cycle and per group, the
    // lane of c+1 ("near") and the lane of c+2 ("far"), each an AND-OR of
    // R2_LANES bytes selected by a rotation of a registered one-hot lane
    // (c mod R2_LANES); no enable. Stage 2 is the bank register's next
    // byte: an AND-OR of the 2*R2_GROUPS stage-1 registers and byte 1,
    // selected by one-hot pick registers set from this cycle's handshake:
    //   no handshake       near of the group of c+1,
    //   mid-frame          far of the group of c+2,
    //   end of frame/reset byte 1 (read directly, a fixed byte).
    // So in the next cycle the stage-2 value is packets[bank*CAP+c'+1] for
    // the cursor c' of that cycle, the byte the default build's 64-input
    // AND-OR selects. A commit rewrites the bank from staging at the end of
    // its cycle; a committed bank's stage-1 registers load the same lanes
    // from staging in that cycle (one shared selection, picked by the
    // bank's commit register), so stage 1 always matches the bank's
    // contents of the cycle it is read in. Byte 1 is read from the bank
    // itself. Only the bank's own CAP bytes are read: a mid-frame handshake
    // happens only below a frame's last index (at most CAP-1, the shape
    // check; at most 5 for a DLLP), so c+1 <= CAP-1 whenever the stage-2
    // byte is loaded, and the cross-bank reads of the flat array are never
    // loaded (as for SOC_PCIE_RX_READ_AHEAD). Every bank register therefore
    // equals the default build's in every cycle, and the module's ports
    // are cycle-identical (random co-simulation against the default build,
    // hw/soc/tb/tb_pcie_rx_credit_read_ahead.v). The handshake reaches only
    // the 2*R2_GROUPS+1 pick registers, the cursor registers and the bank
    // registers' multiplexer, as before. Cost: SLOTS*R2_GROUPS*16 stage-1
    // flip-flops (288 at the SoC's 8 DW and 2 slots per class) and
    // R2_LANES+R2_GROUPS*3+1 cursor and pick flip-flops.
    localparam integer R2_GROUPS=3;
    localparam integer R2_LANES=(CAP+R2_GROUPS-1)/R2_GROUPS;
    reg [R2_LANES-1:0] r2_lane;
    reg [R2_GROUPS-1:0] r2_group,r2_pick_near,r2_pick_far;
    reg r2_pick_first;
    // One-hot lanes of c+1 and c+2, and the groups of c+1 and c+2.
    wire [R2_LANES-1:0] r2_lane_near={r2_lane[R2_LANES-2:0],r2_lane[R2_LANES-1]};
    wire [R2_LANES-1:0] r2_lane_far={r2_lane[R2_LANES-3:0],r2_lane[R2_LANES-1:R2_LANES-2]};
    wire [R2_GROUPS-1:0] r2_group_next={r2_group[R2_GROUPS-2:0],r2_group[R2_GROUPS-1]};
    wire [R2_GROUPS-1:0] r2_group_near=r2_lane[R2_LANES-1] ? r2_group_next : r2_group;
    wire [R2_GROUPS-1:0] r2_group_far=(r2_lane[R2_LANES-1] | r2_lane[R2_LANES-2]) ? r2_group_next : r2_group;
    wire r2_rst_n=rst_ni;
    // Cursor and pick registers, updated at the same points as read_onehot.
    always @(posedge clk_i or negedge r2_rst_n) begin
        if(!r2_rst_n) begin
            r2_lane<=1;r2_group<=1;r2_pick_near<=0;r2_pick_far<=0;r2_pick_first<=1;
        end else if(!link_up_i) begin
            r2_lane<=1;r2_group<=1;r2_pick_near<=0;r2_pick_far<=0;r2_pick_first<=1;
        end else if(handshake) begin
            if(out_eop_o) begin
                r2_lane<=1;r2_group<=1;r2_pick_near<=0;r2_pick_far<=0;r2_pick_first<=1;
            end else begin
                r2_lane<=r2_lane_near;
                if(r2_lane[R2_LANES-1]) r2_group<=r2_group_next;
                r2_pick_near<=0;r2_pick_far<=r2_group_far;r2_pick_first<=0;
            end
        end else begin
            r2_pick_near<=r2_group_near;r2_pick_far<=0;r2_pick_first<=0;
        end
    end
    // The staged TLP's stage-1 selection, shared by every bank; a bank's
    // commit register picks it in the commit cycle.
    wire [8*R2_GROUPS-1:0] r2_staged_near,r2_staged_far;
    genvar r2_index,r2_bit,r2_offset;
    generate for(r2_index=0;r2_index<R2_GROUPS;r2_index=r2_index+1) begin: r2_staged_group
        for(r2_bit=0;r2_bit<8;r2_bit=r2_bit+1) begin: r2_staged_bit
            wire [R2_LANES-1:0] near_pick,far_pick;
            for(r2_offset=0;r2_offset<R2_LANES;r2_offset=r2_offset+1) begin: r2_staged_lane
                if(r2_index*R2_LANES+r2_offset<CAP) begin: present
                    assign near_pick[r2_offset]=r2_lane_near[r2_offset] &
                        staging[r2_index*R2_LANES+r2_offset][r2_bit];
                    assign far_pick[r2_offset]=r2_lane_far[r2_offset] &
                        staging[r2_index*R2_LANES+r2_offset][r2_bit];
                end else begin: absent
                    assign near_pick[r2_offset]=1'b0;
                    assign far_pick[r2_offset]=1'b0;
                end
            end
            assign r2_staged_near[r2_index*8+r2_bit]=|near_pick;
            assign r2_staged_far[r2_index*8+r2_bit]=|far_pick;
        end
    end endgenerate
`endif
    genvar bank,read_bit,read_offset;
    generate for(bank=0;bank<SLOTS;bank=bank+1) begin: read_bank
        wire [7:0] following;
        reg [7:0] registered;
`ifdef SOC_PCIE_RX_READ2
        // Stage 1: per group, the lanes of c+1 (near) and c+2 (far) of this
        // bank, or of the staged TLP when this bank is committed.
        wire [8*R2_GROUPS-1:0] near_bytes,far_bytes;
        for(read_offset=0;read_offset<R2_GROUPS;read_offset=read_offset+1) begin: r2_slot
            wire [7:0] near_d,far_d;
            reg [7:0] near_q,far_q;
            for(read_bit=0;read_bit<8;read_bit=read_bit+1) begin: r2_bit_lane
                wire [R2_LANES-1:0] near_pick,far_pick;
                for(r2_offset=0;r2_offset<R2_LANES;r2_offset=r2_offset+1) begin: r2_byte
                    if(read_offset*R2_LANES+r2_offset<CAP) begin: present
                        assign near_pick[r2_offset]=r2_lane_near[r2_offset] &
                            packets[bank*CAP+read_offset*R2_LANES+r2_offset][read_bit];
                        assign far_pick[r2_offset]=r2_lane_far[r2_offset] &
                            packets[bank*CAP+read_offset*R2_LANES+r2_offset][read_bit];
                    end else begin: absent
                        assign near_pick[r2_offset]=1'b0;
                        assign far_pick[r2_offset]=1'b0;
                    end
                end
                assign near_d[read_bit]=|near_pick;
                assign far_d[read_bit]=|far_pick;
            end
            always @(posedge clk_i) begin
                near_q<=commit_slot[bank] ? r2_staged_near[read_offset*8 +: 8] : near_d;
                far_q<=commit_slot[bank] ? r2_staged_far[read_offset*8 +: 8] : far_d;
            end
            assign near_bytes[read_offset*8 +: 8]=near_q;
            assign far_bytes[read_offset*8 +: 8]=far_q;
        end
        // Stage 2: the byte at the next index, from registers only.
        for(read_bit=0;read_bit<8;read_bit=read_bit+1) begin: read_bit_lane
            wire [R2_GROUPS-1:0] near_selected,far_selected;
            for(read_offset=0;read_offset<R2_GROUPS;read_offset=read_offset+1) begin: read_byte
                assign near_selected[read_offset]=r2_pick_near[read_offset] & near_bytes[read_offset*8+read_bit];
                assign far_selected[read_offset]=r2_pick_far[read_offset] & far_bytes[read_offset*8+read_bit];
            end
            assign following[read_bit]=(|near_selected) | (|far_selected) |
                (r2_pick_first & packets[bank*CAP+1][read_bit]);
        end
`elsif SOC_PCIE_RX_READ_AHEAD
        wire [8*AHEAD_GROUPS-1:0] ahead_bytes;
        for(read_offset=0;read_offset<AHEAD_GROUPS;read_offset=read_offset+1) begin: ahead_slot
            wire [7:0] stored_next,stored_first;
            reg [7:0] ahead;
            for(read_bit=0;read_bit<8;read_bit=read_bit+1) begin: ahead_bit_lane
                wire [LANES-1:0] pick;
                for(ahead_offset=0;ahead_offset<LANES;ahead_offset=ahead_offset+1) begin: ahead_byte
                    if(read_offset*LANES+ahead_offset<CAP) begin: present
                        assign pick[ahead_offset]=ahead_lane_next[ahead_offset] &
                            packets[bank*CAP+read_offset*LANES+ahead_offset][read_bit];
                    end else begin: absent
                        assign pick[ahead_offset]=1'b0;
                    end
                end
                assign stored_next[read_bit]=|pick;
            end
            if(read_offset*LANES+1<CAP) begin: first_present
                assign stored_first=packets[bank*CAP+read_offset*LANES+1];
            end else begin: first_absent
                assign stored_first=8'b0;
            end
            always @(posedge clk_i)
                ahead<=commit_slot[bank] ? staged_ahead[read_offset*8 +: 8] :
                    advance ? stored_next : restart ? stored_first : ahead;
            assign ahead_bytes[read_offset*8 +: 8]=ahead;
        end
        for(read_bit=0;read_bit<8;read_bit=read_bit+1) begin: read_bit_lane
            wire [AHEAD_GROUPS-1:0] selected;
            for(read_offset=0;read_offset<AHEAD_GROUPS;read_offset=read_offset+1) begin: read_byte
                assign selected[read_offset]=ahead_group[read_offset] & ahead_bytes[read_offset*8+read_bit];
            end
            assign following[read_bit]=|selected;
        end
`else
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
`endif
        always @(posedge clk_i)
            registered<=commit_slot[bank] ? staging[0] :
                restart ? packets[bank*CAP] : handshake ? following : registered;
        assign bank_byte[bank]=registered;
    end endgenerate
    // Queue and staging storage. A commit copies the staged TLP into its
    // slot's bank; its write enable is the slot's commit register alone
    // (cleared by reset and link loss), not the link and reset state. The
    // only difference from writing inside the reset/link block is a commit
    // register still set in the first cycle of a link loss: that bank is
    // free afterwards and is rewritten whole by its next commit before it
    // is read, so no byte that leaves differs.
    // Staging bytes are written one cycle after they are accepted, from a
    // registered one-hot byte select and a registered byte. A staged TLP is
    // committed two cycles after its last byte at the earliest, and its
    // header bytes (needed by the check one cycle after the last byte) are
    // at least twelve bytes earlier, so every read sees the same bytes.
    reg [CAP-1:0] stage_write_at;
    reg [7:0] stage_write_data;
    integer w,wb;
`ifdef SOC_PCIE_RX_STAGED_COMMIT
    // docs/combined-timing.md: the copy into the bank is spread over
    // consecutive cycles in groups of eight bytes, group g written g cycles
    // after the commit by its own register (a shift of commit_slot[bank]),
    // so no enable drives more than 64 flip-flops.
    // Byte w is first read w cycles after the commit (one byte per output
    // handshake from index 0; byte 0 by the commit itself and at an end of
    // frame), and group g = w/8 is written at the end of commit cycle +g,
    // before any read of it. Its staging bytes are unchanged until then:
    // a new TLP's byte w is written at the end of cycle commit+2+w at the
    // earliest. A bank is reused only after its TLP has been read out and
    // removed, many cycles after its last group. Reset and link loss clear
    // the shift with commit_slot; the bank is free afterwards and its next
    // commit rewrites it whole.
    // Group g (1..GROUPS-1) of bank b is enabled by
    // commit_later[(g-1)*SLOTS+b]. CAP > 8 for every supported size.
    localparam integer GROUPS=(CAP+7)/8;
    reg [(GROUPS-1)*SLOTS-1:0] commit_later;
    wire [GROUPS*SLOTS-1:0] commit_shift={commit_later,commit_slot};
    always @(posedge clk_i or negedge rst_ni)
        if(!rst_ni) commit_later<=0;
        else if(!link_up_i) commit_later<=0;
        else commit_later<=commit_shift[(GROUPS-1)*SLOTS-1:0];
    integer cw;
    always @(posedge clk_i) begin
        stage_write_data<=rx_data_i;
        for(w=0;w<CAP;w=w+1) if(stage_write_at[w]) staging[w]<=stage_write_data;
        for(wb=0;wb<SLOTS;wb=wb+1)
            for(cw=0;cw<GROUPS;cw=cw+1)
                if(commit_shift[cw*SLOTS+wb])
                    for(w=8*cw;w<8*cw+8 && w<CAP;w=w+1) packets[wb*CAP+w]<=staging[w];
    end
`else
    always @(posedge clk_i) begin
        stage_write_data<=rx_data_i;
        for(w=0;w<CAP;w=w+1) if(stage_write_at[w]) staging[w]<=stage_write_data;
        for(wb=0;wb<SLOTS;wb=wb+1) if(commit_slot[wb])
            for(w=0;w<CAP;w=w+1) packets[wb*CAP+w]<=staging[w];
    end
`endif
`ifdef SOC_PCIE_RX_STAGED_COMMIT
    // The queue write position is also kept one-hot (qwrite_oh has its bit
    // at qwrite), so each order entry's write enable is the commit and one
    // register bit instead of a decode of qwrite.
    reg [SLOTS-1:0] qwrite_oh;
    integer qo;
`endif
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
`ifdef SOC_PCIE_RX_STAGED_COMMIT
            qwrite_oh<=1;
`endif
            head_last<=0;head_class<=0;head_units<=0;head_onehot<=1;read_onehot<=1;
`ifdef SOC_PCIE_RX_READ_AHEAD
            ahead_lane<=2;ahead_group<=1;
`endif
            input_active<=0;input_dllp<=0;input_bad<=0;input_count<=0;
            stage_pending<=0;stage_length<=0;stage_last<=0;stage_bad<=0;release_lo<=0;
            release_hi<=0;release_hi_carry<=0;
            stage_checked<=0;stage_shape_ok<=0;stage_slot<=0;stage_units<=0;commit_slot<=0;
            stage_write_at<=0;dllp_pending<=0;dllp_bad<=0;dllp_length<=0;
            output_active<=0;output_dllp<=0;output_index<=0;waiting<=0;
            header_limit_o<={COMPLETER_ONLY ? 8'b0 : H_INIT,H_INIT,H_INIT};
            data_limit_o<={COMPLETER_ONLY ? 12'b0 : D_INIT,D_INIT,D_INIT};
            released_o<=0;released_class_o<=0;released_data_o<=0;
            dropped_o<=0;protocol_error_o<=0;recovery_request_o<=0;
        end else if(!link_up_i) begin
            used<=0;qread<=0;qwrite<=0;qcount<=0;head_slot<=0;input_active<=0;input_count<=0;
`ifdef SOC_PCIE_RX_STAGED_COMMIT
            qwrite_oh<=1;
`endif
            head_last<=0;head_class<=0;head_units<=0;head_onehot<=1;read_onehot<=1;
`ifdef SOC_PCIE_RX_READ_AHEAD
            ahead_lane<=2;ahead_group<=1;
`endif
            stage_pending<=0;dllp_pending<=0;output_active<=0;output_index<=0;waiting<=0;
            stage_checked<=0;commit_slot<=0;stage_write_at<=0;
            header_limit_o<={COMPLETER_ONLY ? 8'b0 : H_INIT,H_INIT,H_INIT};
            data_limit_o<={COMPLETER_ONLY ? 12'b0 : D_INIT,D_INIT,D_INIT};
            released_o<=0;dropped_o<=0;protocol_error_o<=0;recovery_request_o<=0;
        end else begin
            released_o<=0;dropped_o<=0;head_slot<=next_head_slot;stage_write_at<=0;
            head_last<=next_head_last;head_class<=next_head_slot/SLOTS_PER_CLASS;head_units<=next_head_units;
            release_lo<={1'b0,head_data_limit[5:0]}+{1'b0,head_units[5:0]};
            release_hi<=head_data_limit[11:6]+head_units[11:6];
            release_hi_carry<=head_data_limit[11:6]+head_units[11:6]+6'd1;
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
                    lasts[b]<=stage_last;units[b]<=stage_units;
                    errors[b]<=stage_bad;used[b]<=1;
                end
`ifdef SOC_PCIE_RX_STAGED_COMMIT
                for(qo=0;qo<SLOTS;qo=qo+1) if(qwrite_oh[qo]) order[qo]<=stage_slot;
                qwrite_oh<={qwrite_oh[SLOTS-2:0],qwrite_oh[SLOTS-1]};
                qwrite<=qwrite==SLOTS-1 ? 0 : qwrite+1'b1;
`else
                order[qwrite]<=stage_slot;qwrite<=qwrite==SLOTS-1 ? 0 : qwrite+1'b1;
`endif
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
                    if(rx_dllp_i) dllp[0]<=rx_data_i; else stage_write_at[0]<=1;
                    if(rx_eop_i) begin
                        if(rx_dllp_i) begin dllp_pending<=1;dllp_length<=1;dllp_bad<=1;end
                        else begin stage_pending<=1;stage_length<=1;stage_last<=0;stage_bad<=1;end
                    end
                end else begin
                    input_bad<=input_bad || rx_error_i || rx_sop_i || rx_dllp_i!=input_dllp;
                    if(input_dllp) begin
                        if(input_count<6) dllp[input_count]<=rx_data_i;
                    end else for(k=0;k<CAP;k=k+1) if(input_count==k) stage_write_at[k]<=1;
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
`ifdef SOC_PCIE_RX_READ_AHEAD
                    ahead_lane<=2;ahead_group<=1;
`endif
                    if(select_dllp) dllp_pending<=0; else waiting<=1;
                end else begin
                    output_active<=1;output_dllp<=select_dllp;output_index<=output_index+1'b1;
                    read_onehot<={read_onehot[READ_CHOICES-2:0],read_onehot[READ_CHOICES-1]};
`ifdef SOC_PCIE_RX_READ_AHEAD
                    ahead_lane<=ahead_lane_next;ahead_group<=ahead_group_next;
`endif
                end
            end
        end
    end
endmodule
`default_nettype wire
