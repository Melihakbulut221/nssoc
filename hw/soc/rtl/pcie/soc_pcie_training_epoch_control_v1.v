// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Bundled-data four-phase command transport, NOT PCIe LTSSM or analog lock.
// The common command stays immutable through every request/ack phase. Local
// mailboxes survive epoch abort/reset; only common POR resets their protocol.
// PMA acknowledges the current held request, epoch and encoding, holds its
// acknowledgment until request falls, then returns it low. This is an explicit
// external PMA contract, not a synthesized detector of clock continuity.
// No new request is admitted until ALL acknowledgments returned low. Thus
// modulo epoch reuse cannot match an outstanding old mailbox transaction.
module soc_pcie_training_epoch_control_v1 #(parameter EPOCH_W=16) (
 input wire por_ni,common_clk_i,input wire [3:0] recovered_clk_i,
 input wire reset_i,epoch_abort_i,
 input wire command_valid_i,output wire command_ready_o,
 input wire [1:0] command_encoding_i,
 input wire [3:0] command_polarity_i,command_align_i,
 output reg command_done_o,output wire command_success_o,
 output wire [EPOCH_W-1:0] epoch_o,output wire [1:0] encoding_o,
 output wire [3:0] polarity_o,align_o,
 output wire pma_request_o,
 input wire pma_ack_i,input wire [EPOCH_W-1:0] pma_ack_epoch_i,
 input wire [1:0] pma_ack_encoding_i,
 input wire fronts_ready_i,
 output wire front_reset_o,epoch_active_o,epoch_fault_o,
 output wire [3:0] lane_request_o,lane_ack_o,
 output wire [4*EPOCH_W-1:0] lane_epoch_o,
 output wire [7:0] lane_encoding_o,
 output wire [3:0] lane_polarity_o,lane_align_o
);
 generate if(EPOCH_W<2 || EPOCH_W>32)begin:invalid_epoch_width
  ERROR_training_epoch_width_must_be_2_to_32 bad();
 end endgenerate
 localparam IDLE=3'd0,WAIT_HIGH=3'd1,WAIT_LOW=3'd2,STARTUP=3'd3,ACTIVE=3'd4;
 localparam PAYLOAD_W=EPOCH_W+4;
 reg [2:0] state_q;
 reg [EPOCH_W-1:0] epoch_q;
 reg [1:0] encoding_q;
 reg [3:0] polarity_q,align_q;
 reg request_q,protocol_fault_q,issued_q,command_success_q;
 wire abort_request=!por_ni || reset_i || epoch_abort_i;
 reg abort_q;
 wire [3:0] ack_local;
 (* ASYNC_REG="TRUE" *) reg [3:0] ack_meta_q,ack_sync_q;
 wire acknowledgments_low=!(|ack_sync_q) && !pma_ack_i;
 assign command_ready_o=por_ni && !abort_request &&
   (state_q==IDLE || state_q==ACTIVE) && acknowledgments_low;
 wire command_fire=command_valid_i && command_ready_o;
 // Asynchronous assertion catches even a reset pulse while a clock is stopped.
 // A new explicit command clears the old abort; no automatic epoch restart.
 always @(posedge common_clk_i or posedge abort_request)
  if(abort_request)abort_q<=1'b1;
  else if(command_fire && command_encoding_i!=2'b11)abort_q<=1'b0;
 assign epoch_o=epoch_q;assign encoding_o=encoding_q;
 assign polarity_o=polarity_q;assign align_o=align_q;
 assign pma_request_o=por_ni && request_q;
 assign lane_request_o={4{pma_request_o}};
 assign lane_ack_o=ack_sync_q;
 assign front_reset_o=abort_request || abort_q || protocol_fault_q || command_fire ||
   !(state_q==STARTUP || state_q==ACTIVE);
 assign epoch_active_o=por_ni && state_q==ACTIVE && !front_reset_o && fronts_ready_i;
 // A coincident asynchronous abort may schedule abort_q in the same delta as
 // completion. Qualify the public success witness directly, not one clock later.
 assign command_success_o=command_success_q && !abort_request && !abort_q && !protocol_fault_q;
 assign epoch_fault_o=por_ni && (protocol_fault_q || (issued_q && abort_q));
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1)begin:mailboxes
  (* ASYNC_REG="TRUE" *) reg [1:0] request_sync_q;
  reg ack_q;
  reg [PAYLOAD_W-1:0] applied_q;
  wire [PAYLOAD_W-1:0] held_payload={epoch_q,encoding_q,polarity_q[lane],align_q[lane]};
  always @(posedge recovered_clk_i[lane] or negedge por_ni)begin
   if(!por_ni)begin request_sync_q<=0;ack_q<=0;applied_q<=0;end
   else begin
    request_sync_q<={request_sync_q[0],request_q};
    if(request_sync_q[1] && !ack_q)begin
     applied_q<=held_payload;
     ack_q<=1'b1;
    end else if(!request_sync_q[1])ack_q<=1'b0;
   end
  end
  assign ack_local[lane]=ack_q;
  assign lane_epoch_o[lane*EPOCH_W+:EPOCH_W]=applied_q[PAYLOAD_W-1:4];
  assign lane_encoding_o[lane*2+:2]=applied_q[3:2];
  assign lane_polarity_o[lane]=applied_q[1];
  assign lane_align_o[lane]=applied_q[0];
 end endgenerate
 reg payload_match;
 integer k;
 always @* begin
  payload_match=1'b1;
  for(k=0;k<4;k=k+1)
   if({lane_epoch_o[k*EPOCH_W+:EPOCH_W],lane_encoding_o[k*2+:2],
       lane_polarity_o[k],lane_align_o[k]}!={epoch_q,encoding_q,polarity_q[k],align_q[k]})
    payload_match=1'b0;
 end
 always @(posedge common_clk_i or negedge por_ni)begin
  if(!por_ni)begin
   ack_meta_q<=0;ack_sync_q<=0;state_q<=IDLE;epoch_q<=0;
   encoding_q<=0;polarity_q<=0;align_q<=0;request_q<=0;
   protocol_fault_q<=0;issued_q<=0;command_done_o<=0;command_success_q<=0;
  end else begin
   ack_meta_q<=ack_local;ack_sync_q<=ack_meta_q;
   command_done_o<=0;command_success_q<=0;
   if(command_fire)begin
    if(command_encoding_i==2'b11)begin
     protocol_fault_q<=1'b1;state_q<=IDLE;command_done_o<=1'b1;
    end else begin
     epoch_q<=epoch_q+1'b1;encoding_q<=command_encoding_i;
     polarity_q<=command_polarity_i;align_q<=command_align_i;
     protocol_fault_q<=0;issued_q<=1;request_q<=1;state_q<=WAIT_HIGH;
    end
   end else case(state_q)
    WAIT_HIGH:begin
     if(pma_ack_i && (pma_ack_epoch_i!=epoch_q || pma_ack_encoding_i!=encoding_q))
      protocol_fault_q<=1'b1;
     if((&ack_sync_q) && pma_ack_i)begin
      if(!payload_match)protocol_fault_q<=1'b1;
      request_q<=0;state_q<=WAIT_LOW;
     end
    end
    WAIT_LOW:if(acknowledgments_low)begin
     if(abort_request || abort_q || protocol_fault_q)begin state_q<=IDLE;command_done_o<=1;end
     else state_q<=STARTUP;
    end
    STARTUP:begin
     if(abort_request || abort_q || protocol_fault_q)begin state_q<=IDLE;command_done_o<=1;end
     else if(fronts_ready_i)begin
      state_q<=ACTIVE;command_done_o<=1;command_success_q<=1;
     end
    end
    ACTIVE:if(abort_request || abort_q || protocol_fault_q)state_q<=IDLE;
    default:begin end
   endcase
  end
 end
endmodule
`default_nettype wire
