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
    // The reservation verdict is computed for every class from its own
    // registers; the request's class selects a finished result.
    wire [2:0] class_header_ok,class_data_ok;
    genvar vc;
    generate for(vc=0;vc<3;vc=vc+1) begin: class_verdict
        assign class_header_ok[vc]=hi[vc] || (ah[vc]!=0 && !ah[vc][7]);
        assign class_data_ok[vc]=di[vc] || (!ad[vc][11] && {ad[vc],2'b00}>={3'b0,reserve_payload_dw_i});
    end endgenerate
    wire header_ok=class_header_ok[reserve_class_i];
    wire data_ok=class_data_ok[reserve_class_i];
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
    // follows whether the first cycle overwrote that limit. The first-cycle
    // arithmetic runs once per class from that class's registers, and the
    // event's class selects the results.
    wire debit_now=consume && request_class==fc_class_i;
    wire [7:0] class_h_idle [0:2];
    wire [7:0] class_h_debit [0:2];
    wire [11:0] class_d_idle [0:2];
    wire [11:0] class_d_debit [0:2];
    wire [2:0] class_h_back,class_d_back;
    genvar fcc;
    generate for(fcc=0;fcc<3;fcc=fcc+1) begin: class_update
        wire [11:0] csa_b=~dc[fcc];
        wire [11:0] csa_sum=fc_data_i^csa_b^request_data_negated;
        wire [11:0] csa_carry=(fc_data_i&csa_b)|(fc_data_i&request_data_negated)|(csa_b&request_data_negated);
        wire [7:0] h_advance=fc_header_i-hl[fcc];
        wire [11:0] d_advance=fc_data_i-dl[fcc];
        assign class_h_idle[fcc]=fc_header_i-hc[fcc];
        assign class_h_debit[fcc]=fc_header_i+~hc[fcc];
        assign class_d_idle[fcc]=fc_data_i-dc[fcc];
        assign class_d_debit[fcc]=csa_sum+{csa_carry[10:0],1'b1};
        assign class_h_back[fcc]=h_advance[7];
        assign class_d_back[fcc]=d_advance[11];
    end endgenerate
    reg update_valid,update_h_debited,update_d_debited;
    reg [1:0] update_phase,update_class;
    reg [7:0] update_header,update_h_idle,update_h_debit;
    reg [11:0] update_data,update_d_idle,update_d_debit;
    reg update_h_back_now,update_h_back_written,update_d_back_now,update_d_back_written;
    reg update_h_overwritten,update_d_overwritten;
    wire [7:0] h_advance_written=fc_header_i-update_header;
    wire [11:0] d_advance_written=fc_data_i-update_data;
    wire [7:0] h_idle_remaining=update_h_debited ? update_h_debit : update_h_idle;
    wire [11:0] d_idle_remaining=update_d_debited ? update_d_debit : update_d_idle;
    wire h_step_back=update_h_overwritten ? update_h_back_written : update_h_back_now;
    wire d_step_back=update_d_overwritten ? update_d_back_written : update_d_back_now;
    wire [7:0] h_debit_remaining=update_h_debit;
    wire [11:0] d_debit_remaining=update_d_debit;
    wire update_rejected=update_class==3 || update_phase==3;
    // Consumed counts after a debit, registered one cycle ahead. A consume
    // is never in the cycle after a consume, and only a consume changes a
    // consumed count; the two-cycle request hold keeps request_data from
    // that cycle. So in a consume's cycle these equal hc+1 and dc+required.
    reg [7:0] hc_plus [0:2];
    reg [11:0] dc_plus [0:2];
    // Every register's next value is computed twice, for "the request is
    // consumed in this cycle" (variant 1) and "it is not" (variant 0), from
    // registers only; the consume selects between them as the last step.
    // Each variant follows the original update order exactly: the consume's
    // writes first, then the UpdateFC's writes, which take precedence.
    genvar variant;
    generate for(variant=0;variant<2;variant=variant+1) begin: next
        reg [23:0] hl_n,hc_n,ah_n;
        reg [35:0] dl_n,dc_n,ad_n;
        reg [2:0] seen_n,hi_n,di_n;
        reg confirmed_n,error_n,hl_written,dl_written;
        reg h_ok,d_ok,debit;
        integer c;
        always @* begin
            for(c=0;c<3;c=c+1) begin
                hl_n[c*8+:8]=hl[c];hc_n[c*8+:8]=hc[c];ah_n[c*8+:8]=ah[c];
                dl_n[c*12+:12]=dl[c];dc_n[c*12+:12]=dc[c];ad_n[c*12+:12]=ad[c];
            end
            seen_n=seen;hi_n=hi;di_n=di;confirmed_n=confirmed;error_n=0;
            hl_written=0;dl_written=0;
            if (variant) begin
                for(c=0;c<3;c=c+1) if (request_class==c) begin
                    if (!hi[c]) begin hc_n[c*8+:8]=hc_plus[c];ah_n[c*8+:8]=ah[c]-8'd1; end
                    if (!di[c]) begin
                        dc_n[c*12+:12]=dc_plus[c];
                        ad_n[c*12+:12]=ad[c]+request_data_negated;
                    end
                end
            end
            if (all_seen && rx_tlp_seen_i) confirmed_n=1;
            debit=variant && request_class==update_class;
            h_ok=hi[update_class] ? update_header==0 :
                (!h_step_back && !(debit ? h_debit_remaining[7] : h_idle_remaining[7]));
            d_ok=di[update_class] ? update_data==0 :
                (!d_step_back && !(debit ? d_debit_remaining[11] : d_idle_remaining[11]));
            if (update_valid) begin
                if (update_rejected) error_n=1;
                else if (!all_seen) begin
                    if (update_phase==2 || update_header[7] || update_data[11]) error_n=1;
                    else begin
                        hl_n[update_class*8+:8]=update_header;dl_n[update_class*12+:12]=update_data;
                        ah_n[update_class*8+:8]=h_idle_remaining;ad_n[update_class*12+:12]=d_idle_remaining;
                        hi_n[update_class]=update_header==0;di_n[update_class]=update_data==0;
                        seen_n[update_class]=1;hl_written=1;dl_written=1;
                    end
                end else begin
                    if (update_phase==1) confirmed_n=1;
                    if (update_phase==2) begin
                        if (h_ok && d_ok) begin
                            if (!hi[update_class]) begin
                                hl_n[update_class*8+:8]=update_header;hl_written=1;
                                ah_n[update_class*8+:8]=debit ? h_debit_remaining : h_idle_remaining;
                            end
                            if (!di[update_class]) begin
                                dl_n[update_class*12+:12]=update_data;dl_written=1;
                                ad_n[update_class*12+:12]=debit ? d_debit_remaining : d_idle_remaining;
                            end
                            confirmed_n=1;
                        end else error_n=1;
                    end
                    // InitFC1/2 credit values are ignored after FC_INIT1.
                end
            end
        end
    end endgenerate
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
            verdict<=all_seen && confirmed && local_init_done_i && request_legal &&
                (reserve_replay_i || (header_ok && data_ok));
            consumed<=consume;request_stable<=same_request;
            request_class<=reserve_class_i;request_dw<=reserve_payload_dw_i;request_replay<=reserve_replay_i;
            request_data<=required_data;request_data_negated<=-{2'b0,required_data};
            update_valid<=fc_valid_i;update_phase<=fc_phase_i;update_class<=fc_class_i;
            update_header<=fc_header_i;update_data<=fc_data_i;
            update_h_idle<=class_h_idle[fc_class_i];update_h_debit<=class_h_debit[fc_class_i];
            update_d_idle<=class_d_idle[fc_class_i];update_d_debit<=class_d_debit[fc_class_i];
            update_h_back_now<=class_h_back[fc_class_i];update_h_back_written<=h_advance_written[7];
            update_d_back_now<=class_d_back[fc_class_i];update_d_back_written<=d_advance_written[11];
            update_h_overwritten<=(consume ? next[1].hl_written : next[0].hl_written) && update_class==fc_class_i;
            update_d_overwritten<=(consume ? next[1].dl_written : next[0].dl_written) && update_class==fc_class_i;
            update_h_debited<=debit_now && !hi[request_class];
            update_d_debited<=debit_now && !di[request_class];
            for(i=0;i<3;i=i+1) begin
                hc_plus[i]<=hc[i]+8'd1;dc_plus[i]<=dc[i]+{2'b0,request_data};
                hl[i]<=consume ? next[1].hl_n[i*8+:8] : next[0].hl_n[i*8+:8];
                hc[i]<=consume ? next[1].hc_n[i*8+:8] : next[0].hc_n[i*8+:8];
                ah[i]<=consume ? next[1].ah_n[i*8+:8] : next[0].ah_n[i*8+:8];
                dl[i]<=consume ? next[1].dl_n[i*12+:12] : next[0].dl_n[i*12+:12];
                dc[i]<=consume ? next[1].dc_n[i*12+:12] : next[0].dc_n[i*12+:12];
                ad[i]<=consume ? next[1].ad_n[i*12+:12] : next[0].ad_n[i*12+:12];
            end
            seen<=consume ? next[1].seen_n : next[0].seen_n;
            hi<=consume ? next[1].hi_n : next[0].hi_n;
            di<=consume ? next[1].di_n : next[0].di_n;
            confirmed<=consume ? next[1].confirmed_n : next[0].confirmed_n;
            protocol_error_o<=consume ? next[1].error_n : next[0].error_n;
        end
    end
endmodule
`default_nettype wire
