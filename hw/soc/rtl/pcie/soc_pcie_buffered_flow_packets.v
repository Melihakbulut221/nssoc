// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Real local receive storage and transmitted FC DLLPs around the frozen
// completer-only packet path. No PHY/LTSSM, calibrated link timers or SoC wiring.
module soc_pcie_buffered_flow_packets #(
    parameter [15:0] VENDOR_ID=16'hffff,DEVICE_ID=16'h0000,
    parameter integer APB_TIMEOUT=256,MAX_TLP_DWORDS=8,
    parameter integer REPLAY_DEPTH=4,REPLAY_TIMEOUT_CYCLES=1024,MAX_REPLAYS=3,
    parameter integer RX_SLOTS_PER_CLASS=2,FC_REFRESH_CYCLES=128
) (
    input wire clk_i,rst_ni,link_up_i,training_i,retrain_done_i,
    output wire local_init_done_o,local_init2_sent_o,requester_admission_o,
    output wire [7:0] outstanding_requests_o,rx_queued_o,
    output wire [23:0] rx_header_limit_o,rx_occupied_o,fc_sent_header_o,
    output wire [35:0] rx_data_limit_o,fc_sent_data_o,
    output wire rx_released_o,rx_dropped_o,rx_recovery_o,fc_sent_o,
    output wire [1:0] rx_released_class_o,fc_sent_phase_o,fc_sent_class_o,
    output wire [11:0] rx_released_data_o,
    output wire initialized_o,peer_init1_done_o,peer_init2_seen_o,credit_error_o,
    output wire [23:0] credit_header_limit_o,credit_header_consumed_o,
    output wire [35:0] credit_data_limit_o,credit_data_consumed_o,
    output wire [5:0] credit_infinite_o,
    input wire [15:0] function_id_i,
    input wire [7:0] rx_data_i,
    input wire rx_sop_i,rx_eop_i,rx_error_i,rx_valid_i,rx_dllp_i,
    output wire rx_ready_o,
    output wire [11:0] rx_expected_sequence_o,tx_next_sequence_o,
    output wire packet_accepted_o,packet_duplicate_o,packet_rejected_o,rx_tlp_seen_o,
    output wire [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,tx_dllp_o,tx_replay_o,
    input wire tx_ready_i,
    output wire fc_valid_o,
    output wire [1:0] fc_phase_o,fc_class_o,
    output wire [7:0] fc_header_o,
    output wire [11:0] fc_data_o,
    output wire bad_dllp_o,unsupported_dllp_o,
    output wire reserve_valid_o,
    output wire reserve_ready_o,
    output wire [1:0] reserve_class_o,
    output wire [10:0] reserve_payload_dw_o,
    output wire reserve_replay_o,
    output wire [4:0] buffered_o,outstanding_o,
    output wire [11:0] acknowledged_sequence_o,
    output wire replay_started_o,timeout_o,protocol_error_o,retry_exhausted_o,source_error_o,retrain_request_o,
    output wire psel_o,penable_o,
    output wire [11:0] paddr_o,
    output wire pwrite_o,
    output wire [3:0] pstrb_o,
    output wire [31:0] pwdata_o,
    input wire pready_i,pslverr_i,
    input wire [31:0] prdata_i,
    output wire error_o,memory_enable_o,
    output wire [31:0] bar0_o
);
    // A link retraining completion restarts the local FC/sequence/replay epoch.
    // No fabric, PHY, receive-credit requester or outstanding NP request exists.
    wire local_reset=rst_ni && link_up_i && !retrain_done_i;
    assign requester_admission_o=1'b0;
    assign outstanding_requests_o=8'b0;
    wire [7:0] q_data,flow_data,advert_data;
    wire q_sop,q_eop,q_valid,q_dllp,q_error,q_ready;
    wire flow_sop,flow_eop,flow_valid,flow_dllp,flow_replay,flow_ready;
    wire advert_sop,advert_eop,advert_valid,advert_ready;
    wire flow_error,flow_protocol,flow_retrain,rx_protocol;
    soc_pcie_rx_credit #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS),.SLOTS_PER_CLASS(RX_SLOTS_PER_CLASS),
        .COMPLETER_ONLY(1)) receive_ownership(
        .clk_i(clk_i),.rst_ni(local_reset),.link_up_i(link_up_i),.training_i(training_i),
        .initialized_i(peer_init1_done_o && local_init2_sent_o),.rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),
        .rx_eop_i(rx_eop_i),.rx_valid_i(rx_valid_i),.rx_dllp_i(rx_dllp_i),.rx_error_i(rx_error_i),
        .rx_ready_o(rx_ready_o),.out_data_o(q_data),.out_sop_o(q_sop),.out_eop_o(q_eop),
        .out_valid_o(q_valid),.out_dllp_o(q_dllp),.out_error_o(q_error),.out_ready_i(q_ready),
        .packet_accepted_i(packet_accepted_o),.packet_duplicate_i(packet_duplicate_o),
        .packet_rejected_i(packet_rejected_o),.header_limit_o(rx_header_limit_o),
        .data_limit_o(rx_data_limit_o),.occupied_o(rx_occupied_o),.queued_o(rx_queued_o),
        .released_o(rx_released_o),.released_class_o(rx_released_class_o),
        .released_data_o(rx_released_data_o),.dropped_o(rx_dropped_o),
        .protocol_error_o(rx_protocol),.recovery_request_o(rx_recovery_o));
    soc_pcie_fc_tx #(.REFRESH_CYCLES(FC_REFRESH_CYCLES)) advertiser(
        .clk_i(clk_i),.rst_ni(local_reset),.link_up_i(link_up_i),.training_i(training_i),
        .peer_init1_done_i(peer_init1_done_o),.peer_init2_seen_i(peer_init2_seen_o),
        .header_limit_i(rx_header_limit_o),.data_limit_i(rx_data_limit_o),
        .local_init_done_o(local_init_done_o),.local_init2_sent_o(local_init2_sent_o),.sent_header_o(fc_sent_header_o),
        .sent_data_o(fc_sent_data_o),.sent_valid_o(fc_sent_o),
        .sent_phase_o(fc_sent_phase_o),.sent_class_o(fc_sent_class_o),
        .tx_data_o(advert_data),.tx_sop_o(advert_sop),.tx_eop_o(advert_eop),
        .tx_valid_o(advert_valid),.tx_ready_i(advert_ready));
    // Packet-level round robin. Ownership locks on offered first byte, including
    // stalls, and remains locked through accepted EOP and any inter-byte bubbles.
    reg owner,locked,prefer_flow;
    wire chosen=locked ? owner : (flow_valid && (!advert_valid || prefer_flow));
    assign tx_data_o=chosen ? flow_data : advert_data;
    assign tx_sop_o=chosen ? flow_sop : advert_sop;
    assign tx_eop_o=chosen ? flow_eop : advert_eop;
    assign tx_valid_o=local_reset && (chosen ? flow_valid : advert_valid);
    assign tx_dllp_o=chosen ? flow_dllp : 1'b1;
    assign tx_replay_o=chosen && flow_replay;
    assign flow_ready=local_reset && chosen && tx_ready_i;
    assign advert_ready=local_reset && !chosen && tx_ready_i;
    always @(posedge clk_i or negedge local_reset) begin
        if(!local_reset) begin owner<=0;locked<=0;prefer_flow<=0;end
        else if(tx_valid_o) begin
            if(tx_ready_i && tx_eop_o) begin locked<=0;prefer_flow<=!chosen;end
            else begin owner<=chosen;locked<=1;end
        end
    end
    assign error_o=flow_error || rx_protocol;
    assign protocol_error_o=flow_protocol || rx_protocol;
    assign retrain_request_o=flow_retrain || rx_recovery_o;
    soc_pcie_flow_packets #(.VENDOR_ID(VENDOR_ID),.DEVICE_ID(DEVICE_ID),.APB_TIMEOUT(APB_TIMEOUT),
        .MAX_TLP_DWORDS(MAX_TLP_DWORDS),.REPLAY_DEPTH(REPLAY_DEPTH),
        .REPLAY_TIMEOUT_CYCLES(REPLAY_TIMEOUT_CYCLES),.MAX_REPLAYS(MAX_REPLAYS)) flow(
        .clk_i(clk_i),
        .rst_ni(local_reset),
        .link_up_i(link_up_i),
        .training_i(training_i),
        .retrain_done_i(retrain_done_i),
        .initialized_o(initialized_o),
        .peer_init1_done_o(peer_init1_done_o),
        .peer_init2_seen_o(peer_init2_seen_o),
        .credit_error_o(credit_error_o),
        .credit_header_limit_o(credit_header_limit_o),
        .credit_header_consumed_o(credit_header_consumed_o),
        .credit_data_limit_o(credit_data_limit_o),
        .credit_data_consumed_o(credit_data_consumed_o),
        .credit_infinite_o(credit_infinite_o),
        .function_id_i(function_id_i),
        .rx_data_i(q_data),
        .rx_sop_i(q_sop),
        .rx_eop_i(q_eop),
        .rx_error_i(q_error),
        .rx_valid_i(q_valid),
        .rx_dllp_i(q_dllp),
        .rx_ready_o(q_ready),
        .rx_expected_sequence_o(rx_expected_sequence_o),
        .tx_next_sequence_o(tx_next_sequence_o),
        .packet_accepted_o(packet_accepted_o),
        .packet_duplicate_o(packet_duplicate_o),
        .packet_rejected_o(packet_rejected_o),
        .rx_tlp_seen_o(rx_tlp_seen_o),
        .tx_data_o(flow_data),
        .tx_sop_o(flow_sop),
        .tx_eop_o(flow_eop),
        .tx_valid_o(flow_valid),
        .tx_dllp_o(flow_dllp),
        .tx_replay_o(flow_replay),
        .tx_ready_i(flow_ready),
        .fc_valid_o(fc_valid_o),
        .fc_phase_o(fc_phase_o),
        .fc_class_o(fc_class_o),
        .fc_header_o(fc_header_o),
        .fc_data_o(fc_data_o),
        .bad_dllp_o(bad_dllp_o),
        .unsupported_dllp_o(unsupported_dllp_o),
        .reserve_valid_o(reserve_valid_o),
        .reserve_ready_o(reserve_ready_o),
        .reserve_class_o(reserve_class_o),
        .reserve_payload_dw_o(reserve_payload_dw_o),
        .reserve_replay_o(reserve_replay_o),
        .buffered_o(buffered_o),
        .outstanding_o(outstanding_o),
        .acknowledged_sequence_o(acknowledged_sequence_o),
        .replay_started_o(replay_started_o),
        .timeout_o(timeout_o),
        .protocol_error_o(flow_protocol),
        .retry_exhausted_o(retry_exhausted_o),
        .source_error_o(source_error_o),
        .retrain_request_o(flow_retrain),
        .psel_o(psel_o),
        .penable_o(penable_o),
        .paddr_o(paddr_o),
        .pwrite_o(pwrite_o),
        .pstrb_o(pstrb_o),
        .pwdata_o(pwdata_o),
        .pready_i(pready_i),
        .pslverr_i(pslverr_i),
        .prdata_i(prdata_i),
        .error_o(flow_error),
        .memory_enable_o(memory_enable_o),
        .bar0_o(bar0_o),
        .local_init_done_i(local_init_done_o));
endmodule
`default_nettype wire
