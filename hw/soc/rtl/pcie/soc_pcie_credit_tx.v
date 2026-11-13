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
    // The cycle after an FC event's application never grants either: a
    // consume's available-data debit is finished from a low half registered
    // in the cycle before, which must see the same available credit, and
    // only an application or a consume changes it.
    reg verdict,consumed,request_stable,applied;
    reg [1:0] request_class;
    reg [10:0] request_dw;
    reg request_replay;
    reg [9:0] request_data;
    reg [11:0] request_data_negated;
    wire same_request=reserve_class_i==request_class && reserve_payload_dw_i==request_dw &&
        reserve_replay_i==request_replay;
    // Initialization is part of the registered verdict; it only rises until
    // link loss or reset, which gate the grant directly.
    // The next-state select uses the grant without its reset and link
    // terms: under reset or link loss the registers are cleared regardless.
    wire grant=verdict && same_request && request_stable && !consumed && !applied;
    assign reserve_ready_o=rst_ni && link_up_i && grant;
    wire consume=reserve_valid_i && grant && !reserve_replay_i;
    // UpdateFC takes three cycles from presentation to its effect.
    //  A: the event is registered.
    //  B: from the registered event and this cycle's consumed counts and
    //     limits, the new-limit-minus-consumed balance without a debit and
    //     with one debit (carry-save form), and the limit-advance borrow
    //     against the current limit and against the limit the event being
    //     applied in this cycle writes, are formed up to their low halves;
    //     the low halves, their carries and the high-half operands are
    //     registered. Each class is computed from its own registers and the
    //     event's class selects the results.
    //  C: the high halves are completed and the update is applied.
    // A debit in A's cycle is already in B's consumed counts. Debits in B's
    // and C's cycles are never adjacent, so "one debit" covers either, and
    // the two-cycle request hold makes B's registered required credit the
    // one of a debit in either cycle. The advance borrow follows whether
    // the event applied in B's cycle overwrote that limit.
    reg a_valid;
    reg [1:0] a_phase,a_class;
    reg [7:0] a_header;
    reg [11:0] a_data;
    wire debit_now=consume && request_class==a_class;
    // Stage B forms each sum in 4-bit blocks: the low block, and the middle
    // and high blocks for both carries in (with their carries out). Stage C
    // finishes it with two selects.
    function [22:0] part12;
        input [11:0] a,b;
        input cin;
        reg [4:0] lo,m0,m1;
        reg [3:0] h0,h1;
        begin
            lo={1'b0,a[3:0]}+{1'b0,b[3:0]}+{4'b0,cin};
            m0={1'b0,a[7:4]}+{1'b0,b[7:4]};m1={1'b0,a[7:4]}+{1'b0,b[7:4]}+5'd1;
            h0=a[11:8]+b[11:8];h1=a[11:8]+b[11:8]+4'd1;
            part12={h1,h0,m1,m0,lo};
        end
    endfunction
    function [11:0] sum12;
        input [22:0] p;
        reg cm;
        begin
            cm=p[4] ? p[14] : p[9];
            sum12={cm ? p[22:19] : p[18:15],p[4] ? p[13:10] : p[8:5],p[3:0]};
        end
    endfunction
    function [12:0] part8;
        input [7:0] a,b;
        input cin;
        reg [4:0] lo;
        reg [3:0] h0,h1;
        begin
            lo={1'b0,a[3:0]}+{1'b0,b[3:0]}+{4'b0,cin};
            h0=a[7:4]+b[7:4];h1=a[7:4]+b[7:4]+4'd1;
            part8={h1,h0,lo};
        end
    endfunction
    function [7:0] sum8;
        input [12:0] p;
        begin sum8={p[4] ? p[12:9] : p[8:5],p[3:0]}; end
    endfunction
    wire [12:0] class_hi [0:2];
    wire [12:0] class_hd [0:2];
    wire [12:0] class_ha [0:2];
    wire [22:0] class_di [0:2];
    wire [22:0] class_dd [0:2];
    wire [22:0] class_da [0:2];
    genvar fcc;
    generate for(fcc=0;fcc<3;fcc=fcc+1) begin: class_update
        wire [11:0] csa_b=~dc[fcc];
        wire [11:0] csa_sum=a_data^csa_b^request_data_negated;
        wire [11:0] csa_carry=(a_data&csa_b)|(a_data&request_data_negated)|(csa_b&request_data_negated);
        // a-b = a+~b+1; header debit variant a-b-1 = a+~b.
        assign class_hi[fcc]=part8(a_header,~hc[fcc],1'b1);
        assign class_hd[fcc]=part8(a_header,~hc[fcc],1'b0);
        assign class_ha[fcc]=part8(a_header,~hl[fcc],1'b1);
        assign class_di[fcc]=part12(a_data,csa_b,1'b1);
        assign class_dd[fcc]=part12(csa_sum,{csa_carry[10:0],1'b0},1'b1);
        assign class_da[fcc]=part12(a_data,~dl[fcc],1'b1);
    end endgenerate
    // Stage B registers (the event as seen by stage C).
    reg update_valid,update_h_debited,update_d_debited;
    reg [1:0] update_phase,update_class;
    reg [7:0] update_header;
    reg [11:0] update_data;
    reg update_h_overwritten,update_d_overwritten;
    reg [12:0] b_hi,b_hd,b_ha,b_hw;
    reg [22:0] b_di,b_dd,b_da,b_dw;
    wire [7:0] update_h_idle=sum8(b_hi);
    wire [7:0] update_h_debit=sum8(b_hd);
    wire [11:0] update_d_idle=sum12(b_di);
    wire [11:0] update_d_debit=sum12(b_dd);
    wire [7:0] h_advance_now=sum8(b_ha);
    wire [7:0] h_advance_written=sum8(b_hw);
    wire [11:0] d_advance_now=sum12(b_da);
    wire [11:0] d_advance_written=sum12(b_dw);
    wire update_h_back_now=h_advance_now[7];
    wire update_h_back_written=h_advance_written[7];
    wire update_d_back_now=d_advance_now[11];
    wire update_d_back_written=d_advance_written[11];
    wire [7:0] h_idle_remaining=update_h_debited ? update_h_debit : update_h_idle;
    wire [11:0] d_idle_remaining=update_d_debited ? update_d_debit : update_d_idle;
    wire h_step_back=update_h_overwritten ? update_h_back_written : update_h_back_now;
    wire d_step_back=update_d_overwritten ? update_d_back_written : update_d_back_now;
    wire [7:0] h_debit_remaining=update_h_debit;
    wire [11:0] d_debit_remaining=update_d_debit;
    wire update_rejected=update_class==3 || update_phase==3;
    // The event's class's infinite flags and its zero tests are registered
    // with the event in stage B. Only an InitFC applied in stage C writes
    // those flags, so the registered flag takes that write when the two
    // events have the same class.
    reg update_h_infinite,update_d_infinite,update_header_zero,update_data_zero;
    wire init_applied=update_valid && !update_rejected && !all_seen &&
        !(update_phase==2 || update_header[7] || update_data[11]);
    // Consumed counts after a debit: hc+1 and the low half of dc+required
    // (with its carry) are registered one cycle ahead, and the high half is
    // finished in the consume's cycle. A consume is never in the cycle after
    // a consume, and only a consume changes a consumed count; the two-cycle
    // request hold keeps request_data from that cycle. So in a consume's
    // cycle these equal hc+1 and dc+required.
    // The available data after a debit, ad-required, is split the same way:
    // a consume is never in the cycle after an FC event's application or
    // after a consume, so ad is also unchanged since the cycle before.
    reg [7:0] hc_plus [0:2];
    reg [6:0] dc_plus_lo [0:2];
    reg [6:0] ad_minus_lo [0:2];
    wire [11:0] dc_plus [0:2];
    wire [11:0] ad_minus [0:2];
    genvar dpc;
    generate for(dpc=0;dpc<3;dpc=dpc+1) begin: consumed_plus
        assign dc_plus[dpc]={dc[dpc][11:6]+{2'b0,request_data[9:6]}+dc_plus_lo[dpc][6],dc_plus_lo[dpc][5:0]};
        assign ad_minus[dpc]={ad[dpc][11:6]+request_data_negated[11:6]+ad_minus_lo[dpc][6],ad_minus_lo[dpc][5:0]};
    end endgenerate
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
                        ad_n[c*12+:12]=ad_minus[c];
                    end
                end
            end
            if (all_seen && rx_tlp_seen_i) confirmed_n=1;
            debit=variant && request_class==update_class;
            h_ok=update_h_infinite ? update_header_zero :
                (!h_step_back && !(debit ? h_debit_remaining[7] : h_idle_remaining[7]));
            d_ok=update_d_infinite ? update_data_zero :
                (!d_step_back && !(debit ? d_debit_remaining[11] : d_idle_remaining[11]));
            if (update_valid) begin
                if (update_rejected) error_n=1;
                else if (!all_seen) begin
                    if (update_phase==2 || update_header[7] || update_data[11]) error_n=1;
                    else begin
                        hl_n[update_class*8+:8]=update_header;dl_n[update_class*12+:12]=update_data;
                        ah_n[update_class*8+:8]=h_idle_remaining;ad_n[update_class*12+:12]=d_idle_remaining;
                        hi_n[update_class]=update_header_zero;di_n[update_class]=update_data_zero;
                        seen_n[update_class]=1;hl_written=1;dl_written=1;
                    end
                end else begin
                    if (update_phase==1) confirmed_n=1;
                    if (update_phase==2) begin
                        if (h_ok && d_ok) begin
                            if (!update_h_infinite) begin
                                hl_n[update_class*8+:8]=update_header;hl_written=1;
                                ah_n[update_class*8+:8]=debit ? h_debit_remaining : h_idle_remaining;
                            end
                            if (!update_d_infinite) begin
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
`ifdef SOC_PCIE_CREDIT_PICK
    // docs/combined-timing.md section 19 (default off): the consume select
    // between the two variants' next values is one multiplexer per bit in a
    // module of its own (keep_hierarchy keeps the boundary through
    // synthesis; the flow's final flatten removes it after mapping). In the
    // default build synthesis merges the consume into each variant's update
    // checks (h_ok, d_ok and the limit write enables), so the grant's
    // request compare and the reservation handshake reach the limit,
    // consumed and available registers through about ten more gates. Here
    // consume is the last select before each register, as the comment on
    // the variants describes. The function is the same expression.
    localparam integer PICK_W=3*8*3+3*12*3+3*3+2+2;
    wire [PICK_W-1:0] picked;
    soc_pcie_credit_pick #(.W(PICK_W)) pick(.sel_i(consume),
        .one_i({next[1].hl_n,next[1].hc_n,next[1].ah_n,next[1].dl_n,next[1].dc_n,next[1].ad_n,
                next[1].seen_n,next[1].hi_n,next[1].di_n,next[1].confirmed_n,next[1].error_n,
                next[1].hl_written,next[1].dl_written}),
        .zero_i({next[0].hl_n,next[0].hc_n,next[0].ah_n,next[0].dl_n,next[0].dc_n,next[0].ad_n,
                 next[0].seen_n,next[0].hi_n,next[0].di_n,next[0].confirmed_n,next[0].error_n,
                 next[0].hl_written,next[0].dl_written}),
        .y_o(picked));
    wire [23:0] picked_hl,picked_hc,picked_ah;
    wire [35:0] picked_dl,picked_dc,picked_ad;
    wire [2:0] picked_seen,picked_hi,picked_di;
    wire picked_confirmed,picked_error,picked_hl_written,picked_dl_written;
    assign {picked_hl,picked_hc,picked_ah,picked_dl,picked_dc,picked_ad,picked_seen,picked_hi,picked_di,
            picked_confirmed,picked_error,picked_hl_written,picked_dl_written}=picked;
`endif
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            seen<=0;hi<=0;di<=0;confirmed<=0;protocol_error_o<=0;
            for(i=0;i<3;i=i+1) begin hl[i]<=0;hc[i]<=0;dl[i]<=0;dc[i]<=0;ah[i]<=0;ad[i]<=0;end
            verdict<=0;consumed<=0;request_stable<=0;request_class<=0;request_dw<=0;request_replay<=0;
            request_data<=0;request_data_negated<=0;update_valid<=0;a_valid<=0;applied<=0;
        end else if (!link_up_i) begin
            seen<=0;hi<=0;di<=0;confirmed<=0;protocol_error_o<=0;
            for(i=0;i<3;i=i+1) begin hl[i]<=0;hc[i]<=0;dl[i]<=0;dc[i]<=0;ah[i]<=0;ad[i]<=0;end
            verdict<=0;consumed<=0;request_stable<=0;update_valid<=0;a_valid<=0;applied<=0;
        end else begin
            verdict<=all_seen && confirmed && local_init_done_i && request_legal &&
                (reserve_replay_i || (header_ok && data_ok));
            consumed<=consume;request_stable<=same_request;applied<=update_valid;
            request_class<=reserve_class_i;request_dw<=reserve_payload_dw_i;request_replay<=reserve_replay_i;
            request_data<=required_data;request_data_negated<=-{2'b0,required_data};
            a_valid<=fc_valid_i;a_phase<=fc_phase_i;a_class<=fc_class_i;
            a_header<=fc_header_i;a_data<=fc_data_i;
            update_valid<=a_valid;update_phase<=a_phase;update_class<=a_class;
            update_header<=a_header;update_data<=a_data;
            update_header_zero<=a_header==0;update_data_zero<=a_data==0;
            update_h_infinite<=(init_applied && update_class==a_class) ? update_header_zero : hi[a_class];
            update_d_infinite<=(init_applied && update_class==a_class) ? update_data_zero : di[a_class];
            b_hi<=class_hi[a_class];b_hd<=class_hd[a_class];b_ha<=class_ha[a_class];
            b_hw<=part8(a_header,~update_header,1'b1);
            b_di<=class_di[a_class];b_dd<=class_dd[a_class];b_da<=class_da[a_class];
            b_dw<=part12(a_data,~update_data,1'b1);
`ifdef SOC_PCIE_CREDIT_PICK
            update_h_overwritten<=picked_hl_written && update_class==a_class;
            update_d_overwritten<=picked_dl_written && update_class==a_class;
`else
            update_h_overwritten<=(consume ? next[1].hl_written : next[0].hl_written) && update_class==a_class;
            update_d_overwritten<=(consume ? next[1].dl_written : next[0].dl_written) && update_class==a_class;
`endif
            update_h_debited<=debit_now && !hi[request_class];
            update_d_debited<=debit_now && !di[request_class];
            for(i=0;i<3;i=i+1) begin
                hc_plus[i]<=hc[i]+8'd1;dc_plus_lo[i]<={1'b0,dc[i][5:0]}+{1'b0,request_data[5:0]};
                ad_minus_lo[i]<={1'b0,ad[i][5:0]}+{1'b0,request_data_negated[5:0]};
`ifdef SOC_PCIE_CREDIT_PICK
                hl[i]<=picked_hl[i*8+:8];hc[i]<=picked_hc[i*8+:8];ah[i]<=picked_ah[i*8+:8];
                dl[i]<=picked_dl[i*12+:12];dc[i]<=picked_dc[i*12+:12];ad[i]<=picked_ad[i*12+:12];
            end
            seen<=picked_seen;hi<=picked_hi;di<=picked_di;
            confirmed<=picked_confirmed;protocol_error_o<=picked_error;
`else
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
`endif
        end
    end
endmodule
`ifdef SOC_PCIE_CREDIT_PICK
// Section 19: a W-bit two-input multiplexer, kept as a module through
// synthesis so the select stays the last gate of every bit.
(* keep_hierarchy *)
module soc_pcie_credit_pick #(parameter integer W=1) (
    input wire sel_i,
    input wire [W-1:0] one_i,zero_i,
    output wire [W-1:0] y_o
);
    assign y_o=sel_i ? one_i : zero_i;
endmodule
`endif
`default_nettype wire
