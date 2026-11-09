// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Standalone single-clock byte packet boundary. The retry store retains encoded
// TLPs; generated ACK/NAK DLLPs bypass it. Credit reservation is external, exactly
// once per original TLP; replay bypasses reservation. No local credit advertiser,
// PCS, LTSSM, physical timer calibration, clock crossing, or SoC integration.
module soc_pcie_reliable_packets #(
    parameter [15:0] VENDOR_ID=16'hffff,DEVICE_ID=16'h0000,
    parameter integer APB_TIMEOUT=256,MAX_TLP_DWORDS=8,
    parameter integer REPLAY_DEPTH=4,REPLAY_TIMEOUT_CYCLES=1024,MAX_REPLAYS=3
) (
    input wire clk_i,rst_ni,link_up_i,training_i,retrain_done_i,
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
    input wire reserve_ready_i,
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
    wire local_reset=rst_ni && link_up_i;
    // Registered link/reset copies for the replay store and the link layer,
    // cleared asynchronously with local_reset and released one clock later;
    // the slices and arbiter use local_reset itself. The D
    // inputs differ only so synthesis keeps two flops.
    // The DLLP receiver has its own copy, so its ready and registers start
    // at a flop with only its own loads. Its first beat can come from the
    // receive slice no earlier than the cycle after local_reset rises, when
    // this copy is released.
    reg up_retry,up_link,up_dllp;
    always @(posedge clk_i or negedge local_reset) begin
        if(!local_reset) begin up_retry<=0;up_link<=0;up_dllp<=0;end
        else begin up_retry<=1'b1;up_link<=link_up_i;up_dllp<=rst_ni || training_i;end
    end
    // Receive register slice. Queue beats reach the DLLP and TLP consumers
    // one cycle later, from flops, so the queue read and the consumers' end
    // of frame checks are separate stages. A TLP frame still starts only when
    // the TLP consumer can take its first beat: with the slice empty, nothing
    // is in flight and that consumer's ready cannot fall before the beat
    // arrives. A TLP the consumer cannot start therefore stays in the queue,
    // and DLLPs (ACKs that free the replay store) are never held behind it.
    wire [7:0] slice_data;
    wire slice_sop,slice_eop,slice_error,slice_dllp,slice_valid,slice_ready,slice_room;
    reg rx_input_active;
    wire tlp_first=!rx_dllp_i && (rx_sop_i || !rx_input_active);
    wire tlp_ready,dllp_ready;
    assign rx_ready_o=local_reset && slice_room && (!tlp_first || (!slice_valid && tlp_ready));
    always @(posedge clk_i or negedge local_reset) begin
        if(!local_reset) rx_input_active<=0;
        else if(rx_valid_i && rx_ready_o) begin
            if(rx_sop_i) rx_input_active<=1;
            if(rx_eop_i) rx_input_active<=0;
        end
    end
    soc_pcie_stream_skid #(.W(12)) receive_slice(
        .clk_i(clk_i),.rst_ni(local_reset),.clear_i(1'b0),
        .s_data_i({rx_data_i,rx_sop_i,rx_eop_i,rx_error_i,rx_dllp_i}),.s_valid_i(rx_valid_i && rx_ready_o),.s_ready_o(slice_room),
        .m_data_o({slice_data,slice_sop,slice_eop,slice_error,slice_dllp}),.m_valid_o(slice_valid),.m_ready_i(slice_ready));
    reg rx_active,rx_kind;
    wire selected_kind=slice_sop ? slice_dllp : rx_kind;
    wire kind_error=rx_active && !slice_sop && rx_kind!=slice_dllp;
    assign slice_ready=selected_kind ? dllp_ready : tlp_ready;
    always @(posedge clk_i or negedge local_reset) begin
        if(!local_reset) begin rx_active<=0;rx_kind<=0;end
        else if(slice_valid && slice_ready) begin
            if(slice_sop) begin rx_kind<=slice_dllp;rx_active<=1;end
            if(slice_eop) rx_active<=0;
        end
    end
    wire ack_valid,ack_nak,ack_ready;
    wire [11:0] ack_sequence;
    soc_pcie_dllp_rx receiver(.clk_i(clk_i),.rst_ni(up_dllp),
        .rx_data_i(slice_data),.rx_sop_i(slice_sop),.rx_eop_i(slice_eop),
        .rx_error_i(slice_error || kind_error),.rx_valid_i(slice_valid && selected_kind),.rx_ready_o(dllp_ready),
        .ack_valid_o(ack_valid),.ack_nak_o(ack_nak),.ack_sequence_o(ack_sequence),.ack_ready_i(ack_ready),
        .fc_valid_o(fc_valid_o),.fc_phase_o(fc_phase_o),.fc_class_o(fc_class_o),
        .fc_header_o(fc_header_o),.fc_data_o(fc_data_o),.bad_dllp_o(bad_dllp_o),.unsupported_dllp_o(unsupported_dllp_o));
    wire [7:0] link_data,packet_data;
    wire link_sop,link_eop,link_valid,link_dllp,link_ready,store_ready;
    wire packet_sop,packet_eop,packet_valid,packet_dllp,packet_ready;
    soc_pcie_link_packets #(.VENDOR_ID(VENDOR_ID),.DEVICE_ID(DEVICE_ID),.APB_TIMEOUT(APB_TIMEOUT),
        .MAX_TLP_DWORDS(MAX_TLP_DWORDS)) endpoint(.clk_i(clk_i),.rst_ni(up_link),.function_id_i(function_id_i),
        .rx_data_i(slice_data),.rx_sop_i(slice_sop),.rx_eop_i(slice_eop),.rx_error_i(slice_error || kind_error),
        .rx_valid_i(slice_valid && !selected_kind),.rx_ready_o(tlp_ready),
        .rx_expected_sequence_o(rx_expected_sequence_o),.tx_next_sequence_o(tx_next_sequence_o),
        .packet_accepted_o(packet_accepted_o),.packet_duplicate_o(packet_duplicate_o),.packet_rejected_o(packet_rejected_o),
        .tx_data_o(packet_data),.tx_sop_o(packet_sop),.tx_eop_o(packet_eop),.tx_valid_o(packet_valid),
        .tx_dllp_o(packet_dllp),.tx_ready_i(packet_ready),.psel_o(psel_o),.penable_o(penable_o),.paddr_o(paddr_o),
        .pwrite_o(pwrite_o),.pstrb_o(pstrb_o),.pwdata_o(pwdata_o),.pready_i(pready_i),.pslverr_i(pslverr_i),
        .prdata_i(prdata_i),.error_o(error_o),.memory_enable_o(memory_enable_o),.bar0_o(bar0_o));
    // Transmit register slice between the link layer and the replay store /
    // DLLP arbiter. The LCRC framer's byte select no longer feeds the replay
    // store's capture checks in the same cycle, and the store's ready no
    // longer reaches back into the framer. TLPs and generated ACK/NAK DLLPs
    // both leave the link layer one cycle later, in order.
    soc_pcie_stream_skid #(.W(11)) transmit_slice(
        .clk_i(clk_i),.rst_ni(local_reset),.clear_i(1'b0),
        .s_data_i({packet_data,packet_sop,packet_eop,packet_dllp}),.s_valid_i(packet_valid),.s_ready_o(packet_ready),
        .m_data_o({link_data,link_sop,link_eop,link_dllp}),.m_valid_o(link_valid),.m_ready_i(link_ready));
    assign rx_tlp_seen_o=packet_accepted_o || packet_duplicate_o;
    wire [7:0] retry_data;
    wire retry_sop,retry_eop,retry_valid,retry_ready,retry_kind;
    soc_pcie_replay_tx #(.DEPTH(REPLAY_DEPTH),.MAX_BYTES(MAX_TLP_DWORDS*4+6),
        .TIMEOUT_CYCLES(REPLAY_TIMEOUT_CYCLES),.MAX_REPLAYS(MAX_REPLAYS)) retry(
        .clk_i(clk_i),.rst_ni(up_retry),.link_up_i(up_retry),.training_i(training_i),.retrain_done_i(retrain_done_i),
        .in_data_i(link_data),.in_sop_i(link_sop),.in_eop_i(link_eop),.in_valid_i(link_valid && !link_dllp),.in_ready_o(store_ready),
        .ack_valid_i(ack_valid),.ack_nak_i(ack_nak),.ack_sequence_i(ack_sequence),.ack_ready_o(ack_ready),
        .reserve_valid_o(reserve_valid_o),.reserve_ready_i(reserve_ready_i),.reserve_class_o(reserve_class_o),
        .reserve_payload_dw_o(reserve_payload_dw_o),.reserve_replay_o(reserve_replay_o),
        .tx_data_o(retry_data),.tx_sop_o(retry_sop),.tx_eop_o(retry_eop),.tx_valid_o(retry_valid),
        .tx_replay_o(retry_kind),.tx_ready_i(retry_ready),.buffered_o(buffered_o),.outstanding_o(outstanding_o),
        .acknowledged_sequence_o(acknowledged_sequence_o),.replay_started_o(replay_started_o),.timeout_o(timeout_o),
        .protocol_error_o(protocol_error_o),.retry_exhausted_o(retry_exhausted_o),.source_error_o(source_error_o),
        .retrain_request_o(retrain_request_o));
    // Packet-locked round robin includes a stalled first byte and source bubbles.
    reg locked,owner,prefer_retry;
    wire dllp_valid=link_valid && link_dllp;
    wire choice=locked ? owner : retry_valid && (!dllp_valid || prefer_retry);
    assign tx_valid_o=local_reset && (choice ? retry_valid : dllp_valid);
    assign tx_data_o=choice ? retry_data : link_data;
    assign tx_sop_o=choice ? retry_sop : link_sop;
    assign tx_eop_o=choice ? retry_eop : link_eop;
    assign tx_dllp_o=!choice;
    assign tx_replay_o=choice && retry_kind;
    assign retry_ready=tx_ready_i && local_reset && choice;
    assign link_ready=link_dllp ? tx_ready_i && local_reset && !choice : store_ready;
    always @(posedge clk_i or negedge local_reset) begin
        if(!local_reset) begin locked<=0;owner<=0;prefer_retry<=0;end
        else if(tx_valid_o) begin
            if(tx_ready_i && tx_eop_o) begin locked<=0;prefer_retry<=!choice;end
            else begin locked<=1;owner<=choice;end
        end
    end
endmodule
`default_nettype wire
