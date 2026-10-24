// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// One outstanding APB request across unrelated clocks. Four-phase mailbox:
// request/response payloads stay fixed through two-flop control synchronization.
// reset_ni must assert on system reset OR PCIe link loss/retraining, affecting
// both halves; deassertion is synchronized separately. A completed write cannot
// be undone by reset. Source must obey APB and hold ACCESS until ready/reset.
// Bundled data paths require explicit physical max-delay/CDC verification;
// ASYNC_REG attributes alone do not qualify a placed implementation.
module soc_pcie_apb_cdc (
 input wire source_clk_i, destination_clk_i, reset_ni,
 input wire s_psel_i, s_penable_i, s_pwrite_i,
 input wire [11:0] s_paddr_i,
 input wire [31:0] s_pwdata_i,
 input wire [3:0] s_pstrb_i,
 output wire s_pready_o, s_pslverr_o,
 output wire [31:0] s_prdata_o,
 output wire m_psel_o, m_penable_o,
 output reg m_pwrite_o,
 output reg [11:0] m_paddr_o,
 output reg [31:0] m_pwdata_o,
 output reg [3:0] m_pstrb_o,
 input wire m_pready_i, m_pslverr_i,
 input wire [31:0] m_prdata_i
);
 (* ASYNC_REG="TRUE" *) reg [1:0] source_release, destination_release;
 always @(posedge source_clk_i or negedge reset_ni)
   if(!reset_ni) source_release<=0; else source_release<={source_release[0],1'b1};
 always @(posedge destination_clk_i or negedge reset_ni)
   if(!reset_ni) destination_release<=0; else destination_release<={destination_release[0],1'b1};
 wire source_reset_n=reset_ni && source_release[1];
 wire destination_reset_n=reset_ni && destination_release[1];
 reg request, acknowledgement;
 (* ASYNC_REG="TRUE" *) reg [1:0] request_sync, acknowledgement_sync;
 always @(posedge source_clk_i or negedge source_reset_n)
   if(!source_reset_n) acknowledgement_sync<=0;
   else acknowledgement_sync<={acknowledgement_sync[0],acknowledgement};
 always @(posedge destination_clk_i or negedge destination_reset_n)
   if(!destination_reset_n) request_sync<=0;
   else request_sync<={request_sync[0],request};
 reg [48:0] request_payload;
 reg [32:0] response_payload, response;
 localparam [1:0] S_IDLE=0,S_WAIT=1,S_RESPONSE=2,S_DRAIN=3;
 localparam [1:0] D_IDLE=0,D_SETUP=1,D_ACCESS=2,D_DRAIN=3;
 reg [1:0] source_state, destination_state;
 reg served;
 assign s_pready_o=source_reset_n && source_state==S_RESPONSE && s_psel_i && s_penable_i;
 assign s_pslverr_o=s_pready_o && response[32];
 assign s_prdata_o=s_pready_o ? response[31:0] : 32'b0;
 assign m_psel_o=destination_reset_n && (destination_state==D_SETUP || destination_state==D_ACCESS);
 assign m_penable_o=destination_reset_n && destination_state==D_ACCESS;
 always @(posedge source_clk_i or negedge source_reset_n) begin
   if(!source_reset_n) begin
     request<=0;request_payload<=0;response<=0;source_state<=S_IDLE;served<=0;
   end else begin
     if(!s_psel_i || !s_penable_i) served<=0;
     case(source_state)
       S_IDLE: if(s_psel_i && s_penable_i && !served) begin
         request_payload<={s_pwrite_i,s_paddr_i,s_pwdata_i,s_pstrb_i};
         request<=1;source_state<=S_WAIT;
       end
       S_WAIT: if(acknowledgement_sync[1]) begin
         response<=response_payload;source_state<=S_RESPONSE;
       end
       S_RESPONSE: if(s_pready_o) begin
         request<=0;served<=1;source_state<=S_DRAIN;
       end
       S_DRAIN: if(!acknowledgement_sync[1]) source_state<=S_IDLE;
     endcase
   end
 end
 always @(posedge destination_clk_i or negedge destination_reset_n) begin
   if(!destination_reset_n) begin
     acknowledgement<=0;response_payload<=0;destination_state<=D_IDLE;
     m_pwrite_o<=0;m_paddr_o<=0;m_pwdata_o<=0;m_pstrb_o<=0;
   end else begin
     case(destination_state)
       D_IDLE: if(request_sync[1]) begin
         {m_pwrite_o,m_paddr_o,m_pwdata_o,m_pstrb_o}<=request_payload;
         destination_state<=D_SETUP;
       end
       D_SETUP: destination_state<=D_ACCESS;
       D_ACCESS: if(m_pready_i) begin
         response_payload<={m_pslverr_i,m_prdata_i};
         acknowledgement<=1;destination_state<=D_DRAIN;
       end
       D_DRAIN: if(!request_sync[1]) begin
         acknowledgement<=0;destination_state<=D_IDLE;
       end
     endcase
   end
 end
endmodule
`default_nettype wire
