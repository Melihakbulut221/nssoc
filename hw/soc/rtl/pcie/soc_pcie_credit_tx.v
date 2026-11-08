// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// VC0, unscaled classic flow control. Input events must already pass DLLP CRC
// and reserved/VC checks. The local FC transmitter supplies local_init_done_i.
// Reserve exactly once before first transmission; replay does not debit again.
// No receive-buffer advertisement, FC timer, ordering scheduler or PHY here.
module soc_pcie_credit_tx (
    input wire clk_i,rst_ni,link_up_i,local_init_done_i,rx_tlp_seen_i,
    input wire fc_valid_i,
    input wire [1:0] fc_phase_i,fc_class_i,
    input wire [7:0] fc_header_i,
    input wire [11:0] fc_data_i,
    input wire reserve_valid_i,reserve_replay_i,
    input wire [1:0] reserve_class_i,
    input wire [10:0] reserve_payload_dw_i,
    output wire reserve_ready_o,initialized_o,peer_init1_done_o,peer_init2_seen_o,
    output reg protocol_error_o,
    output wire [23:0] header_limit_o,header_consumed_o,
    output wire [35:0] data_limit_o,data_consumed_o,
    output wire [5:0] infinite_o
);
    reg [7:0] hl[0:2],hc[0:2];
    reg [11:0] dl[0:2],dc[0:2];
    reg [2:0] seen,hi,di;
    reg confirmed;
    integer i;
    wire all_seen=&seen;
    assign peer_init1_done_o=rst_ni && link_up_i && all_seen;
    assign peer_init2_seen_o=rst_ni && link_up_i && confirmed;
    assign initialized_o=peer_init1_done_o && confirmed && local_init_done_i;
    assign header_limit_o={hl[2],hl[1],hl[0]};
    assign header_consumed_o={hc[2],hc[1],hc[0]};
    assign data_limit_o={dl[2],dl[1],dl[0]};
    assign data_consumed_o={dc[2],dc[1],dc[0]};
    assign infinite_o={di[2],hi[2],di[1],hi[1],di[0],hi[0]};
    wire request_legal=reserve_class_i<3 && reserve_payload_dw_i<=1024;
    wire [11:0] rounded_dw={1'b0,reserve_payload_dw_i}+12'd3;
    wire [9:0] required_data=rounded_dw[11:2];
    // Available credit per class, kept in registers that always equal
    // limit minus consumed (ah == hl-hc, ad == dl-dc, modulo 256/4096): every
    // branch below that writes a limit or a consumed count writes the
    // matching difference from the same operands. For the data check,
    // ceil(dw/4) <= available is the same as dw <= 4*available.
    reg [7:0] ah[0:2];
    reg [11:0] ad[0:2];
    wire header_ok=hi[reserve_class_i] || (ah[reserve_class_i]!=0 && !ah[reserve_class_i][7]);
    wire data_ok=di[reserve_class_i] ||
        (!ad[reserve_class_i][11] && {ad[reserve_class_i],2'b00}>={3'b0,reserve_payload_dw_i});
    // Registered verdict. The request and its verdict against this cycle's
    // credit are registered; the next cycle grants only if the request is
    // unchanged and nothing was consumed in between. After initialization
    // credit only decreases by a consume (excluded here) and an UpdateFC can
    // only raise it, so a registered grant is never one the current state
    // would refuse. A request is granted only once it has been presented
    // unchanged for two cycles (so the required credit of any debit that
    // meets an UpdateFC in either of its cycles is one registered value), and
    // the cycle after a consume never grants.
    reg verdict,consumed,request_stable;
    reg [1:0] request_class;
    reg [10:0] request_dw;
    reg request_replay;
    reg [9:0] request_data;
    reg [11:0] request_data_negated;
    wire same_request=reserve_class_i==request_class && reserve_payload_dw_i==request_dw &&
        reserve_replay_i==request_replay;
    // Initialization is part of the registered verdict; it only rises until
    // link loss or reset, which gate the grant directly.
    assign reserve_ready_o=rst_ni && link_up_i && verdict && same_request && request_stable && !consumed;
    wire consume=reserve_valid_i && reserve_ready_o && !reserve_replay_i;
    // UpdateFC is processed one cycle after it is presented. The first cycle
    // registers the event with its new-limit-minus-consumed balance without
    // a debit and with one debit (carry-save form, one adder deep), and the
    // sign of its limit advance against the current limit and against the
    // limit the UpdateFC applied in that cycle writes. The second cycle only
    // selects: two consumes are never adjacent, and the required credit of a
    // debit in either cycle is the same registered value, so "one debit"
    // covers a debit in the first cycle or in the second; the advance sign
    // follows whether the first cycle overwrote that limit.
    wire debit_now=consume && request_class==fc_class_i;
    wire [11:0] fc_dc=dc[fc_class_i];
    wire [11:0] csa_b=~fc_dc;
    wire [11:0] csa_sum=fc_data_i^csa_b^request_data_negated;
    wire [11:0] csa_carry=(fc_data_i&csa_b)|(fc_data_i&request_data_negated)|(csa_b&request_data_negated);
    reg update_valid,update_h_debited,update_d_debited;
    reg [1:0] update_phase,update_class;
    reg [7:0] update_header,update_h_idle,update_h_debit;
    reg [11:0] update_data,update_d_idle,update_d_debit;
    reg update_h_back_now,update_h_back_written,update_d_back_now,update_d_back_written;
    reg update_h_overwritten,update_d_overwritten;
    wire [7:0] h_advance_now=fc_header_i-hl[fc_class_i];
    wire [7:0] h_advance_written=fc_header_i-update_header;
    wire [11:0] d_advance_now=fc_data_i-dl[fc_class_i];
    wire [11:0] d_advance_written=fc_data_i-update_data;
    wire [7:0] h_idle_remaining=update_h_debited ? update_h_debit : update_h_idle;
    wire [11:0] d_idle_remaining=update_d_debited ? update_d_debit : update_d_idle;
    wire credit_debit=consume && request_class==update_class;
    wire h_step_back=update_h_overwritten ? update_h_back_written : update_h_back_now;
    wire d_step_back=update_d_overwritten ? update_d_back_written : update_d_back_now;
    wire [7:0] h_debit_remaining=update_h_debit;
    wire [11:0] d_debit_remaining=update_d_debit;
    wire h_update_ok=hi[update_class] ? update_header==0 :
        (!h_step_back && !(credit_debit ? h_debit_remaining[7] : h_idle_remaining[7]));
    wire d_update_ok=di[update_class] ? update_data==0 :
        (!d_step_back && !(credit_debit ? d_debit_remaining[11] : d_idle_remaining[11]));
    // Limit writes of the UpdateFC applied in this cycle, for the next one.
    wire update_rejected=update_class==3 || update_phase==3;
    wire init_write=update_valid && !update_rejected && !all_seen &&
        !(update_phase==2 || update_header[7] || update_data[11]);
    wire apply_update=update_valid && !update_rejected && all_seen && update_phase==2 &&
        h_update_ok && d_update_ok;
    wire hl_written=init_write || (apply_update && !hi[update_class]);
    wire dl_written=init_write || (apply_update && !di[update_class]);
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            seen<=0;hi<=0;di<=0;confirmed<=0;protocol_error_o<=0;
            for(i=0;i<3;i=i+1) begin hl[i]<=0;hc[i]<=0;dl[i]<=0;dc[i]<=0;ah[i]<=0;ad[i]<=0;end
            verdict<=0;consumed<=0;request_stable<=0;request_class<=0;request_dw<=0;request_replay<=0;
            request_data<=0;request_data_negated<=0;update_valid<=0;
        end else if (!link_up_i) begin
            seen<=0;hi<=0;di<=0;confirmed<=0;protocol_error_o<=0;
            for(i=0;i<3;i=i+1) begin hl[i]<=0;hc[i]<=0;dl[i]<=0;dc[i]<=0;ah[i]<=0;ad[i]<=0;end
            verdict<=0;consumed<=0;request_stable<=0;update_valid<=0;
        end else begin
            protocol_error_o<=0;
            verdict<=all_seen && confirmed && local_init_done_i && request_legal &&
                (reserve_replay_i || (header_ok && data_ok));
            consumed<=consume;request_stable<=same_request;
            request_class<=reserve_class_i;request_dw<=reserve_payload_dw_i;request_replay<=reserve_replay_i;
            request_data<=required_data;request_data_negated<=-{2'b0,required_data};
            update_valid<=fc_valid_i;update_phase<=fc_phase_i;update_class<=fc_class_i;
            update_header<=fc_header_i;update_data<=fc_data_i;
            update_h_idle<=fc_header_i-hc[fc_class_i];update_h_debit<=fc_header_i+~hc[fc_class_i];
            update_d_idle<=fc_data_i-fc_dc;update_d_debit<=csa_sum+{csa_carry[10:0],1'b1};
            update_h_back_now<=h_advance_now[7];update_h_back_written<=h_advance_written[7];
            update_d_back_now<=d_advance_now[11];update_d_back_written<=d_advance_written[11];
            update_h_overwritten<=hl_written && update_class==fc_class_i;
            update_d_overwritten<=dl_written && update_class==fc_class_i;
            update_h_debited<=debit_now && !hi[request_class];
            update_d_debited<=debit_now && !di[request_class];
            if (consume) begin
                if (!hi[request_class]) begin
                    hc[request_class]<=hc[request_class]+8'd1;
                    ah[request_class]<=ah[request_class]-8'd1;
                end
                if (!di[request_class]) begin
                    dc[request_class]<=dc[request_class]+{2'b0,request_data};
                    ad[request_class]<=ad[request_class]+request_data_negated;
                end
            end
            if (all_seen && rx_tlp_seen_i) confirmed<=1;
            if (update_valid) begin
                if (update_class==3 || update_phase==3) protocol_error_o<=1;
                else if (!all_seen) begin
                    if (update_phase==2 || update_header[7] || update_data[11]) protocol_error_o<=1;
                    else begin
                        hl[update_class]<=update_header;dl[update_class]<=update_data;
                        ah[update_class]<=h_idle_remaining;ad[update_class]<=d_idle_remaining;
                        hi[update_class]<=update_header==0;di[update_class]<=update_data==0;
                        seen[update_class]<=1;
                    end
                end else begin
                    if (update_phase==1) confirmed<=1;
                    if (update_phase==2) begin
                        if (h_update_ok && d_update_ok) begin
                            if (!hi[update_class]) begin
                                hl[update_class]<=update_header;
                                ah[update_class]<=credit_debit ? h_debit_remaining : h_idle_remaining;
                            end
                            if (!di[update_class]) begin
                                dl[update_class]<=update_data;
                                ad[update_class]<=credit_debit ? d_debit_remaining : d_idle_remaining;
                            end
                            confirmed<=1;
                        end else protocol_error_o<=1;
                    end
                    // InitFC1/2 credit values are ignored after FC_INIT1.
                end
            end
        end
    end
endmodule
`default_nettype wire
