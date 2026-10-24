// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Owned-integrity boundary: four DWORDs and up to four ordered descriptors.
// DLLP CRC is already checked by the upstream owned framer. Good TLP bytes
// pass through at their full width; no scalar controller adapter is present.
module soc_pcie_gen3_dllp_consumer_v1(
 input wire clk_i,rst_ni,flush_i,input wire [15:0] epoch_i,
 input wire body_valid_i,output wire body_ready_o,
 input wire [127:0] body_data_i,input wire [15:0] body_keep_i,body_sop_i,body_eop_i,body_dllp_i,
 input wire [47:0] body_sequence_i,input wire [23:0] body_owner_i,
 input wire [3:0] descriptor_valid_i,output wire descriptor_ready_o,
 input wire [23:0] descriptor_owner_i,input wire [47:0] descriptor_sequence_i,
 input wire [51:0] descriptor_bytes_i,
 input wire [3:0] descriptor_good_i,descriptor_nullified_i,descriptor_crc_bad_i,descriptor_dllp_i,
 output wire tlp_valid_o,input wire tlp_ready_i,
 output wire [127:0] tlp_data_o,output wire [15:0] tlp_keep_o,tlp_sop_o,tlp_eop_o,
 output wire [47:0] tlp_sequence_o,output wire [23:0] tlp_owner_o,
 output wire [3:0] event_valid_o,input wire event_ready_i,
 output wire [23:0] event_owner_o,output wire [47:0] event_sequence_o,
 output wire [51:0] event_bytes_o,output wire [15:0] event_kind_o,
 output wire [127:0] event_raw_dllp_o,output wire [47:0] event_ack_sequence_o,
 output wire [7:0] event_fc_phase_o,event_fc_class_o,
 output wire [31:0] event_fc_header_o,output wire [47:0] event_fc_data_o,
 output wire [15:0] epoch_o,output reg halted_o
);
 // Event kinds: 0 good TLP,1 CRC discard,2 EDB nullification,3 ACK,4 NAK,
 // 5 VC0 unscaled FC,6 unsupported DLLP. These are decode events, not actions.
 // All 64 complete owner IDs have separate bounded rendezvous entries. A
 // held event prevents reuse of its exact ID, including after modular wrap.
 reg desc[0:63],started[0:63],done[0:63],good[0:63],nul[0:63],bad[0:63],dllp[0:63],body_kind[0:63];
 reg nd[0:63],ns[0:63],nf[0:63],ng[0:63],nn[0:63],nb[0:63],nk[0:63],nbodykind[0:63];
 reg [12:0] size[0:63],received[0:63],nz[0:63],nr[0:63];
 reg [11:0] seq[0:63],nseq[0:63];
 reg [31:0] raw[0:63],nraw[0:63];
 reg [5:0] desc_ptr,event_ptr,desc_next,event_next;
 reg [15:0] epoch;
 reg [2:0] event_count,event_count_n;
 reg [23:0] event_owner,event_owner_n;
 reg [47:0] event_sequence,event_sequence_n,event_ack,event_ack_n,event_fc_data,event_fc_data_n;
 reg [51:0] event_bytes,event_bytes_n;
 reg [15:0] event_kind,event_kind_n;
 reg [127:0] event_raw,event_raw_n;
 reg [7:0] event_phase,event_phase_n,event_class,event_class_n;
 reg [31:0] event_header,event_header_n;
 reg desc_space,body_space,protocol_error,stop_event;
 reg [3:0] desc_count;
 reg [63:0] released;
 reg [3:0] k,s,e,d;
 reg [5:0] id;
 reg [7:0] kind;
 reg [31:0] word_value;
 integer i,j,b,a,nbytes,c;
 wire enabled=rst_ni && !flush_i && epoch_i==epoch && !halted_o;
 wire event_pop=enabled && event_count!=0 && event_ready_i;
 wire has_tlp=|(body_keep_i & ~body_dllp_i);
 assign descriptor_ready_o=enabled && desc_space;
 assign body_ready_o=enabled && body_space && (!has_tlp || tlp_ready_i);
 // Atomic fork: the TLP sink can handshake iff the same whole input beat is
 // accepted. DLLP-only traffic remains independent of the TLP sink readiness.
 assign tlp_valid_o=enabled && body_valid_i && body_space && has_tlp;
 assign tlp_data_o=tlp_valid_o?body_data_i:0;
 assign tlp_keep_o=tlp_valid_o?(body_keep_i & ~body_dllp_i):0;
 assign tlp_sop_o=body_sop_i & tlp_keep_o;
 assign tlp_eop_o=body_eop_i & tlp_keep_o;
 assign tlp_sequence_o=tlp_valid_o?body_sequence_i:0;
 assign tlp_owner_o=tlp_valid_o?body_owner_i:0;
 assign event_valid_o=enabled?((5'b1<<event_count)-1'b1):0;
 assign event_owner_o=event_valid_o!=0?event_owner:0;
 assign event_sequence_o=event_valid_o!=0?event_sequence:0;
 assign event_bytes_o=event_valid_o!=0?event_bytes:0;
 assign event_kind_o=event_valid_o!=0?event_kind:0;
 assign event_raw_dllp_o=event_valid_o!=0?event_raw:0;
 assign event_ack_sequence_o=event_valid_o!=0?event_ack:0;
 assign event_fc_phase_o=event_valid_o!=0?event_phase:0;
 assign event_fc_class_o=event_valid_o!=0?event_class:0;
 assign event_fc_header_o=event_valid_o!=0?event_header:0;
 assign event_fc_data_o=event_valid_o!=0?event_fc_data:0;
 assign epoch_o=epoch;
 always @* begin
   released=0;
   if(event_pop) for(c=0;c<4;c=c+1)
     if(c<event_count) released[event_owner[c*6+:6]]=1;
   desc_count=0;desc_space=1;
   for(c=0;c<4;c=c+1) begin
     if(descriptor_valid_i[c]) begin
       desc_count=desc_count+1'b1;
       if(desc[descriptor_owner_i[c*6+:6]] && !released[descriptor_owner_i[c*6+:6]]) desc_space=0;
     end
   end
   body_space=1;
   for(c=0;c<4;c=c+1) begin
     if(body_keep_i[c*4+:4]!=0 && body_sop_i[c*4+:4]!=0) begin
       if((started[body_owner_i[c*6+:6]] ||
          (desc[body_owner_i[c*6+:6]] && !good[body_owner_i[c*6+:6]])) &&
          !released[body_owner_i[c*6+:6]]) body_space=0;
     end
   end
 end
 always @* begin
   for(i=0;i<64;i=i+1) begin
     nd[i]=desc[i];ns[i]=started[i];nf[i]=done[i];ng[i]=good[i];nn[i]=nul[i];nb[i]=bad[i];nk[i]=dllp[i];nbodykind[i]=body_kind[i];
     nz[i]=size[i];nr[i]=received[i];nseq[i]=seq[i];nraw[i]=raw[i];
     if(released[i]) begin
       nd[i]=0;ns[i]=0;nf[i]=0;ng[i]=0;nn[i]=0;nb[i]=0;nk[i]=0;nbodykind[i]=0;
       nz[i]=0;nr[i]=0;nseq[i]=0;nraw[i]=0;
     end
   end
   desc_next=desc_ptr;event_next=event_ptr+(event_pop?event_count:0);
   protocol_error=0;k=0;s=0;e=0;d=0;id=0;kind=0;word_value=0;nbytes=0;a=0;
   if(enabled && descriptor_valid_i!=0 && descriptor_ready_o) begin
     if(descriptor_valid_i!=1 && descriptor_valid_i!=3 && descriptor_valid_i!=7 && descriptor_valid_i!=15) protocol_error=1;
     for(j=0;j<4;j=j+1) if(descriptor_valid_i[j]) begin
       id=descriptor_owner_i[j*6+:6];
       if(id!=desc_next || (descriptor_good_i[j]+{1'b0,descriptor_nullified_i[j]}+{1'b0,descriptor_crc_bad_i[j]})!=1) protocol_error=1;
       nd[id]=1;ng[id]=descriptor_good_i[j];nn[id]=descriptor_nullified_i[j];nb[id]=descriptor_crc_bad_i[j];nk[id]=descriptor_dllp_i[j];
       nz[id]=descriptor_bytes_i[j*13+:13];nseq[id]=descriptor_sequence_i[j*12+:12];
       if(nk[id] && (nz[id]!=6 || nn[id])) protocol_error=1;
       if(!ng[id] && ns[id]) protocol_error=1;
       desc_next=desc_next+1'b1;
     end
   end
   if(enabled && body_valid_i && body_ready_o) begin
     for(j=0;j<4;j=j+1) begin
       k=body_keep_i[j*4+:4];s=body_sop_i[j*4+:4];e=body_eop_i[j*4+:4];d=body_dllp_i[j*4+:4];
       id=body_owner_i[j*6+:6];word_value=body_data_i[j*32+:32];
       if(k!=0) begin
         if(s!=0) begin
           if(s!=1 || k!=3 || ns[id]) protocol_error=1;
           ns[id]=1;nf[id]=0;nr[id]=0;nraw[id]=0;nbodykind[id]=(d!=0);
         end else if(!ns[id] || nf[id] || k!=15) protocol_error=1;
         if((d!=0 && d!=k) || (d!=0)!=nbodykind[id] || (nd[id] && (!ng[id] || nk[id]!=(d!=0)))) protocol_error=1;
         for(b=0;b<4;b=b+1) if(k[b]) begin
           if(nr[id]<4) nraw[id][nr[id]*8+:8]=word_value[b*8+:8];
           if(nr[id]==8191) protocol_error=1;
           nr[id]=nr[id]+1'b1;
         end
         if(e!=0) begin
           if(e!=8 || k!=15) protocol_error=1;
           nf[id]=1;
           if(nbodykind[id] && nr[id]!=6) protocol_error=1;
         end
       end else if(s!=0 || e!=0 || d!=0) protocol_error=1;
     end
   end
   event_count_n=event_count;event_owner_n=event_owner;event_sequence_n=event_sequence;event_bytes_n=event_bytes;
   event_kind_n=event_kind;event_raw_n=event_raw;event_ack_n=event_ack;event_phase_n=event_phase;event_class_n=event_class;
   event_header_n=event_header;event_fc_data_n=event_fc_data;
   stop_event=0;
   if(event_count==0 || event_pop) begin
     event_count_n=0;event_owner_n=0;event_sequence_n=0;event_bytes_n=0;event_kind_n=0;event_raw_n=0;
     event_ack_n=0;event_phase_n=0;event_class_n=0;event_header_n=0;event_fc_data_n=0;
     for(j=0;j<4;j=j+1) begin
       a=(event_next+j)&63;
       if(!stop_event && nd[a] && (!ng[a] || nf[a])) begin
         if(ng[a] && (nr[a]!=nz[a] || nk[a]!=nbodykind[a])) protocol_error=1;
         event_count_n=event_count_n+1'b1;event_owner_n[j*6+:6]=a[5:0];event_sequence_n[j*12+:12]=nseq[a];event_bytes_n[j*13+:13]=nz[a];
         if(nb[a]) event_kind_n[j*4+:4]=1;
         else if(nn[a]) event_kind_n[j*4+:4]=2;
         else if(!nk[a]) event_kind_n[j*4+:4]=0;
         else begin
           word_value=nraw[a];kind=word_value[7:0];event_raw_n[j*32+:32]=word_value;
           if(kind==8'h00 || kind==8'h10) begin
             event_kind_n[j*4+:4]=(kind==8'h00)?3:4;
             event_ack_n[j*12+:12]={word_value[19:16],word_value[31:24]};
           end else if(kind==8'h40 || kind==8'h50 || kind==8'h60 || kind==8'hc0 || kind==8'hd0 || kind==8'he0 || kind==8'h80 || kind==8'h90 || kind==8'ha0) begin
             event_kind_n[j*4+:4]=5;
             event_phase_n[j*2+:2]=kind[7:6]==1?0:kind[7:6]==3?1:2;
             event_class_n[j*2+:2]=kind[5:4];
             event_header_n[j*8+:8]={word_value[13:8],word_value[23:22]};
             event_fc_data_n[j*12+:12]={word_value[19:16],word_value[31:24]};
           end else event_kind_n[j*4+:4]=6;
         end
       end else stop_event=1;
     end
   end
 end
 integer q;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     epoch<=0;halted_o<=0;desc_ptr<=0;event_ptr<=0;event_count<=0;event_owner<=0;event_sequence<=0;event_bytes<=0;
     event_kind<=0;event_raw<=0;event_ack<=0;event_phase<=0;event_class<=0;event_header<=0;event_fc_data<=0;
     for(q=0;q<64;q=q+1) begin desc[q]<=0;started[q]<=0;done[q]<=0;good[q]<=0;nul[q]<=0;bad[q]<=0;dllp[q]<=0;body_kind[q]<=0;size[q]<=0;received[q]<=0;seq[q]<=0;raw[q]<=0;end
   end else if(flush_i || epoch_i!=epoch) begin
     epoch<=epoch_i;halted_o<=0;desc_ptr<=0;event_ptr<=0;event_count<=0;
     for(q=0;q<64;q=q+1) begin desc[q]<=0;started[q]<=0;done[q]<=0;good[q]<=0;nul[q]<=0;bad[q]<=0;dllp[q]<=0;body_kind[q]<=0;size[q]<=0;received[q]<=0;seq[q]<=0;raw[q]<=0;end
   end else if(enabled) begin
     if(protocol_error) begin halted_o<=1;event_count<=0;end
     else begin
       desc_ptr<=desc_next;event_ptr<=event_next;event_count<=event_count_n;event_owner<=event_owner_n;event_sequence<=event_sequence_n;event_bytes<=event_bytes_n;
       event_kind<=event_kind_n;event_raw<=event_raw_n;event_ack<=event_ack_n;event_phase<=event_phase_n;event_class<=event_class_n;event_header<=event_header_n;event_fc_data<=event_fc_data_n;
       for(q=0;q<64;q=q+1) begin desc[q]<=nd[q];started[q]<=ns[q];done[q]<=nf[q];good[q]<=ng[q];nul[q]<=nn[q];bad[q]<=nb[q];dllp[q]<=nk[q];body_kind[q]<=nbodykind[q];size[q]<=nz[q];received[q]<=nr[q];seq[q]<=nseq[q];raw[q]<=nraw[q];end
     end
   end
 end
endmodule
`default_nettype wire
