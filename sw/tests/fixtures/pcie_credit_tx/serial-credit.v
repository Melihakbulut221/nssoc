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
    wire [7:0] available_h=hl[reserve_class_i]-hc[reserve_class_i];
    wire [11:0] available_d=dl[reserve_class_i]-dc[reserve_class_i];
    wire header_ok=hi[reserve_class_i] || (available_h!=0 && !available_h[7]);
    wire data_ok=di[reserve_class_i] || (!available_d[11] && available_d>={2'b0,required_data});
    assign reserve_ready_o=initialized_o && request_legal &&
        (reserve_replay_i || (header_ok && data_ok));
    wire consume=reserve_valid_i && reserve_ready_o && !reserve_replay_i;
    wire [7:0] next_hc=hc[fc_class_i]+((consume && reserve_class_i==fc_class_i && !hi[fc_class_i]) ? 8'd1 : 8'd0);
    wire [11:0] next_dc=dc[fc_class_i]+((consume && reserve_class_i==fc_class_i && !di[fc_class_i]) ? {2'b0,required_data} : 12'd0);
    wire [7:0] h_step=fc_header_i-hl[fc_class_i];
    wire [11:0] d_step=fc_data_i-dl[fc_class_i];
    wire [7:0] h_remaining=fc_header_i-next_hc;
    wire [11:0] d_remaining=fc_data_i-next_dc;
    wire h_update_ok=hi[fc_class_i] ? fc_header_i==0 : (!h_step[7] && !h_remaining[7]);
    wire d_update_ok=di[fc_class_i] ? fc_data_i==0 : (!d_step[11] && !d_remaining[11]);
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            seen<=0;hi<=0;di<=0;confirmed<=0;protocol_error_o<=0;
            for(i=0;i<3;i=i+1) begin hl[i]<=0;hc[i]<=0;dl[i]<=0;dc[i]<=0;end
        end else if (!link_up_i) begin
            seen<=0;hi<=0;di<=0;confirmed<=0;protocol_error_o<=0;
            for(i=0;i<3;i=i+1) begin hl[i]<=0;hc[i]<=0;dl[i]<=0;dc[i]<=0;end
        end else begin
            protocol_error_o<=0;
            if (consume) begin
                if (!hi[reserve_class_i]) hc[reserve_class_i]<=hc[reserve_class_i]+8'd1;
                if (!di[reserve_class_i]) dc[reserve_class_i]<=dc[reserve_class_i]+{2'b0,required_data};
            end
            if (all_seen && rx_tlp_seen_i) confirmed<=1;
            if (fc_valid_i) begin
                if (fc_class_i==3 || fc_phase_i==3) protocol_error_o<=1;
                else if (!all_seen) begin
                    if (fc_phase_i==2 || fc_header_i[7] || fc_data_i[11]) protocol_error_o<=1;
                    else begin
                        hl[fc_class_i]<=fc_header_i;dl[fc_class_i]<=fc_data_i;
                        hi[fc_class_i]<=fc_header_i==0;di[fc_class_i]<=fc_data_i==0;
                        seen[fc_class_i]<=1;
                    end
                end else begin
                    if (fc_phase_i==1) confirmed<=1;
                    if (fc_phase_i==2) begin
                        if (h_update_ok && d_update_ok) begin
                            if (!hi[fc_class_i]) hl[fc_class_i]<=fc_header_i;
                            if (!di[fc_class_i]) dl[fc_class_i]<=fc_data_i;
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
